import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const [inputPath, offerPath, outputPath, sourceSha256] = process.argv.slice(2);
const offer = JSON.parse(await fs.readFile(offerPath, "utf8"));
const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(inputPath));
const values = workbook.worksheets.getItem("protokoll").getUsedRange(false).values;
const headerIndex = values.findIndex((row) => String(row[0] ?? "").trim() === "Müügi-objekt");
const rows = values.slice(headerIndex + 1).filter((row) => typeof row[0] === "number").map((row) => ({
  object_id: row[0],
  product: String(row[1]).trim(),
  buyer: String(row[2]).trim(),
  destination: String(row[3]).trim(),
  awarded_volume_pm3: Number(row[4]),
  awarded_price_eur_pm3: Number(row[5]),
  awarded_volume_m3: Number(row[4]) / offer.frozen_conversions.m3_to_pm3,
  awarded_price_eur_m3: Number(row[5]) * offer.frozen_conversions.m3_to_pm3,
}));
if (rows.length !== 2 || rows.some((row) => row.product !== "Hakkpuit")) throw new Error("unexpected wood-chip result schema");
const totalPm3 = rows.reduce((sum, row) => sum + row.awarded_volume_pm3, 0);
const totalM3 = rows.reduce((sum, row) => sum + row.awarded_volume_m3, 0);
const result = {
  schema_version: "bpm.rmk.hakkpuit-result-structured.v0.1",
  event_date: "2025-03-20",
  protocol_date: "2025-03-24",
  source_file: inputPath,
  source_sha256: sourceSha256,
  source_bytes: 22882,
  frozen_offer_sha256: offer.source_sha256,
  conversion_source: "OFFER_FROZEN_BEFORE_RESULT",
  conversion_m3_to_pm3: offer.frozen_conversions.m3_to_pm3,
  award_row_count: rows.length,
  total_awarded_volume_pm3: totalPm3,
  total_awarded_volume_m3: totalM3,
  approximate_offer_volume_m3: offer.advertised_volume_m3,
  approximate_coverage_ratio: totalM3 / offer.advertised_volume_m3,
  coverage_state: "DIAGNOSTIC_ONLY_APPROXIMATE_OFFER_AND_UNIT_ROUNDING",
  local_outcomes: rows.map((row) => ({
    product: row.product,
    measurement_fingerprint_sha256: offer.measurement_fingerprint_sha256,
    destination: row.destination,
    buyer: row.buyer,
    delivery_period: offer.delivery_period,
    calendar_phase: offer.exact_calendar_phase,
    awarded_volume_m3: row.awarded_volume_m3,
    awarded_price_eur_m3: row.awarded_price_eur_m3,
    original_volume_pm3: row.awarded_volume_pm3,
    original_price_eur_pm3: row.awarded_price_eur_pm3,
  })),
};
await fs.writeFile(outputPath, JSON.stringify(result, null, 2) + "\n", "utf8");
console.log(JSON.stringify({ outputPath, rows: rows.length, totalPm3, totalM3, approximateCoverageRatio: result.approximate_coverage_ratio }, null, 2));
