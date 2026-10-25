import re
from dataclasses import dataclass

from ingest.extract import ExtractedBlock, ExtractedDocument

MAX_CHUNK_CHARS = 5_000
OVERLAP_CHARS = 700
_SENTENCE_END_RE = re.compile(r"(?<=[.!?])\s+")


@dataclass(frozen=True)
class DocumentChunk:
    chunk_index: int
    content: str
    token_count: int
    page: int | None
    section: str | None
    start_offset: int
    end_offset: int


def chunk_document(
    document: ExtractedDocument,
    max_chars: int = MAX_CHUNK_CHARS,
    overlap_chars: int = OVERLAP_CHARS,
) -> list[DocumentChunk]:
    if max_chars <= 0 or overlap_chars < 0 or overlap_chars >= max_chars:
        raise ValueError("Chunk sizes must satisfy 0 <= overlap_chars < max_chars")

    blocks = [
        piece
        for block in document.blocks
        for piece in _split_oversized_block(block, max_chars)
        if piece.markdown.strip()
    ]
    chunks: list[DocumentChunk] = []
    current: list[ExtractedBlock] = []

    for block in blocks:
        candidate = _join_blocks([*current, block])
        if current and len(candidate) > max_chars:
            chunks.append(_make_chunk(len(chunks), current))
            current = _overlap_blocks(current, overlap_chars)
            while current and len(_join_blocks([*current, block])) > max_chars:
                current.pop(0)
        current.append(block)

    if current:
        chunks.append(_make_chunk(len(chunks), current))
    return chunks


def estimate_tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4)


def _make_chunk(index: int, blocks: list[ExtractedBlock]) -> DocumentChunk:
    content = _join_blocks(blocks)
    first = blocks[0]
    last = blocks[-1]
    return DocumentChunk(
        chunk_index=index,
        content=content,
        token_count=estimate_tokens(content),
        page=first.page if all(block.page == first.page for block in blocks) else None,
        section=first.section
        if all(block.section == first.section for block in blocks)
        else None,
        start_offset=first.start_offset,
        end_offset=last.end_offset,
    )


def _join_blocks(blocks: list[ExtractedBlock]) -> str:
    return "\n\n".join(block.markdown for block in blocks)


def _overlap_blocks(
    blocks: list[ExtractedBlock], overlap_chars: int
) -> list[ExtractedBlock]:
    if overlap_chars == 0:
        return []
    selected: list[ExtractedBlock] = []
    size = 0
    for block in reversed(blocks):
        if selected and size + len(block.markdown) > overlap_chars:
            break
        selected.append(block)
        size += len(block.markdown) + 2
    return list(reversed(selected))


def _split_oversized_block(
    block: ExtractedBlock, max_chars: int
) -> list[ExtractedBlock]:
    if len(block.markdown) <= max_chars:
        return [block]
    pieces = (
        _split_table(block.markdown, max_chars)
        if block.kind == "table"
        else _split_text(block.markdown, max_chars)
    )
    result: list[ExtractedBlock] = []
    cursor = block.start_offset
    for piece in pieces:
        end = min(block.end_offset, cursor + len(piece))
        result.append(
            ExtractedBlock(
                markdown=piece,
                kind=block.kind,
                section=block.section,
                page=block.page,
                start_offset=cursor,
                end_offset=end,
            )
        )
        cursor = end
    return result


def _split_table(markdown: str, max_chars: int) -> list[str]:
    lines = markdown.splitlines()
    if len(lines) < 3:
        return _split_text(markdown, max_chars)
    header = lines[:2]
    pieces: list[str] = []
    current = header.copy()
    for row in lines[2:]:
        candidate = "\n".join([*current, row])
        if len(candidate) > max_chars and len(current) > 2:
            pieces.append("\n".join(current))
            current = [*header, row]
        else:
            current.append(row)
    if len(current) > 2:
        pieces.append("\n".join(current))
    return [part for piece in pieces for part in _split_text(piece, max_chars)]


def _split_text(text: str, max_chars: int) -> list[str]:
    sentences = _SENTENCE_END_RE.split(text)
    pieces: list[str] = []
    current = ""
    for sentence in sentences:
        for part in _hard_split(sentence, max_chars):
            candidate = f"{current} {part}".strip()
            if current and len(candidate) > max_chars:
                pieces.append(current)
                current = part
            else:
                current = candidate
    if current:
        pieces.append(current)
    return pieces


def _hard_split(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    words = text.split()
    pieces: list[str] = []
    current = ""
    for word in words:
        if len(word) > max_chars:
            if current:
                pieces.append(current)
                current = ""
            pieces.extend(
                word[index : index + max_chars]
                for index in range(0, len(word), max_chars)
            )
            continue
        candidate = f"{current} {word}".strip()
        if current and len(candidate) > max_chars:
            pieces.append(current)
            current = word
        else:
            current = candidate
    if current:
        pieces.append(current)
    return pieces
