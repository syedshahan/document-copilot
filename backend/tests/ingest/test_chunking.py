from ingest.chunking import chunk_document
from ingest.extract import ExtractedBlock, ExtractedDocument


def _document(blocks: list[str], kind: str = "paragraph") -> ExtractedDocument:
    extracted = []
    offset = 0
    for text in blocks:
        extracted.append(
            ExtractedBlock(text, kind, "Item 7", None, offset, offset + len(text))
        )
        offset += len(text) + 2
    return ExtractedDocument("\n\n".join(blocks), extracted)


def test_chunking_respects_size_order_and_overlap() -> None:
    document = _document(["A" * 40, "B" * 40, "C" * 40])

    chunks = chunk_document(document, max_chars=90, overlap_chars=45)

    assert [chunk.chunk_index for chunk in chunks] == [0, 1]
    assert chunks[0].content == f"{'A' * 40}\n\n{'B' * 40}"
    assert chunks[1].content == f"{'B' * 40}\n\n{'C' * 40}"
    assert all(len(chunk.content) <= 90 for chunk in chunks)


def test_large_table_chunks_repeat_header() -> None:
    table = "| Year | Revenue |\n| --- | --- |\n" + "\n".join(
        f"| {year} | {'9' * 30} |" for year in range(2015, 2025)
    )

    chunks = chunk_document(
        _document([table], kind="table"), max_chars=160, overlap_chars=0
    )

    assert len(chunks) > 1
    assert all(
        chunk.content.startswith("| Year | Revenue |\n| --- | --- |")
        for chunk in chunks
    )
    assert all(len(chunk.content) <= 160 for chunk in chunks)
