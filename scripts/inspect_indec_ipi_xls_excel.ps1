param(
  [string]$RepoRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = 'Stop'
$runDir = Join-Path $RepoRoot 'evidence\runs\hbp-indec-prodcom-public-custody-probe-v0.1'
$source = Join-Path $runDir 'indec_ipi_series_2026.xls'
$output = Join-Path $runDir 'indec_ipi_series_2026_workbook_inspection.json'
$excel = $null
$book = $null

try {
  $excel = New-Object -ComObject Excel.Application
  $excel.Visible = $false
  $excel.DisplayAlerts = $false
  $excel.AskToUpdateLinks = $false
  $book = $excel.Workbooks.Open($source, 0, $true)
  $sheets = @()
  foreach ($sheet in $book.Worksheets) {
    $used = $sheet.UsedRange
    $rowCount = [int]$used.Rows.Count
    $columnCount = [int]$used.Columns.Count
    $sampleRows = [Math]::Min($rowCount, 18)
    $sampleColumns = [Math]::Min($columnCount, 16)
    $sample = @()
    for ($r = 1; $r -le $sampleRows; $r++) {
      $row = @()
      for ($c = 1; $c -le $sampleColumns; $c++) {
        $row += $sheet.Cells.Item($r, $c).Text
      }
      $sample += ,$row
    }
    $sheets += [ordered]@{
      name = [string]$sheet.Name
      used_rows = $rowCount
      used_columns = $columnCount
      top_left_sample_display_values = $sample
    }
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($used)
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($sheet)
  }
  $payload = [ordered]@{
    classification = 'READ_ONLY_XLS_BINARY_INSPECTION_NO_EDIT_NO_SAVE'
    source_file = 'indec_ipi_series_2026.xls'
    excel_automation_available = $true
    sheet_count = $sheets.Count
    sheets = $sheets
  }
  $payload | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $output -Encoding utf8
  $payload | ConvertTo-Json -Depth 12
}
catch {
  $payload = [ordered]@{
    classification = 'READ_ONLY_XLS_BINARY_INSPECTION_BLOCKED'
    source_file = 'indec_ipi_series_2026.xls'
    excel_automation_available = $false
    error_type = $_.Exception.GetType().FullName
    error = $_.Exception.Message
  }
  $payload | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $output -Encoding utf8
  $payload | ConvertTo-Json -Depth 6
  exit 2
}
finally {
  if ($book -ne $null) {
    $book.Close($false)
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($book)
  }
  if ($excel -ne $null) {
    $excel.Quit()
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($excel)
  }
  [GC]::Collect()
  [GC]::WaitForPendingFinalizers()
}

