from ingest.extract import extract_html


def test_extracts_sections_tables_and_visible_inline_xbrl() -> None:
    document = extract_html(
        """
        <html><body>
          <script>ignore()</script>
          <ix:hidden><ix:nonfraction>999</ix:nonfraction></ix:hidden>
          <h2>Item 7. Management's Discussion</h2>
          <p>Net sales were <ix:nonfraction>$100 million</ix:nonfraction>.</p>
          <table>
            <tr><th>Year</th><th>Revenue</th></tr>
            <tr><td>2024</td><td>$100</td></tr>
          </table>
        </body></html>
        """
    )

    assert "ignore" not in document.markdown
    assert "999" not in document.markdown
    assert "$100 million" in document.markdown
    assert "| Year | Revenue |" in document.markdown
    assert "| 2024 | $100 |" in document.markdown
    assert all(block.section == "Item 7" for block in document.blocks)
    assert document.blocks[0].start_offset == 0
    assert document.blocks[-1].end_offset == len(document.markdown)


def test_page_is_only_set_when_reliable_break_marker_exists() -> None:
    without_pages = extract_html("<p>First paragraph</p><p>Second paragraph</p>")
    with_pages = extract_html(
        '<p>Page one</p><div style="page-break-before: always"></div><p>Page two</p>'
    )

    assert all(block.page is None for block in without_pages.blocks)
    assert [block.page for block in with_pages.blocks] == [1, 2]
