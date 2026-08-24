import fs from "node:fs/promises";
import crypto from "node:crypto";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const [inputPath, outputPath, sourceSha256] = process.argv.slice(2);
const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(inputPath));
const sheet = workbook.worksheets.getItem("pakkumuse vorm");
const values = sheet.getUsedRange(false).values;
const headerIndex = values.findIndex((row) => String(row[0] ?? "").trim() === "Müügi-objekti nr");
if (headerIndex < 0) throw new Error("wood-chip offer header not found");
const row = values[headerIndex + 1];
if (row[0] !== 1 || String(row[1]).trim() !== "Hakkpuit") throw new Error("unexpected wood-chip object identity");
const quality = String(row[4]).trim();
const measurementFingerprint = crypto.createHash("sha256").update(quality, "utf8").digest("hex").toUpperCase();
const locationSheet = workbook.worksheets.getItem("Asukoht").getUsedRange(false).values;
const locationVolume = locationSheet.slice(1).reduce((sum, item) => sum + (Number(item[3]) || 0), 0);
const result = {
  schema_version: "bpm.rmk.hakkpuit-offer-structured.v0.1",
  event_date: "2025-03-20",
  source_file: inputPath,
  source_sha256: sourceSha256,
  source_bytes: 25449,
  result_payload_opened: false,
  object_id: 1,
  product: "Hakkpuit",
  advertised_volume_m3: Number(row[2]),
  location_sheet_volume_m3: locationVolume,
  location_total_matches: Number(row[2]) === locationVolume,
  advertised_region: String(row[3]).trim(),
  quality_and_measurement_standard: quality,
  measurement_fingerprint_sha256: measurementFingerprint,
  delivery_period: String(row[5]).trim(),
  exact_calendar_phase: "M04-M05-M06",
  starting_prices: {
    eur_per_m3: 48.65,
    eur_per_pm3: 17.50,
    eur_per_MWh_primary: 21.91,
  },
  frozen_conversions: {
    m3_to_pm3: 2.78,
    m3_to_MWh_primary: 2.22,
  },
  destination_at_offer: null,
};
await fs.writeFile(outputPath, JSON.stringify(result, null, 2) + "\n", "utf8");
console.log(JSON.stringify({ outputPath, volumeM3: result.advertised_volume_m3, locationTotalMatches: result.location_total_matches, phase: result.exact_calendar_phase }, null, 2));
