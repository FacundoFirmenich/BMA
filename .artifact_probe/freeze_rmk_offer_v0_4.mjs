import fs from "node:fs/promises";
import crypto from "node:crypto";

const [offerPath, priorPath, outputPath, rawOfferSha256, structuredOfferSha256, priorSha256, softwareCorrectionSha256, eventDate, pairedResultUrl] = process.argv.slice(2);
if (!offerPath || !priorPath || !outputPath || !rawOfferSha256 || !structuredOfferSha256 || !priorSha256 || !softwareCorrectionSha256 || !eventDate || !pairedResultUrl) {
  throw new Error("Usage: node freeze_rmk_offer_v0_4.mjs offer.json prior.json freeze.json raw_sha structured_sha prior_sha correction_sha event_date paired_result_url");
}

const offer = JSON.parse(await fs.readFile(offerPath, "utf8"));
const prior = JSON.parse(await fs.readFile(priorPath, "utf8"));
const priorCells = Object.values(prior.local_cells);

function parseEstonianDate(value) {
  const match = /^(\d{2})\.(\d{2})\.(\d{4})$/.exec(value);
  if (!match) return null;
  const [, day, month, year] = match;
  const date = new Date(Date.UTC(Number(year), Number(month) - 1, Number(day)));
  return Number.isNaN(date.valueOf()) ? null : date;
}

function periodState(period) {
  const match = /^\s*(\d{2}\.\d{2}\.\d{4})\s*-\s*(\d{2}\.\d{2}\.\d{4})\s*$/.exec(period);
  if (!match) return { state: "NOT_ESTIMABLE_INVALID_DELIVERY_PERIOD_ENCODING", phase: null };
  const start = parseEstonianDate(match[1]);
  const end = parseEstonianDate(match[2]);
  const event = new Date(`${eventDate}T00:00:00Z`);
  if (!start || !end || end < start || start < event) {
    return { state: "NOT_ESTIMABLE_INVALID_DELIVERY_PERIOD_CHRONOLOGY", phase: null };
  }
  const months = new Set();
  let year = start.getUTCFullYear();
  let month = start.getUTCMonth() + 1;
  while (year < end.getUTCFullYear() || (year === end.getUTCFullYear() && month <= end.getUTCMonth() + 1)) {
    months.add(month);
    if (month === 12) {
      year += 1;
      month = 1;
    } else {
      month += 1;
    }
  }
  return { state: "VALID", phase: [...months].sort((a, b) => a - b).map((value) => `M${String(value).padStart(2, "0")}`).join("-") };
}

const objects = offer.objects.map((object) => {
  const delivery = periodState(object.delivery_period);
  const classDescriptor = JSON.stringify({
    quality: object.quality_and_measurement_standard,
    price_classes: object.price_classes.map((entry) => entry.diameter_or_class),
    class_weights: null,
  });
  const fingerprint = crypto.createHash("sha256").update(classDescriptor, "utf8").digest("hex").toUpperCase();
  const matches = delivery.state === "VALID"
    ? priorCells.filter((cell) => cell.descriptor.product === object.product && cell.descriptor.measurement_fingerprint_sha256 === fingerprint)
    : [];
  return {
    object_id: object.object_id,
    product: object.product,
    delivery_period: object.delivery_period,
    delivery_period_state: delivery.state,
    calendar_phase: delivery.phase,
    source_volume_state: object.location_volume_state,
    measurement_fingerprint_sha256: fingerprint,
    prior_matching_destinations: matches.map((cell) => cell.descriptor.destination).sort(),
    frozen_local_predictions: matches.map((cell) => ({
      destination: cell.descriptor.destination,
      price: {
        M0: cell.price.observations.at(-1),
        M1: cell.price.observations.length >= 3 ? "REQUIRES_MODEL_CORE_EVALUATION" : "NOT_ESTIMABLE_M1_SUPPORT",
        M2: "NOT_ESTIMABLE_SEASONAL_SUPPORT",
        BMA: "BMA_MIXTURE_NOT_ESTIMABLE_COMMON_SUPPORT",
      },
      volume: {
        M0: cell.volume.observations.at(-1),
        M1: cell.volume.observations.length >= 3 ? "REQUIRES_MODEL_CORE_EVALUATION" : "NOT_ESTIMABLE_M1_SUPPORT",
        M2: "NOT_ESTIMABLE_SEASONAL_SUPPORT",
        BMA: "BMA_MIXTURE_NOT_ESTIMABLE_COMMON_SUPPORT",
      },
    })),
    no_match_state: delivery.state !== "VALID"
      ? delivery.state
      : matches.length === 0
        ? "NOT_ESTIMABLE_NO_PRIOR_COMPARABLE_BASE_CELL"
        : null,
  };
});

const freeze = {
  schema_version: "bpm.rmk.event-freeze.v0.4",
  campaign_id: "BPM_RMK_TIMBER_CAUSAL_CAMPAIGN_V0.1",
  event_date: eventDate,
  state: "FREEZE_WRITTEN_PAIRED_RESULT_STILL_CLOSED",
  inputs_sha256: { raw_offer: rawOfferSha256, structured_offer: structuredOfferSha256, prior: priorSha256 },
  software_correction_sha256: softwareCorrectionSha256,
  object_count: objects.length,
  invalid_delivery_period_objects: objects.filter((object) => object.delivery_period_state !== "VALID").map((object) => object.object_id),
  source_volume_conflict_objects: objects.filter((object) => !String(object.source_volume_state).startsWith("VERIFIED_")).map((object) => object.object_id),
  objects_with_prior_base_cell_match: objects.filter((object) => object.prior_matching_destinations.length > 0).length,
  frozen_destination_predictions: objects.reduce((sum, object) => sum + object.frozen_local_predictions.length, 0),
  objects,
  paired_result: { url: pairedResultUrl, body_opened: false, opening_authorized_only_after_this_freeze_is_hashed: true },
  global_winner: null,
  automatic_promotion: false,
};

await fs.writeFile(outputPath, JSON.stringify(freeze, null, 2) + "\n", "utf8");
console.log(JSON.stringify({
  objects: freeze.object_count,
  invalidDeliveryPeriodObjects: freeze.invalid_delivery_period_objects,
  sourceVolumeConflictObjects: freeze.source_volume_conflict_objects,
  objectsWithPriorMatch: freeze.objects_with_prior_base_cell_match,
  frozenDestinationPredictions: freeze.frozen_destination_predictions,
}, null, 2));
