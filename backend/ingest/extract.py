import re
from dataclasses import dataclass
from pathlib import Path

from bs4 import BeautifulSoup, Tag, UnicodeDammit

_BLOCK_TAGS = {"div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "p", "table"}
_HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
_SECTION_RE = re.compile(
    r"^ITEM\s+(1A|1B|1C|1|2|3|4|5|6|7A|7|8|9A|9B|9C|9|10|11|12|13|14|15|16)\b",
    re.IGNORECASE,
)
_SPACE_RE = re.compile(r"[\t\r\f\v ]+")


@dataclass(frozen=True)
class ExtractedBlock:
    markdown: str
    kind: str
    section: str | None
    page: int | None
    start_offset: int
    end_offset: int


@dataclass(frozen=True)
class ExtractedDocument:
    markdown: str
    blocks: list[ExtractedBlock]


def extract_filing(path: Path) -> ExtractedDocument:
    return extract_html(path.read_bytes())


def extract_html(content: bytes | str) -> ExtractedDocument:
    if isinstance(content, bytes):
        content = UnicodeDammit.detwingle(content).decode("utf-8")
    soup = BeautifulSoup(content, "html.parser")
    _remove_noise(soup)
    has_pages = any(_is_page_break(tag) for tag in soup.find_all(True))
    page = 1 if has_pages else None
    section: str | None = None
    pending: list[tuple[str, str, str | None, int | None]] = []

    for tag in soup.find_all(_BLOCK_TAGS):
        if _inside_ignored_container(tag) or not _is_content_block(tag):
            continue
        if _is_page_break(tag) and page is not None:
            page += 1

        kind, markdown = _render_block(tag)
        if not markdown:
            continue
        plain_text = _normalize_text(tag.get_text(" ", strip=True))
        if match := _SECTION_RE.match(plain_text):
            section = f"Item {match.group(1).upper()}"
            kind = "heading"
        pending.append((markdown, kind, section, page))

    blocks: list[ExtractedBlock] = []
    pieces: list[str] = []
    offset = 0
    for markdown, kind, block_section, block_page in pending:
        if pieces:
            pieces.append("\n\n")
            offset += 2
        start = offset
        pieces.append(markdown)
        offset += len(markdown)
        blocks.append(
            ExtractedBlock(
                markdown=markdown,
                kind=kind,
                section=block_section,
                page=block_page,
                start_offset=start,
                end_offset=offset,
            )
        )
    return ExtractedDocument(markdown="".join(pieces), blocks=blocks)


def _remove_noise(soup: BeautifulSoup) -> None:
    for tag in soup.find_all(
        ["script", "style", "noscript", "template", "ix:hidden", "ix:header"]
    ):
        tag.decompose()
    for tag in soup.find_all(True):
        if tag.name is None or tag.attrs is None:
            continue
        style = str(tag.get("style", "")).replace(" ", "").lower()
        if (
            tag.get("hidden") is not None
            or str(tag.get("aria-hidden", "")).lower() == "true"
            or "display:none" in style
            or "visibility:hidden" in style
        ):
            tag.decompose()


def _inside_ignored_container(tag: Tag) -> bool:
    if tag.name in {"li", "p"} and tag.find_parent("table") is not None:
        return True
    if tag.name != "table" and tag.find_parent("table") is not None:
        return True
    return bool(tag.name == "li" and tag.find_parent("li") is not None)


def _is_content_block(tag: Tag) -> bool:
    if tag.name in {"table", "p", "li", *_HEADING_TAGS}:
        return True
    return tag.name == "div" and tag.find(_BLOCK_TAGS) is None


def _render_block(tag: Tag) -> tuple[str, str]:
    if tag.name == "table":
        return "table", _render_table(tag)
    text = _normalize_text(tag.get_text(" ", strip=True))
    if not text:
        return "paragraph", ""
    if tag.name in _HEADING_TAGS:
        level = int(tag.name[1])
        return "heading", f"{'#' * min(level, 4)} {text}"
    if tag.name == "li":
        return "list", f"- {text}"
    return "paragraph", text


def _render_table(table: Tag) -> str:
    rows: list[list[str]] = []
    header_flags: list[bool] = []
    for row in table.find_all("tr"):
        cells = row.find_all(["th", "td"], recursive=False)
        if not cells:
            cells = row.find_all(["th", "td"])
        values = [
            _escape_cell(_normalize_text(cell.get_text(" ", strip=True)))
            for cell in cells
        ]
        if any(values):
            rows.append(values)
            header_flags.append(any(cell.name == "th" for cell in cells))
    if not rows:
        return ""

    width = max(len(row) for row in rows)
    normalized = [row + [""] * (width - len(row)) for row in rows]
    header_index = next((index for index, flag in enumerate(header_flags) if flag), 0)
    header = normalized[header_index]
    body = normalized[:header_index] + normalized[header_index + 1 :]
    lines = [_markdown_row(header), _markdown_row(["---"] * width)]
    lines.extend(_markdown_row(row) for row in body)
    return "\n".join(lines)


def _markdown_row(cells: list[str]) -> str:
    return f"| {' | '.join(cells)} |"


def _escape_cell(value: str) -> str:
    return value.replace("|", "\\|")


def _normalize_text(value: str) -> str:
    return _SPACE_RE.sub(" ", value).strip()


def _is_page_break(tag: Tag) -> bool:
    style = str(tag.get("style", "")).replace(" ", "").lower()
    return "page-break-before:always" in style or "break-before:page" in style
