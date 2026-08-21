import fs from "node:fs/promises";
import crypto from "node:crypto";

const [offerPath, priorPath, outputPath] = process.argv.slice(2);
const offer = JSON.parse(await fs.readFile(offerPath, "utf8"));
const prior = JSON.parse(await fs.readFile(priorPath, "utf8"));
const weights = new Map([
  [1, [0.07, 0.20, 0.13, 0.01, 0.59]],
  [2, [0.70, 0.30]],
  [3, [0.70, 0.30]],
  [4, [0.18, 0.37, 0.19, 0.26]],
  [5, [0.16, 0.37, 0.22, 0.25]],
  [6, [0.09, 0.32, 0.23, 0.36]],
]);
const priorCells = Object.values(prior.local_cells);
const objects = offer.objects.map((object) => {
  const classDescriptor = JSON.stringify({
    quality: object.quality_and_measurement_standard,
    price_classes: object.price_classes.map((entry) => entry.diameter_or_class),
    class_weights: weights.get(object.object_id) ?? null,
  });
  const fingerprint = crypto.createHash("sha256").update(classDescriptor, "utf8").digest("hex").toUpperCase();
  const matches = priorCells.filter((cell) => cell.descriptor.product === object.product && cell.descriptor.measurement_fingerprint_sha256 === fingerprint);
  return {
    object_id: object.object_id,
    product: object.product,
    delivery_period: object.delivery_period,
    calendar_phase: "M04-M05-M06",
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
  schema_version: "bpm.rmk.event-freeze.v0.2",
  campaign_id: "BPM_RMK_TIMBER_CAUSAL_CAMPAIGN_V0.1",
  event_date: "2025-04-24",
  state: "FREEZE_WRITTEN_RESULT_STILL_CLOSED",
  inputs_sha256: {
    raw_offer: "86994714CFEF962F72712B2F823529B658280838CD520C10CEF30A6EC9DA1165",
    structured_offer: "83E30BB9FD19AC6B3507D2764BDBEFA14310916015B46B7CB5A50E33748E0CAA",
    prior_after_2025_03_20: "7E2A47DCB8A7F11546A4769008FCADB8D3FFF3F4CE0069FCDEF871CD2FC3FA53",
  },
  object_count: objects.length,
  objects_with_prior_base_cell_match: objects.filter((object) => object.prior_matching_destinations.length > 0).length,
  frozen_destination_predictions: objects.reduce((sum, object) => sum + object.frozen_local_predictions.length, 0),
  objects,
  result: {
    url: "https://rmk.ee/wp-content/uploads/2025/04/Edukad_KLH_24.04.2025.xlsx",
    body_opened: false,
    opening_authorized_only_after_this_freeze_is_hashed: true,
  },
  global_winner: null,
  automatic_promotion: false,
};
await fs.mkdir(new URL(".", `file:///${outputPath.replaceAll("\\", "/")}`).pathname, { recursive: true }).catch(() => {});
await fs.writeFile(outputPath, JSON.stringify(freeze, null, 2) + "\n", "utf8");
console.log(JSON.stringify({ objects: freeze.object_count, objectsWithPriorMatch: freeze.objects_with_prior_base_cell_match, frozenDestinationPredictions: freeze.frozen_destination_predictions }, null, 2));
