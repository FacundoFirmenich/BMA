import fs from "node:fs/promises";
import crypto from "node:crypto";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const [inputPath, offerPath, outputPath, sourceSha256, eventDate, protocolDate, sourceBytesText, freezePath] = process.argv.slice(2);
if (!freezePath) throw new Error("freeze path required");
const offer = JSON.parse(await fs.readFile(offerPath, "utf8"));
const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(inputPath));
const values = workbook.worksheets.getItem("protokoll").getUsedRange(false).values;
const headerIndex = values.findIndex((row) => String(row[0] ?? "").trim() === "Müügi-objekt");
if (headerIndex < 0) throw new Error("wood-chip result header not found");
const factor = offer.frozen_conversions.m3_to_pm3;
const rows = values.slice(headerIndex + 1).filter((row) => typeof row[0] === "number").map((row) => {
  if (row[0] !== offer.object_id || String(row[1]).trim() !== offer.product) throw new Error("wood-chip result identity mismatch");
  const volumePm3 = Number(row[4]);
  const pricePm3 = Number(row[5]);
  if (!(volumePm3 > 0) || !(pricePm3 > 0)) throw new Error("wood-chip result numeric encoding failure");
  return {
    object_id: row[0], product: offer.product, buyer: String(row[2]).trim(), destination: String(row[3]).trim(),
    awarded_volume_pm3: volumePm3, awarded_price_eur_pm3: pricePm3,
    awarded_volume_m3: volumePm3 / factor, effective_weighted_price_eur_m3: pricePm3 * factor,
    price_state: "ESTIMABLE_OFFER_FROZEN_UNIT_CONVERSION"
  };
});
const result = {
  schema_version: "bpm.rmk.hakkpuit-result-structured.v0.2",
  event_date: eventDate,
  protocol_date: protocolDate,
  source_file: inputPath,
  source_sha256: sourceSha256,
  source_bytes: Number(sourceBytesText),
  structured_offer_used_sha256: crypto.createHash("sha256").update(await fs.readFile(offerPath)).digest("hex").toUpperCase(),
  freeze_used_sha256: crypto.createHash("sha256").update(await fs.readFile(freezePath)).digest("hex").toUpperCase(),
  conversion_source: "OFFER_FROZEN_BEFORE_RESULT",
  conversion_m3_to_pm3: factor,
  award_row_count: rows.length,
  total_awarded_volume_pm3: rows.reduce((sum, row) => sum + row.awarded_volume_pm3, 0),
  total_awarded_volume_m3: rows.reduce((sum, row) => sum + row.awarded_volume_m3, 0),
  approximate_offer_volume_m3: offer.advertised_volume_m3,
  approximate_coverage_ratio: rows.reduce((sum, row) => sum + row.awarded_volume_m3, 0) / offer.advertised_volume_m3,
  coverage_state: "DIAGNOSTIC_ONLY_APPROXIMATE_OFFER_AND_UNIT_ROUNDING",
  extraction_failures: [],
  local_outcomes: rows.map((row) => ({
    object_id: row.object_id, product: row.product,
    measurement_fingerprint_sha256: offer.measurement_fingerprint_sha256,
    destination: row.destination, buyers: [row.buyer], delivery_period: offer.delivery_period,
    calendar_phase: offer.exact_calendar_phase, awarded_volume_m3: row.awarded_volume_m3,
    effective_weighted_price_eur_m3: row.effective_weighted_price_eur_m3,
    original_volume_pm3: row.awarded_volume_pm3, original_price_eur_pm3: row.awarded_price_eur_pm3,
    price_state: row.price_state
  }))
};
await fs.writeFile(outputPath, JSON.stringify(result, null, 2) + "\n", "utf8");
console.log(JSON.stringify({ rows: rows.length, totalPm3: result.total_awarded_volume_pm3, totalM3: result.total_awarded_volume_m3, coverage: result.approximate_coverage_ratio }, null, 2));
