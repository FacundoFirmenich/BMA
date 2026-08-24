import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const [inputPath, outputPath, sourceSha256] = process.argv.slice(2);
if (!inputPath || !outputPath || !sourceSha256) {
  throw new Error("Usage: node extract_rmk_offer_v0_1.mjs input.xlsx output.json SHA256");
}

const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(inputPath));
const sheet = workbook.worksheets.getItem("Müügiobjektid");
const values = sheet.getUsedRange(false).values;
const headerIndex = values.findIndex((row) => String(row[0] ?? "").trim() === "Müügi-objekti nr");
if (headerIndex < 0) throw new Error("offer header not found");

const objects = [];
let current = null;
for (let index = headerIndex + 1; index < values.length; index += 1) {
  const row = values[index];
  const first = row[0];
  if (typeof first === "string" && first.trim().startsWith("*)")) break;
  if (typeof first === "number") {
    current = {
      object_id: first,
      product: String(row[1] ?? "").trim(),
      advertised_region: String(row[3] ?? "").trim(),
      quality_and_measurement_standard: String(row[4] ?? "").trim(),
      delivery_period: String(row[5] ?? "").trim(),
      quantity_components: [],
      price_classes: [],
    };
    objects.push(current);
  }
  if (!current) continue;

  const quantity = Number(row[2]);
  if (Number.isFinite(quantity) && quantity > 0) {
    current.quantity_components.push({
      approximate_volume_m3: quantity,
      region: String(row[3] ?? current.advertised_region).trim(),
      starting_price_eur_m3: Number.isFinite(Number(row[7])) ? Number(row[7]) : null,
    });
  }
  if (row[6] != null || Number.isFinite(Number(row[7]))) {
    current.price_classes.push({
      diameter_or_class: row[6] == null ? null : String(row[6]).trim(),
      starting_price_eur_m3: Number.isFinite(Number(row[7])) ? Number(row[7]) : null,
      quality_override: row[4] == null ? null : String(row[4]).trim(),
    });
  }
}

const notes = values
  .slice(headerIndex + 1)
  .map((row) => row[0])
  .filter((value) => typeof value === "string" && (value.trim().startsWith("*)") || value.trim().startsWith("**")))
  .map((value) => value.trim());

const locationSheet = workbook.worksheets.getItem("asukoht");
const locationValues = locationSheet.getUsedRange(false).values;
const locationTotals = {};
let currentObject = null;
for (const row of locationValues.slice(1)) {
  if (typeof row[0] === "number") currentObject = row[0];
  if (currentObject == null) continue;
  if (String(row[2] ?? "").trim() === "Kokku" && Number.isFinite(Number(row[3]))) {
    locationTotals[String(currentObject)] = Number(row[3]);
  }
}

for (const object of objects) {
  object.advertised_volume_m3 = object.quantity_components.reduce(
    (sum, component) => sum + component.approximate_volume_m3,
    0,
  );
  object.location_sheet_total_m3 = locationTotals[String(object.object_id)] ?? null;
  object.location_total_matches =
    object.location_sheet_total_m3 == null || object.location_sheet_total_m3 === object.advertised_volume_m3;
}

const result = {
  schema_version: "bpm.rmk.offer-structured.v0.1",
  event_date: "2025-02-26",
  source_file: inputPath,
  source_sha256: sourceSha256,
  source_bytes: 56041,
  result_payload_opened: false,
  object_count: objects.length,
  advertised_volume_m3: objects.reduce((sum, object) => sum + object.advertised_volume_m3, 0),
  all_location_totals_match: objects.every((object) => object.location_total_matches),
  objects,
  notes,
};

await fs.mkdir(new URL(".", `file:///${outputPath.replaceAll("\\", "/")}`).pathname, { recursive: true }).catch(() => {});
await fs.writeFile(outputPath, JSON.stringify(result, null, 2) + "\n", "utf8");
console.log(JSON.stringify({
  outputPath,
  objectCount: result.object_count,
  advertisedVolumeM3: result.advertised_volume_m3,
  allLocationTotalsMatch: result.all_location_totals_match,
  noteCount: notes.length,
}, null, 2));
