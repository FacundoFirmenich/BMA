import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const input = await FileBlob.load(process.argv[2]);
const workbook = await SpreadsheetFile.importXlsx(input);
for (const sheet of workbook.worksheets.items) {
  const used = sheet.getUsedRange(false);
  if (!used) continue;
  const findings = await workbook.inspect({
    kind: "formula",
    sheetId: sheet.name,
    range: used.address,
    maxChars: 12000,
    options: { maxResults: 200 },
  });
  console.log(findings.ndjson);
}
