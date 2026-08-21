import fs from "node:fs/promises";
import crypto from "node:crypto";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const [inputPath, offerPath, outputPath, sourceSha256] = process.argv.slice(2);
if (!inputPath || !offerPath || !outputPath || !sourceSha256) {
  throw new Error("Usage: node extract_rmk_result_v0_1.mjs result.xlsx offer.json output.json SHA256");
}

const offer = JSON.parse(await fs.readFile(offerPath, "utf8"));
const offerById = new Map(offer.objects.map((object) => [object.object_id, object]));
const classWeights = new Map([
  [1, [0.07, 0.20, 0.13, 0.01, 0.59]],
  [2, [0.70, 0.30]],
  [3, [0.16, 0.50, 0.34]],
  [21, [0.10, 0.12, 0.02, 0.65, 0.11]],
]);

const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(inputPath));
const sheet = workbook.worksheets.getItem("protokoll");
const values = sheet.getUsedRange(false).values;
const headerIndex = values.findIndex((row) => String(row[0] ?? "").trim() === "Müügi-objekt");
if (headerIndex < 0) throw new Error("result header not found");

const rows = [];
const failures = [];
for (const row of values.slice(headerIndex + 1)) {
  if (typeof row[0] !== "number") continue;
  const objectId = row[0];
  const object = offerById.get(objectId);
  if (!object) {
    failures.push({ object_id: objectId, state: "RESULT_OBJECT_NOT_IN_FROZEN_OFFER" });
    continue;
  }
  const volume = Number(row[4]);
  const rawPrice = row[5];
  let weightedPrice = null;
  let priceState = "ESTIMABLE_EXACT_DESTINATION_FALLBACK";
  let priceComponents = null;
  if (typeof rawPrice === "number" && Number.isFinite(rawPrice)) {
    weightedPrice = rawPrice;
  } else if (typeof rawPrice === "string" && rawPrice.includes("/")) {
    priceComponents = rawPrice.split("/").map((value) => Number(value.replace(",", ".")));
    const weights = classWeights.get(objectId);
    if (!weights || weights.length !== priceComponents.length || priceComponents.some((value) => !Number.isFinite(value))) {
      priceState = "NOT_ESTIMABLE_CLASS_VECTOR_MAP";
      failures.push({ object_id: objectId, raw_price: rawPrice, state: priceState });
    } else {
      weightedPrice = priceComponents.reduce((sum, value, index) => sum + value * weights[index], 0);
    }
  } else {
    priceState = "NOT_ESTIMABLE_PRICE_ENCODING";
    failures.push({ object_id: objectId, raw_price: rawPrice, state: priceState });
  }
  rows.push({
    object_id: objectId,
    product: String(row[1] ?? "").trim(),
    buyer: String(row[2] ?? "").trim(),
    destination: String(row[3] ?? "").trim(),
    awarded_volume_m3: volume,
    raw_price: rawPrice,
    price_components: priceComponents,
    effective_weighted_price_eur_m3: weightedPrice,
    price_state: priceState,
  });
}

const groups = new Map();
for (const row of rows) {
  const key = `${row.object_id}\u001f${row.destination}`;
  if (!groups.has(key)) {
    groups.set(key, {
      object_id: row.object_id,
      product: row.product,
      destination: row.destination,
      buyers: new Set(),
      awarded_volume_m3: 0,
      price_volume_sum: 0,
      price_volume_support_m3: 0,
      source_rows: 0,
    });
  }
  const group = groups.get(key);
  group.buyers.add(row.buyer);
  group.awarded_volume_m3 += row.awarded_volume_m3;
  group.source_rows += 1;
  if (row.effective_weighted_price_eur_m3 != null) {
    group.price_volume_sum += row.effective_weighted_price_eur_m3 * row.awarded_volume_m3;
    group.price_volume_support_m3 += row.awarded_volume_m3;
  }
}

const localOutcomes = [];
for (const group of groups.values()) {
  const object = offerById.get(group.object_id);
  const classDescriptor = JSON.stringify({
    quality: object.quality_and_measurement_standard,
    price_classes: object.price_classes.map((entry) => entry.diameter_or_class),
    class_weights: classWeights.get(group.object_id) ?? null,
  });
  const measurementFingerprint = crypto.createHash("sha256").update(classDescriptor, "utf8").digest("hex").toUpperCase();
  localOutcomes.push({
    object_id: group.object_id,
    product: group.product,
    destination: group.destination,
    buyers: [...group.buyers].sort(),
    delivery_period: object.delivery_period,
    measurement_fingerprint_sha256: measurementFingerprint,
    awarded_volume_m3: group.awarded_volume_m3,
    effective_weighted_price_eur_m3:
      group.price_volume_support_m3 === group.awarded_volume_m3
        ? group.price_volume_sum / group.awarded_volume_m3
        : null,
    price_state:
      group.price_volume_support_m3 === group.awarded_volume_m3
        ? "ESTIMABLE_EXACT_DESTINATION_FALLBACK"
        : "NOT_ESTIMABLE_PARTIAL_PRICE_SUPPORT",
    source_rows: group.source_rows,
  });
}

const objectTotals = [];
for (const object of offer.objects) {
  const resultRows = rows.filter((row) => row.object_id === object.object_id);
  const awarded = resultRows.reduce((sum, row) => sum + row.awarded_volume_m3, 0);
  objectTotals.push({
    object_id: object.object_id,
    product: object.product,
    offer_volume_m3: object.advertised_volume_m3,
    location_sheet_volume_m3: object.location_sheet_total_m3,
    awarded_volume_m3: awarded,
    coverage_offer_denominator: object.location_total_matches ? awarded / object.advertised_volume_m3 : null,
    coverage_location_sheet_denominator: object.location_total_matches ? awarded / object.location_sheet_total_m3 : null,
    state: object.location_total_matches ? "ADJUDICABLE" : "NOT_ESTIMABLE_SOURCE_VOLUME_DISAGREEMENT",
  });
}

const result = {
  schema_version: "bpm.rmk.result-structured.v0.1",
  event_date: "2025-02-26",
  protocol_date: "2025-03-03",
  source_file: inputPath,
  source_sha256: sourceSha256,
  source_bytes: 28757,
  frozen_offer_sha256: offer.source_sha256,
  award_row_count: rows.length,
  local_outcome_count: localOutcomes.length,
  total_awarded_volume_m3: rows.reduce((sum, row) => sum + row.awarded_volume_m3, 0),
  price_mapping_failures: failures,
  rows,
  local_outcomes: localOutcomes,
  object_totals: objectTotals,
};

await fs.writeFile(outputPath, JSON.stringify(result, null, 2) + "\n", "utf8");
console.log(JSON.stringify({
  outputPath,
  awardRows: result.award_row_count,
  localOutcomes: result.local_outcome_count,
  totalAwardedVolumeM3: result.total_awarded_volume_m3,
  priceMappingFailures: failures.length,
  unawardedObjects: objectTotals.filter((item) => item.awarded_volume_m3 === 0).map((item) => item.object_id),
}, null, 2));
