import fs from "node:fs/promises";
import crypto from "node:crypto";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const [inputPath, outputPath, sourceSha256, eventDate, sourceBytesText] = process.argv.slice(2);
if (!inputPath || !outputPath || !sourceSha256 || !eventDate || !sourceBytesText) {
  throw new Error("Usage: node extract_rmk_hakkpuit_offer_v0_2.mjs input.xlsx output.json SHA256 event_date source_bytes");
}

function parseDate(text) {
  const match = String(text).trim().match(/^(\d{1,2})\.(\d{1,2})\.(\d{4})$/);
  if (!match) throw new Error(`Unparseable delivery date: ${text}`);
  return new Date(Date.UTC(Number(match[3]), Number(match[2]) - 1, Number(match[1])));
}

function calendarPhase(period) {
  const parts = String(period).split(/\s+kuni\s+/iu);
  if (parts.length !== 2) throw new Error(`Unparseable delivery period: ${period}`);
  const start = parseDate(parts[0]);
  const end = parseDate(parts[1]);
  if (end < start) throw new Error("Invalid delivery chronology");
  const months = [];
  let year = start.getUTCFullYear();
  let month = start.getUTCMonth() + 1;
  while (year < end.getUTCFullYear() || (year === end.getUTCFullYear() && month <= end.getUTCMonth() + 1)) {
    months.push(month);
    if (month === 12) { year += 1; month = 1; } else { month += 1; }
  }
  return months.map((value) => `M${String(value).padStart(2, "0")}`).join("-");
}

function parseStartingPrices(text) {
  const normalized = String(text).replaceAll(",", ".");
  const numbers = [...normalized.matchAll(/(\d+(?:\.\d+)?)\s*EUR\s*\/\s*(m3|pm3|MWh)/giu)];
  if (numbers.length !== 3) throw new Error(`Unexpected starting-price encoding: ${text}`);
  const byUnit = Object.fromEntries(numbers.map((match) => [match[2].toLowerCase(), Number(match[1])]));
  return { eur_per_m3: byUnit.m3, eur_per_pm3: byUnit.pm3, eur_per_MWh_primary: byUnit.mwh };
}

const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(inputPath));
const offerValues = workbook.worksheets.getItem("pakkumuse vorm").getUsedRange(false).values;
const headerIndex = offerValues.findIndex((row) => String(row[0] ?? "").trim() === "Müügi-objekti nr");
if (headerIndex < 0) throw new Error("wood-chip offer header not found");
const row = offerValues[headerIndex + 1];
if (row[0] !== 1 || String(row[1]).trim() !== "Hakkpuit") throw new Error("unexpected wood-chip object identity");
const continuation = offerValues[headerIndex + 2];
const quality = String(row[4]).trim();
const measurementFingerprint = crypto.createHash("sha256").update(quality, "utf8").digest("hex").toUpperCase();
const locationValues = workbook.worksheets.getItem("Asukoht").getUsedRange(false).values;
const locationComponents = locationValues.slice(1)
  .filter((item) => String(item[2] ?? "").trim() !== "" && Number(item[3]) > 0)
  .map((item) => ({ region: String(item[1] ?? "").trim(), location: String(item[2]).trim(), volume_m3: Number(item[3]) }));
const locationVolume = locationComponents.reduce((sum, item) => sum + item.volume_m3, 0);
const statedTotal = Number(locationValues[1]?.[4]);
const result = {
  schema_version: "bpm.rmk.hakkpuit-offer-structured.v0.2",
  event_date: eventDate,
  source_file: inputPath,
  source_sha256: sourceSha256,
  source_bytes: Number(sourceBytesText),
  result_payload_opened: false,
  object_id: 1,
  product: "Hakkpuit",
  advertised_volume_m3: Number(row[2]),
  location_sheet_volume_m3: locationVolume,
  location_sheet_stated_total_m3: statedTotal,
  location_total_matches: Number(row[2]) === locationVolume && locationVolume === statedTotal,
  location_components: locationComponents,
  advertised_region: String(row[3]).trim(),
  quality_and_measurement_standard: quality,
  measurement_fingerprint_sha256: measurementFingerprint,
  delivery_period: String(row[5]).trim(),
  exact_calendar_phase: calendarPhase(row[5]),
  starting_price_regions: [
    { scope: "HIIUMAA_SAAREMAA_MUHUMAA", ...parseStartingPrices(row[6]) },
    { scope: "MAINLAND_EDELA_PARNUMAA_LAANEMAA", ...parseStartingPrices(continuation[6]) }
  ],
  frozen_conversions: { m3_to_pm3: 2.78, m3_to_MWh_primary: 2.22 },
  destination_at_offer: null
};
await fs.writeFile(outputPath, JSON.stringify(result, null, 2) + "\n", "utf8");
console.log(JSON.stringify({ outputPath, volumeM3: result.advertised_volume_m3, locationTotalMatches: result.location_total_matches, phase: result.exact_calendar_phase, fingerprint: result.measurement_fingerprint_sha256 }, null, 2));
