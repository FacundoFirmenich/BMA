import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const [inputPath] = process.argv.slice(2);
if (!inputPath) throw new Error("Usage: node summarize_rmk_location_sheet.mjs offer.xlsx");
const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(inputPath));
const sheet = workbook.worksheets.getItem("asukoht");
const values = sheet.getUsedRange(false).values;
const objects = new Map();
let currentObject = null;
for (const row of values.slice(1)) {
  if (typeof row[0] === "number") currentObject = row[0];
  if (currentObject == null) continue;
  if (!objects.has(currentObject)) objects.set(currentObject, { object_id: currentObject, rows: [], component_sum_m3: 0, stated_total_m3: null });
  const item = objects.get(currentObject);
  const label = String(row[1] ?? row[2] ?? "").trim();
  const isTotal = label.toLocaleLowerCase("et") === "kokku";
  const quantity = Number(row[3]);
  if (isTotal) {
    item.stated_total_m3 = Number.isFinite(quantity) ? quantity : null;
  } else if (Number.isFinite(quantity)) {
    const location = String(row[2] ?? "").trim();
    item.rows.push({ location, quantity_m3: quantity });
    item.component_sum_m3 += quantity;
  }
}
for (const item of objects.values()) {
  const seen = new Map();
  for (const row of item.rows) {
    const key = `${row.location}\u001f${row.quantity_m3}`;
    seen.set(key, (seen.get(key) ?? 0) + 1);
  }
  item.exact_duplicate_rows = [...seen.entries()]
    .filter(([, count]) => count > 1)
    .map(([key, count]) => {
      const [location, quantity] = key.split("\u001f");
      return { location, quantity_m3: Number(quantity), count };
    });
  item.component_sum_matches_stated_total = item.stated_total_m3 != null && item.component_sum_m3 === item.stated_total_m3;
}
console.log(JSON.stringify({ objects: [...objects.values()] }, null, 2));
