import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const [inputPath, outputPath, sourceSha256, eventDate, sourceBytesText] = process.argv.slice(2);
if (!inputPath || !outputPath || !sourceSha256) {
  throw new Error("Usage: node extract_rmk_offer_v0_2.mjs input.xlsx output.json SHA256 event-date source-bytes");
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

  const rawStartingPrice = row[7];
  const hasStartingPrice =
    rawStartingPrice != null &&
    String(rawStartingPrice).trim() !== "" &&
    Number.isFinite(Number(rawStartingPrice));
  const quantity = Number(row[2]);
  if (Number.isFinite(quantity) && quantity > 0) {
    current.quantity_components.push({
      approximate_volume_m3: quantity,
      region: String(row[3] ?? current.advertised_region).trim(),
      starting_price_eur_m3: hasStartingPrice ? Number(rawStartingPrice) : null,
    });
  }
  const rawClass = row[6];
  const hasClass = rawClass != null && String(rawClass).trim() !== "";
  if (hasClass) {
    const classValue = String(rawClass).trim();
    const existingClass = current.price_classes.find((entry) => entry.diameter_or_class === classValue);
    if (!existingClass) {
      current.price_classes.push({
        diameter_or_class: classValue,
        starting_price_eur_m3: hasStartingPrice ? Number(rawStartingPrice) : null,
        quality_override: row[4] == null ? null : String(row[4]).trim(),
      });
    } else if (existingClass.starting_price_eur_m3 == null && hasStartingPrice) {
      existingClass.starting_price_eur_m3 = Number(rawStartingPrice);
    }
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
const locationComponentSums = {};
const locationRowCounts = {};
let currentObject = null;
for (const row of locationValues.slice(1)) {
  if (typeof row[0] === "number") currentObject = row[0];
  if (currentObject == null) continue;
  const key = String(currentObject);
  locationComponentSums[key] ??= 0;
  locationRowCounts[key] ??= {};
  const totalLabel = [row[1], row[2]]
    .map((value) => String(value ?? "").trim().toLocaleLowerCase("et"))
    .find((value) => value === "kokku");
  const rawQuantity = row[3];
  const quantity = Number(rawQuantity);
  const hasQuantity = rawQuantity !== null
    && rawQuantity !== undefined
    && String(rawQuantity).trim() !== ""
    && Number.isFinite(quantity);
  const location = String(row[2] ?? "").trim();
  if (totalLabel && hasQuantity) {
    locationTotals[key] = quantity;
  } else if (hasQuantity && location !== "" && quantity > 0) {
    locationComponentSums[key] += quantity;
    const rowKey = `${location}\u001f${quantity}`;
    locationRowCounts[key][rowKey] = (locationRowCounts[key][rowKey] ?? 0) + 1;
  }
}

for (const object of objects) {
  object.advertised_volume_m3 = object.quantity_components.reduce(
    (sum, component) => sum + component.approximate_volume_m3,
    0,
  );
  const key = String(object.object_id);
  object.location_sheet_total_m3 = locationTotals[key] ?? null;
  object.location_component_sum_m3 = locationComponentSums[key] ?? null;
  object.location_exact_duplicate_rows = Object.entries(locationRowCounts[key] ?? {})
    .filter(([, count]) => count > 1)
    .map(([rowKey, count]) => {
      const [location, quantity] = rowKey.split("\u001f");
      return { location, quantity_m3: Number(quantity), count };
    });
  if (object.location_exact_duplicate_rows.length > 0) {
    object.location_volume_state = "SOURCE_EXACT_DUPLICATE_LOCATION_ROWS";
  } else if (object.location_sheet_total_m3 != null && object.location_sheet_total_m3 !== object.advertised_volume_m3) {
    object.location_volume_state = "SOURCE_STATED_TOTAL_DISAGREEMENT";
  } else if (object.location_sheet_total_m3 != null && object.location_component_sum_m3 !== object.location_sheet_total_m3) {
    object.location_volume_state = "SOURCE_COMPONENT_SUM_DISAGREEMENT";
  } else if (object.location_sheet_total_m3 == null && object.location_component_sum_m3 !== object.advertised_volume_m3) {
    object.location_volume_state = "SOURCE_COMPONENT_SUM_WITHOUT_TOTAL_DISAGREEMENT";
  } else {
    object.location_volume_state = object.location_sheet_total_m3 == null
      ? "VERIFIED_COMPONENT_SUM_NO_STATED_TOTAL"
      : "VERIFIED_STATED_TOTAL_AND_COMPONENT_SUM";
  }
  object.location_total_matches = object.location_volume_state.startsWith("VERIFIED_");
}

const result = {
  schema_version: "bpm.rmk.offer-structured.v0.1",
  event_date: eventDate,
  source_file: inputPath,
  source_sha256: sourceSha256,
  source_bytes: Number(sourceBytesText),
  result_payload_opened: false,
  object_count: objects.length,
  advertised_volume_m3: objects.reduce((sum, object) => sum + object.advertised_volume_m3, 0),
  all_location_totals_match: objects.every((object) => object.location_total_matches === true),
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
