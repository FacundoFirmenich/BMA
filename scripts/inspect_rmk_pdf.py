from __future__ import annotations

import argparse
import json
from pathlib import Path

import pypdfium2 as pdfium
import pdfplumber


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", type=Path)
    parser.add_argument("render_dir", type=Path)
    args = parser.parse_args()

    args.render_dir.mkdir(parents=True, exist_ok=True)
    with pdfplumber.open(args.pdf) as pdf:
        extracted = [page.extract_text(x_tolerance=2, y_tolerance=3) or "" for page in pdf.pages]

    document = pdfium.PdfDocument(args.pdf)
    rendered = []
    for index in range(len(document)):
        page = document[index]
        output = args.render_dir / f"page-{index + 1:03d}.png"
        page.render(scale=2).to_pil().save(output)
        rendered.append(str(output))

    lines = [line.strip() for text in extracted for line in text.splitlines() if line.strip()]
    result = {
        "pdf": str(args.pdf),
        "pages": len(extracted),
        "rendered": rendered,
        "first_40_lines": lines[:40],
        "last_20_lines": lines[-20:],
        "product_header_hits": sum("Metsamaterjali nimetus" in line for line in lines),
        "volume_header_hits": sum("Maht" in line and "m³" in line for line in lines),
        "price_header_hits": sum("hind" in line.lower() and "m³" in line for line in lines),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
