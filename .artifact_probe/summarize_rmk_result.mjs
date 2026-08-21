import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const inputPath = process.argv[2];
if (!inputPath) throw new Error("Usage: node summarize_rmk_result.mjs <workbook.xlsx>");

const input = await FileBlob.load(inputPath);
const workbook = await SpreadsheetFile.importXlsx(input);
const out = { inputPath, sheets: [], candidateTables: [] };

for (const sheet of workbook.worksheets.items) {
  const used = sheet.getUsedRange(false);
  if (!used) {
    out.sheets.push({ name: sheet.name, empty: true });
    continue;
  }
  const values = used.values;
  out.sheets.push({
    name: sheet.name,
    address: used.address,
    rows: values.length,
    cols: Math.max(0, ...values.map((r) => r.length)),
    leadingRows: values.slice(0, 5),
  });

  for (let i = 0; i < values.length; i += 1) {
    const row = values[i].map((v) => (v == null ? "" : String(v).trim()));
    const productIndex = row.findIndex((v) => /Metsamaterjali nimetus|Sortiment/i.test(v));
    const quantityIndex = row.findIndex((v) => /Maht|Kogus/i.test(v));
    const priceIndex = row.findIndex((v) => /Pakutud hind|Hind eur/i.test(v));
    if (productIndex < 0 || quantityIndex < 0) continue;

    const records = [];
    for (let j = i + 1; j < values.length; j += 1) {
      const data = values[j];
      const product = data[productIndex];
      const quantity = Number(data[quantityIndex]);
      if (typeof product !== "string" || !product.trim() || !Number.isFinite(quantity)) continue;
      const price = priceIndex >= 0 ? data[priceIndex] : null;
      records.push({ product: product.trim(), quantity, price });
    }
    const products = [...new Set(records.map((r) => r.product))].sort();
    const slashPrices = records.filter((r) => typeof r.price === "string" && r.price.includes("/")).length;
    const scalarPrices = records.filter((r) => typeof r.price === "number").length;
    const commaDecimalPrices = records.filter((r) => typeof r.price === "string" && r.price.includes(",")).length;
    out.candidateTables.push({
      sheet: sheet.name,
      headerRow: i + 1,
      productIndex,
      quantityIndex,
      priceIndex,
      recordCount: records.length,
      totalVolumeM3: records.reduce((s, r) => s + r.quantity, 0),
      productCount: products.length,
      products,
      slashPrices,
      scalarPrices,
      commaDecimalPrices,
      allRowsHaveQuantity: records.every((r) => Number.isFinite(r.quantity)),
      rowsWithPrice: records.filter((r) => r.price !== null && r.price !== "").length,
    });
  }
}

console.log(JSON.stringify(out, null, 2));
