import json
from datetime import date
from pathlib import Path

from pydantic import BaseModel, Field, HttpUrl, ValidationError, field_validator

COMPANY_NAMES = {
    "AAPL": "Apple Inc.",
    "MSFT": "Microsoft Corporation",
    "NVDA": "NVIDIA Corporation",
    "AMZN": "Amazon.com, Inc.",
    "GOOGL": "Alphabet Inc.",
}


class FilingRecord(BaseModel):
    ticker: str
    cik: str
    form: str
    filing_date: date
    report_date: date
    accession_number: str
    primary_document: str
    source_url: HttpUrl
    local_path: str

    @field_validator("ticker")
    @classmethod
    def known_ticker(cls, value: str) -> str:
        ticker = value.upper()
        if ticker not in COMPANY_NAMES:
            raise ValueError(f"Unsupported ticker: {ticker}")
        return ticker

    @field_validator("cik", "form", "accession_number", "local_path")
    @classmethod
    def required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Field cannot be empty")
        return value.strip()

    @property
    def company_name(self) -> str:
        return COMPANY_NAMES[self.ticker]

    @property
    def fiscal_year(self) -> int:
        return self.report_date.year


class FilingManifest(BaseModel):
    source: str
    generated_at_utc: str
    form: str
    downloaded_count: int = Field(ge=0)
    filings: list[FilingRecord]

    @field_validator("filings")
    @classmethod
    def unique_accession_numbers(
        cls, filings: list[FilingRecord]
    ) -> list[FilingRecord]:
        accession_numbers = [filing.accession_number for filing in filings]
        if len(accession_numbers) != len(set(accession_numbers)):
            raise ValueError("Manifest contains duplicate accession numbers")
        return filings


class ManifestError(ValueError):
    pass


def load_manifest(path: Path) -> FilingManifest:
    manifest_path = path.resolve()
    if not manifest_path.is_file():
        raise ManifestError(f"Manifest not found: {manifest_path}")

    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest = FilingManifest.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise ManifestError(f"Invalid manifest {manifest_path}: {exc}") from exc

    if manifest.downloaded_count != len(manifest.filings):
        raise ManifestError(
            "Manifest downloaded_count does not match the number of filing records"
        )

    downloads_dir = manifest_path.parent
    for filing in manifest.filings:
        resolve_filing_path(downloads_dir, filing)
    return manifest


def resolve_filing_path(downloads_dir: Path, filing: FilingRecord) -> Path:
    root = downloads_dir.resolve()
    local_path = Path(filing.local_path.replace("\\", "/"))
    candidate = (root / local_path).resolve()
    if not candidate.is_relative_to(root):
        raise ManifestError(
            f"Filing path escapes the downloads directory: {filing.local_path}"
        )
    if not candidate.is_file():
        raise ManifestError(
            f"Missing filing for {filing.accession_number}: {candidate}"
        )
    return candidate
