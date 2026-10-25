import json
from pathlib import Path

import pytest

from ingest.manifest import ManifestError, load_manifest


def _manifest(local_path: str = "2024/aapl.htm") -> dict:
    return {
        "source": "SEC EDGAR",
        "generated_at_utc": "2025-01-01T00:00:00+00:00",
        "form": "10-K",
        "downloaded_count": 1,
        "filings": [
            {
                "ticker": "AAPL",
                "cik": "0000320193",
                "form": "10-K",
                "filing_date": "2024-11-01",
                "report_date": "2024-09-28",
                "accession_number": "0000320193-24-000123",
                "primary_document": "aapl.htm",
                "source_url": "https://www.sec.gov/aapl.htm",
                "local_path": local_path,
            }
        ],
    }


def test_load_manifest_validates_file_and_derives_fiscal_year(tmp_path: Path) -> None:
    filing_path = tmp_path / "2024" / "aapl.htm"
    filing_path.parent.mkdir()
    filing_path.write_text("<html></html>", encoding="utf-8")
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(_manifest()), encoding="utf-8")

    manifest = load_manifest(manifest_path)

    assert manifest.filings[0].company_name == "Apple Inc."
    assert manifest.filings[0].fiscal_year == 2024


def test_load_manifest_rejects_path_outside_downloads(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.htm"
    outside.write_text("<html></html>", encoding="utf-8")
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(_manifest("../outside.htm")), encoding="utf-8")

    with pytest.raises(ManifestError, match="escapes the downloads directory"):
        load_manifest(manifest_path)

    outside.unlink()
