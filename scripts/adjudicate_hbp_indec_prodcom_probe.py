from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pdfplumber


RUN_ID = "hbp-indec-prodcom-public-custody-probe-v0.1"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def extract_pdf_text(path: Path) -> str:
    with pdfplumber.open(path) as document:
        return "\n\n".join((page.extract_text() or "") for page in document.pages)


def require(pattern: str, text: str, label: str) -> None:
    if re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL) is None:
        raise ValueError(f"Required source evidence not found: {label}")


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    run_dir = repo / "evidence" / "runs" / RUN_ID
    capture_manifest_path = run_dir / "capture_manifest.json"
    capture_manifest = json.loads(capture_manifest_path.read_text(encoding="utf-8"))

    for record in capture_manifest["records"]:
        raw = run_dir / record["name"]
        observed = sha256_bytes(raw.read_bytes())
        if observed != record["sha256"]:
            raise ValueError(f"Raw hash mismatch for {record['name']}: {observed}")

    ipi_pdf = run_dir / "indec_ipi_2026_06_report.pdf"
    ucii_pdf = run_dir / "indec_ucii_2026_06_report.pdf"
    ipi_text = extract_pdf_text(ipi_pdf)
    ucii_text = extract_pdf_text(ucii_pdf)
    ipi_text_path = run_dir / "indec_ipi_2026_06_report.pdf.pdfplumber.txt"
    ucii_text_path = run_dir / "indec_ucii_2026_06_report.pdf.pdfplumber.txt"
    ipi_text_path.write_text(ipi_text, encoding="utf-8")
    ucii_text_path.write_text(ucii_text, encoding="utf-8")

    require(r"7 de agosto de 2026", ipi_text, "IPI publication date")
    require(r"Junio\s+119,9\s+2,0\s+-2,2\s+119,1\s+0,9\s+118,9", ipi_text, "IPI June general row")
    require(r"nueve de las diecis.{0,4}is divisiones", ipi_text, "IPI nine of sixteen divisions rising")
    require(r"20-22\s+Madera, papel, edici.{0,4}n e impresi.{0,4}n\s+102,9\s+8,4\s+3,7\s+8,4", ipi_text, "IPI wood-paper-printing row")
    require(r"20100/210/220/230/290\s+87,9\s+17,3\s+9,2\s+3,5", ipi_text, "IPI wood products row")

    require(r"14 de agosto de 2026", ucii_text, "UCII publication date")
    require(r"Junio\s+59,1", ucii_text, "UCII June 2026 row")
    require(r"mismo mes de 2025.{0,80}58,9", ucii_text, "UCII June 2025 comparator")
    require(r"panel de entre 600\s*y 700 empresas", ucii_text, "UCII panel size")
    require(r"Refinaci.{0,4}n del petr.{0,4}leo\s+86,7", ucii_text, "UCII refinery sector")
    require(r"Industrias met.{0,4}licas b.{0,4}sicas\s+68,7", ucii_text, "UCII basic metals sector")
    require(r"Industria automotriz\s+45,5", ucii_text, "UCII automotive sector")

    prodcom_path = run_dir / "eurostat_prodcom_es_16101035_2024_primary.json"
    prodcom = json.loads(prodcom_path.read_text(encoding="utf-8"))
    expected_id = ["freq", "reporter", "product", "indicators", "time"]
    if prodcom.get("id") != expected_id or prodcom.get("size") != [1, 1, 1, 3, 1]:
        raise ValueError("Prodcom bounded cube shape differs from preregistration")
    if prodcom["dimension"]["reporter"]["category"]["index"] != {"ES": 0}:
        raise ValueError("Prodcom reporter is not Spain-only")
    if prodcom["dimension"]["product"]["category"]["index"] != {"16101035": 0}:
        raise ValueError("Prodcom product is not 16101035-only")
    if prodcom["dimension"]["time"]["category"]["index"] != {"2024": 0}:
        raise ValueError("Prodcom year is not 2024-only")
    if prodcom.get("value") != {}:
        raise ValueError("Prodcom selected cell unexpectedly contains a value; adjudication must be reviewed")

    adjudication = {
        "run_id": RUN_ID,
        "classification": "OBSERVATIONAL_CUSTODY_AND_BOUNDED_SUPPORT_PROBE_NO_FITTING",
        "raw_integrity": "PASS_ALL_CAPTURE_HASHES_RECOMPUTED",
        "indec_ipi": {
            "status": "PASS_CURRENT_VINTAGE_OBSERVATIONAL_CUSTODY",
            "publication_date": "2026-08-07",
            "reference_period": "2026-06",
            "provisional": True,
            "national_general": {
                "original_index_base_2004_100": 119.9,
                "year_over_year_percent": 2.0,
                "year_to_date_percent": -2.2,
                "seasonally_adjusted_index": 119.1,
                "month_over_month_percent": 0.9,
                "trend_cycle_index": 118.9,
                "trend_cycle_month_over_month_percent": -0.0
            },
            "division_breadth": {"rising": 9, "total": 16, "falling": 7},
            "wood_evidence": {
                "aggregate_code": "20-22",
                "aggregate_label": "Madera, papel, edición e impresión",
                "aggregate_index_base_2004_100": 102.9,
                "aggregate_year_over_year_percent": 8.4,
                "aggregate_year_to_date_percent": 3.7,
                "wood_codes": "20100/210/220/230/290",
                "wood_label": "Madera y productos de madera y corcho, excepto muebles",
                "wood_index_base_2004_100": 87.9,
                "wood_year_over_year_percent": 17.3,
                "wood_year_to_date_percent": 9.2,
                "wood_contribution_percentage_points": 3.5
            },
            "support": "MONTHLY_MANUFACTURING_OUTCOME_WITH_DIVISION_AND_SUBCLASS_DETAIL",
            "limits": [
                "Current vintage observed after release; not a causal holdout",
                "Report table exposes 18 monthly national rows, below the preregistered 36-month forecasting minimum",
                "The official full-series XLS is preserved but its legacy binary format is not readable by the bundled OpenXML tool or local Excel automation",
                "Activity/subclass indices are not product-level transaction quantities"
            ],
            "forecast_authority": "ABSTAIN_UNTIL_STRUCTURED_SERIES_OR_FUTURE_FREEZE"
        },
        "indec_ucii": {
            "status": "PASS_CURRENT_VINTAGE_OBSERVATIONAL_CUSTODY",
            "publication_date": "2026-08-14",
            "reference_period": "2026-06",
            "provisional": True,
            "general_capacity_utilization_percent": 59.1,
            "year_ago_percent": 58.9,
            "sector_examples_percent": {
                "refinacion_del_petroleo": 86.7,
                "industrias_metalicas_basicas": 68.7,
                "sustancias_y_productos_quimicos": 67.0,
                "papel_y_carton": 66.2,
                "productos_alimenticios_y_bebidas": 64.4,
                "industria_automotriz": 45.5,
                "metalmecanica_excepto_automotores": 41.5,
                "productos_de_caucho_y_plastico": 41.0
            },
            "survey_panel_companies": "600-700",
            "support": "MONTHLY_CAPACITY_STATE_OBSERVER_BY_INDUSTRIAL_BLOCK",
            "limits": [
                "Capacity utilization is not output quantity and cannot replace IPI or product observations",
                "Current vintage observed after release; not a causal holdout",
                "Food excludes wine and sugar capacity; chemicals excludes pharmaceuticals",
                "No likelihood pooling with IPI, Eurostat STS or Prodcom"
            ],
            "forecast_authority": "OBSERVER_ONLY_UNTIL_SEPARATE_CAUSAL_PREREGISTRATION"
        },
        "eurostat_prodcom": {
            "status": "NOT_ESTIMABLE_NO_CELL",
            "dataset": "DS-059358",
            "updated": prodcom["updated"],
            "reporter": "ES",
            "product": "16101035",
            "product_label": prodcom["dimension"]["product"]["category"]["label"]["16101035"],
            "reference_year": "2024",
            "requested_indicators": ["PRODQNT", "QNTUNIT", "PQNTFLAG"],
            "published_value_count": len(prodcom["value"]),
            "support": "PRODUCT_IDENTITY_CONFIRMED_BUT_SELECTED_PHYSICAL_CELL_EMPTY",
            "limits": [
                "No quantity, unit or flag is published for the selected Spain-product-year cell",
                "The empty result is retained; no post-hoc product substitution is allowed",
                "Annual revised support cannot serve as a monthly outcome"
            ]
        },
        "coral_adjudication": {
            "position_change": "BETTER_OBSERVATIONAL_CUSTODY_BUT_NO_NEW_CAUSAL_SCORE",
            "quantitative_jump": "Argentina now contributes a verified monthly national outcome, 16 manufacturing divisions/subclasses and a 12-block capacity observer; these are separate panels, not pooled observations.",
            "qualitative_jump": "Wood is now visible both as a real Argentine manufacturing subclass outcome and as an explicit Eurostat product identity. Only the Argentine report contains a published magnitude in this probe.",
            "forbidden_claims": [
                "global winner",
                "Argentina prospective validation",
                "Prodcom physical quantity support for ES product 16101035 in 2024",
                "historical first-release freeze recovery",
                "cross-source likelihood pooling"
            ],
            "next_decision_critical_action": "Freeze a new independent Argentina forecast only after a machine-readable series with at least 36 contiguous months is available; select any further Prodcom product before querying it and preserve empty/confidential outcomes."
        },
        "derived_files": {
            "ipi_pdfplumber_text": ipi_text_path.name,
            "ipi_pdfplumber_text_sha256": sha256_bytes(ipi_text_path.read_bytes()),
            "ucii_pdfplumber_text": ucii_text_path.name,
            "ucii_pdfplumber_text_sha256": sha256_bytes(ucii_text_path.read_bytes()),
            "workbook_inspection": "indec_ipi_series_2026_workbook_inspection.json",
            "workbook_inspection_status": "BLOCKED_LEGACY_XLS_READER_UNAVAILABLE"
        },
        "invariants": capture_manifest["invariants"],
    }

    output = run_dir / "probe_adjudication.json"
    output.write_text(json.dumps(adjudication, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(adjudication, ensure_ascii=False, indent=2))
    print(f"probe_adjudication_sha256={sha256_bytes(output.read_bytes())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

