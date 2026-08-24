param(
    [string]$InputCsv = "evidence/probes/rmk-url-inventory-v1/rmk_payload_url_inventory.csv",
    [string]$OutputDir = "evidence/probes/rmk-url-inventory-v1"
)

$ErrorActionPreference = "Stop"
$rows = Import-Csv -LiteralPath $InputCsv
$dated = foreach ($row in $rows) {
    $resolvedDate = [string]$row.event_date
    $dateEvidence = if ($resolvedDate) { "EVENT_PAGE_EXPLICIT" } else { "UNRESOLVED" }
    $phaseHint = ""
    if (-not $resolvedDate -and $row.payload_url -match "(?<!\d)(?<day>0?[1-9]|[12]\d|3[01])[._-](?<month>0?[1-9]|1[0-2])[._-](?<year>20\d{2})(?!\d)") {
        $resolvedDate = "{0:D4}-{1:D2}-{2:D2}" -f [int]$Matches.year, [int]$Matches.month, [int]$Matches.day
        $dateEvidence = "FILENAME_EXPLICIT_SEMANTIC_UNVERIFIED"
    }
    if ($row.payload_url -match "(?<year>20\d{2})[_-](?<quarter>I{1,3}|IV|[1-4])(?:[_-]|\.)") {
        $quarter = switch ($Matches.quarter) { "I" {1}; "II" {2}; "III" {3}; "IV" {4}; default {[int]$Matches.quarter} }
        $phaseHint = "$($Matches.year)-Q$quarter"
    }
    [pscustomobject]@{
        resolved_event_date = $resolvedDate
        date_evidence = $dateEvidence
        phase_hint = $phaseHint
        discovery_context = $row.discovery_context
        discovery_page = $row.discovery_page
        role_guess = $row.role_guess
        payload_url = $row.payload_url
        payload_opened = $row.payload_opened
    }
}

$resolvedOutput = [System.IO.Path]::GetFullPath((Join-Path (Get-Location) $OutputDir))
New-Item -ItemType Directory -Path $resolvedOutput -Force | Out-Null
$outputCsv = Join-Path $resolvedOutput "rmk_dated_payload_url_inventory.csv"
$dated | Sort-Object resolved_event_date, role_guess, payload_url -Unique | Export-Csv -NoTypeInformation -Encoding utf8 -LiteralPath $outputCsv

$datedResults = @($dated | Where-Object { $_.role_guess -eq "RESULT" -and $_.resolved_event_date })
$datedOffers = @($dated | Where-Object { $_.role_guess -eq "OFFER_OR_FORM" -and $_.resolved_event_date })
$pairDates = @(
    $dated | Where-Object resolved_event_date |
        Group-Object resolved_event_date |
        Where-Object {
            ($_.Group.role_guess -contains "RESULT") -and
            ($_.Group.role_guess -contains "OFFER_OR_FORM")
        }
)
$manifest = [ordered]@{
    schema = "rmk-dated-url-inventory/v1"
    generated_at = (Get-Date -Format o)
    source = $InputCsv
    rows = @($dated).Count
    dated_result_rows = $datedResults.Count
    dated_offer_rows = $datedOffers.Count
    dates_with_offer_and_result_links = $pairDates.Count
    unresolved_rows = @($dated | Where-Object { -not $_.resolved_event_date }).Count
    payloads_opened = @($dated | Where-Object { $_.payload_opened -ne "False" }).Count
    date_semantics = "FILENAME_DATES_ARE_DISCOVERY_EVIDENCE_ONLY_UNTIL_MATCHED_TO_EVENT_PAGE_OR_PAYLOAD_METADATA"
    output = [ordered]@{ path = "rmk_dated_payload_url_inventory.csv"; sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $outputCsv).Hash }
}
$manifestPath = Join-Path $resolvedOutput "rmk_dated_inventory_manifest.json"
[System.IO.File]::WriteAllText($manifestPath, ($manifest | ConvertTo-Json -Depth 8), [System.Text.UTF8Encoding]::new($false))
$manifest | ConvertTo-Json -Depth 8
