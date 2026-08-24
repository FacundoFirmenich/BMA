import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const repo = path.resolve(path.dirname(new URL(import.meta.url).pathname.replace(/^\/(.:)/, "$1")), "..");
const runDir = path.join(repo, "evidence", "runs", "hbp-indec-prodcom-public-custody-probe-v0.1");
const workbookPath = path.join(runDir, "indec_ipi_series_2026.xls");
const outputPath = path.join(runDir, "indec_ipi_series_2026_workbook_inspection.json");

const input = await FileBlob.load(workbookPath);
const workbook = await SpreadsheetFile.importXlsx(input);

const sheetsInspection = await workbook.inspect({
  kind: "workbook,sheet",
  include: "id,name",
  maxChars: 12000,
});
const compactInspection = await workbook.inspect({
  kind: "table",
  maxChars: 30000,
  tableMaxRows: 12,
  tableMaxCols: 12,
  tableMaxCellChars: 160,
});

const payload = {
  classification: "READ_ONLY_STRUCTURE_INSPECTION_NO_EDIT_NO_EXPORT",
  source_file: "indec_ipi_series_2026.xls",
  sheets_ndjson: sheetsInspection.ndjson,
  compact_tables_ndjson: compactInspection.ndjson,
};
await fs.writeFile(outputPath, JSON.stringify(payload, null, 2) + "\n", "utf8");
console.log(JSON.stringify(payload, null, 2));
