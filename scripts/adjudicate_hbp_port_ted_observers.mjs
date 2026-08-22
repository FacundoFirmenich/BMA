import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const repo = path.resolve(process.argv[2] || process.cwd());
const portRelative = "evidence/probes/public-expansion-v1/puertos_es_2026-06.xlsx";
const tedRelative = "evidence/probes/public-expansion-v1/ted_can_standard_cpv44_limit10.json";
const preregRelative = "preregistrations/HBP_PORT_TED_PROSPECTIVE_OBSERVER_CHAIN_V0.1.json";
const outputRelative = "evidence/runs/hbp-port-ted-prospective-observer-chain-v0.1/observer_adjudication.json";
const portPath = path.join(repo, ...portRelative.split("/"));
const tedPath = path.join(repo, ...tedRelative.split("/"));
const preregPath = path.join(repo, ...preregRelative.split("/"));
const outputPath = path.join(repo, ...outputRelative.split("/"));

function sha256(bytes) {
  return crypto.createHash("sha256").update(bytes).digest("hex").toUpperCase();
}

function norm(value) {
  return String(value ?? "").trim().toLowerCase();
}

function parseFirstTable(result) {
  for (const line of result.ndjson.split(/\r?\n/)) {
    if (!line.trim()) continue;
    const item = JSON.parse(line);
    if (item.kind === "table") return item;
  }
  throw new Error("No table returned by artifact-tool inspection");
}

async function inspectTable(workbook, sheetId, range) {
  return parseFirstTable(
    await workbook.inspect({
      kind: "table",
      sheetId,
      range,
      maxChars: 50000,
      tableMaxRows: 80,
      tableMaxCols: 50,
      tableMaxCellChars: 160,
    }),
  );
}

function requireRow(rows, predicate, label) {
  const row = rows.find(predicate);
  if (!row) throw new Error(`Missing expected row: ${label}`);
  return row;
}

function presentationRow(row, cell) {
  return {
    source_cells: cell,
    june_2025_tonnes: row[3],
    june_2026_tonnes: row[4],
    january_to_june_2025_tonnes: row[5],
    january_to_june_2026_tonnes: row[6],
    accumulated_change_tonnes: row[7],
    accumulated_change_percent: row[8],
  };
}

function natureRow(row, cell) {
  return {
    source_cells: cell,
    liquid_bulk: {
      january_to_june_2025_tonnes: row[2],
      january_to_june_2026_tonnes: row[3],
      change_tonnes: row[4],
      change_percent: row[5],
    },
    solid_bulk: {
      january_to_june_2025_tonnes: row[6],
      january_to_june_2026_tonnes: row[7],
      change_tonnes: row[8],
      change_percent: row[9],
    },
    general_cargo: {
      january_to_june_2025_tonnes: row[10],
      january_to_june_2026_tonnes: row[11],
      change_tonnes: row[12],
      change_percent: row[13],
    },
  };
}

const portBytes = await fs.readFile(portPath);
const tedBytes = await fs.readFile(tedPath);
const preregBytes = await fs.readFile(preregPath);
const portHash = sha256(portBytes);
const tedHash = sha256(tedBytes);
if (portHash !== "C4BDD4500A67A7A3CD3A17BDFD6131D206F468A7E99BE1584BA7A217EC39A28F") {
  throw new Error(`Puertos anchor hash mismatch: ${portHash}`);
}
if (tedHash !== "C1A75475D2C6D6617475A770AEE2B2F11A6013687803996E1C5ADD850A75DBA3") {
  throw new Error(`TED anchor hash mismatch: ${tedHash}`);
}

const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(portPath));
const sheetsResult = await workbook.inspect({ kind: "sheet", include: "id,name", maxChars: 30000 });
const sheets = sheetsResult.ndjson
  .split(/\r?\n/)
  .filter(Boolean)
  .map((line) => JSON.parse(line))
  .filter((item) => item.kind === "sheet");
const general = (await inspectTable(workbook, "Resumen general", "A4:I18")).values;
const monthlySheet = sheets.find((sheet) => String(sheet.name ?? "").includes("Mensual (t)"));
if (!monthlySheet) throw new Error("Missing monthly evolution worksheet");
const natures = (await inspectTable(workbook, "Resumen naturalezas", "A20:N45")).values;
const historicPresentation = (await inspectTable(workbook, monthlySheet.id, "Z6:AP19")).values;
const historicGeneral = (await inspectTable(workbook, monthlySheet.id, "Z33:AP46")).values;

const totalTraffic = requireRow(general, (row) => String(row[0] ?? "").includes("TOTAL (*)"), "total traffic");
const liquidBulk = requireRow(general, (row) => norm(row[1]).includes("quidos"), "liquid bulk");
const solidBulk = requireRow(general, (row) => norm(row[1]).includes("lidos"), "solid bulk");
const generalCargo = requireRow(
  general,
  (row) => norm(row[1]).includes("general") && norm(row[2]) === "total",
  "general cargo",
);
const containerCargo = requireRow(general, (row) => norm(row[2]).includes("contenedores"), "container cargo");

const wood = requireRow(natures, (row) => norm(row[1]).includes("maderas y corcho"), "wood and cork");
const paper = requireRow(natures, (row) => norm(row[1]).includes("papel y pasta"), "paper and pulp");
const steel = requireRow(natures, (row) => norm(row[1]).includes("productos sider"), "steel products");
const machinery = requireRow(natures, (row) => norm(row[1]).includes("maquinaria"), "machinery");
const vehicles = requireRow(natures, (row) => norm(row[1]).includes("veh") && norm(row[1]).includes("piezas"), "vehicles and parts");

const junePresentation = requireRow(historicPresentation, (row) => norm(row[0]) === "jun", "historic June presentation");
const juneGeneral = requireRow(historicGeneral, (row) => norm(row[0]) === "jun", "historic June general cargo");
const historicYears = [...new Set(
  [...historicPresentation.flat(), ...historicGeneral.flat()].filter(
    (value) => Number.isInteger(value) && value >= 1900 && value <= 2100,
  ),
)].sort();
const inspectedErrors = [...general.flat(), ...natures.flat(), ...historicPresentation.flat(), ...historicGeneral.flat()]
  .filter((value) => typeof value === "string" && value.startsWith("#"));

const ted = JSON.parse(tedBytes.toString("utf8"));
const notices = ted.notices ?? [];
const uniqueNotices = new Set(notices.map((notice) => notice["publication-number"]));
const coverageCount = (field) => notices.filter((notice) => notice[field] !== undefined && notice[field] !== null).length;
const countries = [...new Set(
  notices.flatMap((notice) => notice["place-of-performance"] ?? []).filter((value) => /^[A-Z]{3}$/.test(value)),
)].sort();
const quantityFields = notices.reduce(
  (count, notice) => count + Object.keys(notice).filter((key) => key.toLowerCase().includes("quantity")).length,
  0,
);

const output = {
  schema: "hbp-port-ted-observer-adjudication/v0.1",
  adjudicated_on: "2026-08-22",
  classification: "EXISTING_BYTES_ONLY_NO_NEW_REMOTE_ACQUISITION",
  preregistration: { path: preregRelative, sha256: sha256(preregBytes) },
  invariants: {
    fit_performed: false,
    forecast_performed: false,
    score_performed: false,
    posterior_updated: false,
    Z_post_updated: false,
    historical_freeze_reconstructed: false,
    cross_source_likelihood_pooling: false,
    global_winner: null,
    automatic_promotion: false,
  },
  puertos: {
    raw: { path: portRelative, bytes: portBytes.length, sha256: portHash },
    workbook: {
      sheet_count: sheets.length,
      workbook_date: "2026-07-22",
      reference_month: "2026-06",
      unit: "tonnes unless expressly stated otherwise",
      formula_errors_observed_in_selected_ranges: [...new Set(inspectedErrors)].sort(),
      formula_error_rule: "do not use an imported formula error when a published value cell exists",
    },
    national_physical_activity: {
      total_traffic: presentationRow(totalTraffic, "Resumen general!A18:I18"),
      liquid_bulk: presentationRow(liquidBulk, "Resumen general!A7:I7"),
      solid_bulk: presentationRow(solidBulk, "Resumen general!A8:I8"),
      general_cargo: presentationRow(generalCargo, "Resumen general!A9:I9"),
      containerized_general_cargo: presentationRow(containerCargo, "Resumen general!A10:I10"),
    },
    selected_non_energy_natures: {
      wood_and_cork: natureRow(wood, "Resumen naturalezas!A41:N41"),
      paper_and_pulp: natureRow(paper, "Resumen naturalezas!A42:N42"),
      steel_products: natureRow(steel, "Resumen naturalezas!A20:N20"),
      machinery_apparatus_tools_and_spares: natureRow(machinery, "Resumen naturalezas!A43:N43"),
      vehicles_and_parts: natureRow(vehicles, "Resumen naturalezas!A45:N45"),
    },
    historic_monthly_presentation_schema: {
      years_exposed: historicYears,
      current_2026_monthly_by_nature_exposed: false,
      june_total_traffic_tonnes_2019_to_2022: junePresentation.slice(1, 5),
      june_liquid_bulk_tonnes_2019_to_2022: junePresentation.slice(7, 11),
      june_solid_bulk_tonnes_2019_to_2022: junePresentation.slice(13, 17),
      june_general_cargo_tonnes_2019_to_2022: juneGeneral.slice(1, 5),
      june_containerized_general_cargo_tonnes_2019_to_2022: juneGeneral.slice(7, 11),
      adjudication: "HISTORICAL_PRESENTATION_TOTALS_ONLY_NOT_A_CURRENT_MONTHLY_NATURE_PANEL",
    },
    authority: "DESCRIPTIVE_PHYSICAL_ACTIVITY_OBSERVER_ONLY",
    nature_monthly_status: "NOT_ESTIMABLE_NO_CURRENT_MONTHLY_NATURE_CELL",
    cumulative_difference_status: "FORBIDDEN_REVISION_MIXED_INCREMENT_UNLESS_SEPARATELY_RECONCILED",
  },
  ted: {
    raw: { path: tedRelative, bytes: tedBytes.length, sha256: tedHash },
    query_semantics_recovered: {
      notice_type: "can-standard",
      cpv_prefix: "44",
      sample_limit: 10,
      exact_prior_request_body_available: false,
    },
    response: {
      timed_out: ted.timedOut,
      reported_total_notice_count: ted.totalNoticeCount,
      sampled_notices: notices.length,
      unique_publication_numbers: uniqueNotices.size,
      publication_date_min: notices.map((notice) => notice["publication-date"]).sort()[0],
      publication_date_max: notices.map((notice) => notice["publication-date"]).sort().at(-1),
      countries,
      field_coverage: {
        publication_number: coverageCount("publication-number"),
        publication_date: coverageCount("publication-date"),
        notice_type: coverageCount("notice-type"),
        cpv: coverageCount("classification-cpv"),
        place: coverageCount("place-of-performance"),
        award_value: coverageCount("result-value-notice"),
        currency: coverageCount("result-value-cur-notice"),
        quantity_fields: quantityFields,
      },
    },
    authority: "INSTITUTIONAL_DEMAND_EVENT_COUNT_OBSERVER_ONLY",
    value_status: "NOT_ESTIMABLE_INCOMPLETE_VALUE_AND_CURRENCY",
    quantity_status: "NOT_ESTIMABLE_NO_QUANTITY_FIELD",
    current_sample_causal_status: "RETROSPECTIVE_SCHEMA_SAMPLE_NO_CAUSAL_SCORE",
  },
  coral_adjudication: {
    position_change: "BETTER_TYPED_OBSERVER_DESIGN_WITHOUT_NEW_PREDICTIVE_AUTHORITY",
    puertos_role: "physical logistics activity",
    ted_role: "institutional demand events",
    direct_product_monthly_role: "NOT_ESTIMABLE",
    M2_status: "ABSTAIN_UNTIL_TARGET_SPECIFIC_FREEZE_AND_SUPPORT_GATE",
    M3_status: "ABSTAIN_NO_CAUSALLY_ALIGNED_MULTI_SOURCE_LIKELIHOOD",
  },
};

await fs.mkdir(path.dirname(outputPath), { recursive: true });
await fs.writeFile(outputPath, `${JSON.stringify(output, null, 2)}\n`, "utf8");
console.log(JSON.stringify({ output: outputRelative, puertos: output.puertos.authority, ted: output.ted.authority, M2: output.coral_adjudication.M2_status }, null, 2));
