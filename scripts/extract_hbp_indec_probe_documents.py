from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from pypdf import PdfReader


RUN_ID = "hbp-indec-prodcom-public-custody-probe-v0.1"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def extract_pdf(path: Path) -> dict[str, object]:
    reader = PdfReader(path)
    page_text = [(page.extract_text() or "") for page in reader.pages]
    full_text = "\n\n".join(page_text)
    text_path = path.with_suffix(path.suffix + ".extracted.txt")
    text_path.write_text(full_text, encoding="utf-8")
    return {
        "source_file": path.name,
        "source_sha256": sha256_bytes(path.read_bytes()),
        "page_count": len(reader.pages),
        "metadata": {str(k): str(v) for k, v in (reader.metadata or {}).items()},
        "extracted_text_file": text_path.name,
        "extracted_text_sha256": sha256_bytes(text_path.read_bytes()),
        "first_page_normalized_excerpt": normalize(page_text[0])[:2500] if page_text else "",
    }


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    run_dir = repo / "evidence" / "runs" / RUN_ID
    pdfs = [
        run_dir / "indec_ipi_2026_06_report.pdf",
        run_dir / "indec_ucii_2026_06_report.pdf",
    ]
    payload = {
        "classification": "READ_ONLY_PDF_TEXT_EXTRACTION_NO_TRANSFORMATION_OF_RAW_BYTES",
        "documents": [extract_pdf(path) for path in pdfs],
    }
    output = run_dir / "indec_document_inspection.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
