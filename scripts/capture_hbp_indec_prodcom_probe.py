from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


RUN_ID = "hbp-indec-prodcom-public-custody-probe-v0.1"
USER_AGENT = "BMA-HBP-public-custody-probe/0.1 (+research; bounded exact-source capture)"

SOURCES = [
    (
        "indec_ipi_landing_page.html",
        "https://www.indec.gob.ar/Nivel4/Tema/3/6/14",
    ),
    (
        "indec_ipi_2026_06_report.pdf",
        "https://www.indec.gob.ar/uploads/informesdeprensa/ipi_manufacturero_08_2683F2E17728.pdf",
    ),
    (
        "indec_ipi_series_2026.xls",
        "https://www.indec.gob.ar/ftp/cuadros/economia/sh_ipi_manufacturero_2026.xls",
    ),
    (
        "indec_ucii_landing_page.html",
        "https://www.indec.gob.ar/Nivel4/Tema/3/6/15",
    ),
    (
        "indec_ucii_2026_06_report.pdf",
        "https://www.indec.gob.ar/uploads/informesdeprensa/capacidad_08_26EE16AEA30D.pdf",
    ),
    (
        "eurostat_prodcom_es_16101035_2024_primary.json",
        "https://ec.europa.eu/eurostat/api/comext/dissemination/statistics/1.0/data/DS-059358?lang=en&reporter=ES&product=16101035&time=2024&indicators=PRODQNT&indicators=PQNTFLAG&indicators=QNTUNIT",
    ),
]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def capture(name: str, url: str, output_dir: Path) -> dict[str, object]:
    requested_at = datetime.now(timezone.utc).isoformat()
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    status: int | None = None
    final_url = url
    headers: dict[str, str] = {}
    error: str | None = None
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            status = response.status
            final_url = response.geturl()
            headers = dict(response.headers.items())
            body = response.read()
    except urllib.error.HTTPError as exc:
        status = exc.code
        final_url = exc.geturl()
        headers = dict(exc.headers.items()) if exc.headers else {}
        body = exc.read()
        error = f"HTTPError: {exc.code} {exc.reason}"
    except Exception as exc:  # exact failure is an evidence state
        body = str(exc).encode("utf-8")
        error = f"{type(exc).__name__}: {exc}"

    completed_at = datetime.now(timezone.utc).isoformat()
    raw_path = output_dir / name
    raw_path.write_bytes(body)
    header_path = output_dir / f"{name}.headers.json"
    header_payload = {
        "requested_url": url,
        "final_url": final_url,
        "requested_at_utc": requested_at,
        "completed_at_utc": completed_at,
        "http_status": status,
        "headers": headers,
        "error": error,
    }
    header_path.write_text(
        json.dumps(header_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "name": name,
        "requested_url": url,
        "final_url": final_url,
        "http_status": status,
        "error": error,
        "byte_count": len(body),
        "sha256": sha256_bytes(body),
        "headers_file": header_path.name,
        "headers_sha256": sha256_bytes(header_path.read_bytes()),
    }


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    prereg = repo / "preregistrations" / "HBP_INDEC_PRODCOM_PUBLIC_CUSTODY_PROBE_V0.1.json"
    output_dir = repo / "evidence" / "runs" / RUN_ID
    output_dir.mkdir(parents=True, exist_ok=False)

    prereg_bytes = prereg.read_bytes()
    records = [capture(name, url, output_dir) for name, url in SOURCES]
    manifest = {
        "run_id": RUN_ID,
        "classification": "OBSERVATIONAL_CUSTODY_AND_BOUNDED_SUPPORT_PROBE_NO_FITTING",
        "preregistration": str(prereg.relative_to(repo)).replace("\\", "/"),
        "preregistration_sha256": sha256_bytes(prereg_bytes),
        "records": records,
        "invariants": {
            "fit_performed": False,
            "forecast_performed": False,
            "score_performed": False,
            "historical_freeze_reconstructed": False,
            "cross_source_likelihood_pooling": False,
            "bulk_download": False,
        },
    }
    manifest_path = output_dir / "capture_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(f"capture_manifest_sha256={sha256_bytes(manifest_path.read_bytes())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
