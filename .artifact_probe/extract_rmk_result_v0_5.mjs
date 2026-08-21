import fs from "node:fs/promises";
import crypto from "node:crypto";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const [inputPath, offerPath, outputPath, sourceSha256, eventDate, protocolDate, sourceBytesText, quarantinedResultUrl = "", freezePath = "", classWeightsPath = ""] = process.argv.slice(2);
if (!inputPath || !offerPath || !outputPath || !sourceSha256 || !eventDate || !protocolDate || !sourceBytesText) {
  throw new Error("Usage: node extract_rmk_result_v0_2.mjs result.xlsx offer.json output.json SHA256 event_date protocol_date source_bytes");
}

const offer = JSON.parse(await fs.readFile(offerPath, "utf8"));
const offerById = new Map(offer.objects.map((object) => [object.object_id, object]));
const freeze = freezePath ? JSON.parse(await fs.readFile(freezePath, "utf8")) : null;
const invalidDeliveryObjectIds = new Set(freeze?.invalid_delivery_period_objects ?? []);
const sourceVolumeConflictObjectIds = new Set(freeze?.source_volume_conflict_objects ?? []);
const classWeights = classWeightsPath ? JSON.parse(await fs.readFile(classWeightsPath, "utf8")) : { weights_by_object: {} };
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
  const product = String(row[1] ?? "").trim();

  const volume = Number(row[4]);
  if (!Number.isFinite(volume) || volume <= 0) {
    failures.push({ object_id: objectId, raw_volume: row[4], state: "NOT_ESTIMABLE_VOLUME_ENCODING" });
  }
  const rawPrice = row[5];
  const rawPriceText = String(rawPrice ?? "").trim();
  const parsedComponents = rawPriceText.split("/").map((part) => part.trim()).filter((part) => part !== "").map((part) => Number(part.replace(",", ".")));
  const configuredWeights = classWeights.weights_by_object?.[String(objectId)] ?? null;
  let priceComponents = null;
  let effectivePrice = null;
  let priceState = "NOT_ESTIMABLE_PRICE_ENCODING";
  if (typeof rawPrice === "number" && Number.isFinite(rawPrice)) {
    effectivePrice = rawPrice;
    priceState = "ESTIMABLE_EXACT_DESTINATION";
  } else if (parsedComponents.length > 1
      && parsedComponents.every(Number.isFinite)
      && Array.isArray(configuredWeights)
      && configuredWeights.length === parsedComponents.length
      && Math.abs(configuredWeights.reduce((sum, value) => sum + value, 0) - 1) < 1e-12) {
    priceComponents = parsedComponents;
    effectivePrice = parsedComponents.reduce((sum, value, index) => sum + value * configuredWeights[index], 0);
    priceState = "ESTIMABLE_OFFER_WEIGHTED_CLASS_PRICE";
  } else {
    const scalar = Number(rawPriceText.replace(",", "."));
    if (Number.isFinite(scalar)) {
      effectivePrice = scalar;
      priceState = "ESTIMABLE_EXACT_DESTINATION";
    }
  }
  if (effectivePrice == null) {
    failures.push({ object_id: objectId, raw_price: rawPrice, state: "NOT_ESTIMABLE_PRICE_ENCODING_OR_MISSING_OFFER_WEIGHTS" });
  }
  rows.push({
    object_id: objectId,
    product: object.product,
    raw_result_product: product,
    buyer: String(row[2] ?? "").trim(),
    destination: String(row[3] ?? "").trim(),
    awarded_volume_m3: Number.isFinite(volume) ? volume : null,
    raw_price: rawPrice,
    price_components: priceComponents,
    effective_weighted_price_eur_m3: effectivePrice,
    price_state: priceState,
  });
}

const groups = new Map();
for (const row of rows) {
  if (row.awarded_volume_m3 == null) continue;
  const key = `${row.object_id}\u001f${row.destination}`;
  if (!groups.has(key)) {
    groups.set(key, {
      object_id: row.object_id,
      product: row.product,
      raw_result_products: new Set(),
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
  group.raw_result_products.add(row.raw_result_product);
  group.awarded_volume_m3 += row.awarded_volume_m3;
  group.source_rows += 1;
  if (row.effective_weighted_price_eur_m3 != null) {
    group.price_volume_sum += row.effective_weighted_price_eur_m3 * row.awarded_volume_m3;
    group.price_volume_support_m3 += row.awarded_volume_m3;
  }
}

const localOutcomes = [];
const quarantinedOutcomes = [];
for (const group of groups.values()) {
  const object = offerById.get(group.object_id);
  const classDescriptor = JSON.stringify({
    quality: object.quality_and_measurement_standard,
    price_classes: object.price_classes.map((entry) => entry.diameter_or_class),
    class_weights: null,
  });
  const measurementFingerprint = crypto.createHash("sha256").update(classDescriptor, "utf8").digest("hex").toUpperCase();
  const outcome = {
    object_id: group.object_id,
    product: group.product,
    raw_result_products: [...group.raw_result_products].sort(),
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
        ? "ESTIMABLE_EXACT_DESTINATION"
        : "NOT_ESTIMABLE_PARTIAL_PRICE_SUPPORT",
    source_rows: group.source_rows,
  };
  if (invalidDeliveryObjectIds.has(group.object_id)) {
    quarantinedOutcomes.push({ ...outcome, state: "NOT_ESTIMABLE_INVALID_DELIVERY_PERIOD_CHRONOLOGY" });
  } else if (sourceVolumeConflictObjectIds.has(group.object_id)) {
    quarantinedOutcomes.push({ ...outcome, state: "NOT_ESTIMABLE_SOURCE_VOLUME_CONFLICT" });
  } else {
    localOutcomes.push(outcome);
  }
}

const objectTotals = [];
for (const object of offer.objects) {
  const resultRows = rows.filter((row) => row.object_id === object.object_id && row.awarded_volume_m3 != null);
  const awarded = resultRows.reduce((sum, row) => sum + row.awarded_volume_m3, 0);
  const sourceVolumesVerified = object.location_total_matches === true;
  objectTotals.push({
    object_id: object.object_id,
    product: object.product,
    offer_volume_m3: object.advertised_volume_m3,
    location_sheet_volume_m3: object.location_sheet_total_m3,
    awarded_volume_m3: awarded,
    coverage_offer_denominator: sourceVolumesVerified ? awarded / object.advertised_volume_m3 : null,
    coverage_location_sheet_denominator: sourceVolumesVerified && object.location_sheet_total_m3 != null ? awarded / object.location_sheet_total_m3 : null,
    state: invalidDeliveryObjectIds.has(object.object_id)
      ? "NOT_ESTIMABLE_INVALID_DELIVERY_PERIOD_CHRONOLOGY"
      : sourceVolumeConflictObjectIds.has(object.object_id)
        ? "NOT_ESTIMABLE_SOURCE_VOLUME_CONFLICT"
        : sourceVolumesVerified
          ? "ADJUDICABLE"
          : "NOT_ESTIMABLE_SOURCE_VOLUME_UNVERIFIED_OR_DISAGREEMENT",
  });
}

const result = {
  schema_version: "bpm.rmk.result-structured.v0.5",
  event_date: eventDate,
  protocol_date: protocolDate,
  source_file: inputPath,
  source_sha256: sourceSha256,
  source_bytes: Number(sourceBytesText),
  frozen_offer_raw_sha256: offer.source_sha256,
  structured_offer_used_sha256: crypto.createHash("sha256").update(await fs.readFile(offerPath)).digest("hex").toUpperCase(),
  award_row_count: rows.length,
  local_outcome_count: localOutcomes.length,
  quarantined_outcome_count: quarantinedOutcomes.length,
  freeze_used_sha256: freezePath ? crypto.createHash("sha256").update(await fs.readFile(freezePath)).digest("hex").toUpperCase() : null,
  total_awarded_volume_m3: rows.reduce((sum, row) => sum + (row.awarded_volume_m3 ?? 0), 0),
  extraction_failures: failures,
  rows,
  local_outcomes: localOutcomes,
  quarantined_outcomes: quarantinedOutcomes,
  object_totals: objectTotals,
  quarantined_unpaired_result: quarantinedResultUrl
    ? {
        url: quarantinedResultUrl,
        body_opened: false,
        state: "QUARANTINE_UNPAIRED_RESULT_NO_FROZEN_OFFER"
      }
    : null
};

await fs.writeFile(outputPath, JSON.stringify(result, null, 2) + "\n", "utf8");
console.log(JSON.stringify({
  outputPath,
  awardRows: result.award_row_count,
  localOutcomes: result.local_outcome_count,
  quarantinedOutcomes: result.quarantined_outcome_count,
  totalAwardedVolumeM3: result.total_awarded_volume_m3,
  extractionFailures: failures.length,
  unawardedObjects: objectTotals.filter((item) => item.awarded_volume_m3 === 0).map((item) => item.object_id),
}, null, 2));
