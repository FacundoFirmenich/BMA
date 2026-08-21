import fs from "node:fs/promises";
import crypto from "node:crypto";

const [
  offerPath,
  priorPath,
  outputPath,
  rawOfferSha256,
  structuredOfferSha256,
  priorSha256,
  softwareCorrectionSha256,
  eventDate,
  calendarPhase,
  pairedResultUrl,
  quarantinedResultUrl = "",
] = process.argv.slice(2);

if (!offerPath || !priorPath || !outputPath || !rawOfferSha256 || !structuredOfferSha256 || !priorSha256 || !softwareCorrectionSha256 || !eventDate || !calendarPhase || !pairedResultUrl) {
  throw new Error("Usage: node freeze_rmk_offer_v0_3.mjs offer.json prior.json freeze.json raw_sha structured_sha prior_sha software_correction_sha event_date phase paired_result_url [quarantined_result_url]");
}

const offer = JSON.parse(await fs.readFile(offerPath, "utf8"));
const prior = JSON.parse(await fs.readFile(priorPath, "utf8"));
const priorCells = Object.values(prior.local_cells);

const objects = offer.objects.map((object) => {
  const classDescriptor = JSON.stringify({
    quality: object.quality_and_measurement_standard,
    price_classes: object.price_classes.map((entry) => entry.diameter_or_class),
    class_weights: null,
  });
  const fingerprint = crypto.createHash("sha256").update(classDescriptor, "utf8").digest("hex").toUpperCase();
  const matches = priorCells.filter(
    (cell) =>
      cell.descriptor.product === object.product &&
      cell.descriptor.measurement_fingerprint_sha256 === fingerprint,
  );
  return {
    object_id: object.object_id,
    product: object.product,
    delivery_period: object.delivery_period,
    calendar_phase: calendarPhase,
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
    no_match_state: matches.length === 0 ? "NOT_ESTIMABLE_NO_PRIOR_COMPARABLE_BASE_CELL" : null,
  };
});

const freeze = {
  schema_version: "bpm.rmk.event-freeze.v0.3",
  campaign_id: "BPM_RMK_TIMBER_CAUSAL_CAMPAIGN_V0.1",
  event_date: eventDate,
  state: "FREEZE_WRITTEN_PAIRED_RESULT_STILL_CLOSED",
  inputs_sha256: {
    raw_offer: rawOfferSha256,
    structured_offer: structuredOfferSha256,
    prior: priorSha256,
  },
  software_correction_sha256: softwareCorrectionSha256,
  object_count: objects.length,
  objects_with_prior_base_cell_match: objects.filter((object) => object.prior_matching_destinations.length > 0).length,
  frozen_destination_predictions: objects.reduce((sum, object) => sum + object.frozen_local_predictions.length, 0),
  objects,
  paired_result: {
    url: pairedResultUrl,
    body_opened: false,
    opening_authorized_only_after_this_freeze_is_hashed: true,
  },
  quarantined_unpaired_result: quarantinedResultUrl
    ? {
        url: quarantinedResultUrl,
        body_opened: false,
        state: "QUARANTINE_UNPAIRED_RESULT_NO_FROZEN_OFFER",
      }
    : null,
  global_winner: null,
  automatic_promotion: false,
};

await fs.writeFile(outputPath, JSON.stringify(freeze, null, 2) + "\n", "utf8");
console.log(JSON.stringify({
  objects: freeze.object_count,
  objectsWithPriorMatch: freeze.objects_with_prior_base_cell_match,
  frozenDestinationPredictions: freeze.frozen_destination_predictions,
  quarantinedUnpairedResult: freeze.quarantined_unpaired_result?.state ?? null,
}, null, 2));
