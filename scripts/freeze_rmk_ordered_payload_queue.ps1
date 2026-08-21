param(
    [string]$DatedInventory = "evidence/probes/rmk-url-inventory-v1/rmk_dated_payload_url_inventory.csv",
    [string]$CandidateLinks = "evidence/probes/rmk-url-inventory-v1/rmk_candidate_event_page_links.csv",
    [string]$OutputDir = "evidence/probes/rmk-url-inventory-v1",
    [int]$MaximumUniqueUrls = 80
)

$ErrorActionPreference = "Stop"
$rows = @()
$rows += Import-Csv -LiteralPath $DatedInventory
if (Test-Path -LiteralPath $CandidateLinks) {
    $rows += Import-Csv -LiteralPath $CandidateLinks | ForEach-Object {
        [pscustomobject]@{
            resolved_event_date=$_.event_date; date_evidence="CANDIDATE_EVENT_PAGE_EXPLICIT"; phase_hint="";
            discovery_context="CANDIDATE_EVENT"; discovery_page=$_.discovery_page;
            role_guess=$_.role_guess; payload_url=$_.payload_url; payload_opened=$_.payload_opened
        }
    }
}

$normalized = foreach ($row in $rows) {
    $role = [string]$row.role_guess
    $probe = ([string]$row.payload_url).ToLowerInvariant()
    if ($role -match "UNRESOLVED" -and $probe -match "muugiobjekt|myygiobjekt|müügiobjekt|pakkumuse") { $role = "OFFER_OR_FORM" }
    if ($role -match "UNRESOLVED" -and $probe -match "edukad|winner|protokoll") { $role = "RESULT" }
    [pscustomobject]@{
        event_date=[string]$row.resolved_event_date; phase_hint=[string]$row.phase_hint;
        date_evidence=[string]$row.date_evidence; role=$role;
        discovery_page=[string]$row.discovery_page; payload_url=[string]$row.payload_url
    }
}
$normalized = @($normalized | Sort-Object event_date,phase_hint,role,payload_url -Unique)
$uniqueUrls = @($normalized.payload_url | Sort-Object -Unique)
if ($uniqueUrls.Count -gt $MaximumUniqueUrls) { throw "URL cap exceeded: $($uniqueUrls.Count)" }

$dateRole = @{}
foreach ($group in ($normalized | Where-Object event_date | Group-Object event_date)) { $dateRole[$group.Name] = @($group.Group.role) }
$schemaProbeUrls = @(
    "https://rmk.ee/wp-content/uploads/2026/06/Myygiobjektid_30.06.2026.xlsx",
    "https://rmk.ee/wp-content/uploads/2026/07/Edukad_EP_30.06.2026.xlsx"
)

$head = @{}
foreach ($url in $uniqueUrls) {
    try {
        $response = Invoke-WebRequest -Uri $url -Method Head -MaximumRedirection 5
        $head[$url] = [pscustomobject]@{status=[int]$response.StatusCode;content_type=[string]$response.Headers["Content-Type"][0];content_length=[string]$response.Headers["Content-Length"][0];etag=[string]$response.Headers["ETag"][0];last_modified=[string]$response.Headers["Last-Modified"][0];head_error=""}
    }
    catch {
        $status = if ($_.Exception.Response -and $_.Exception.Response.StatusCode) { [int]$_.Exception.Response.StatusCode } else { 0 }
        $head[$url] = [pscustomobject]@{status=$status;content_type="";content_length="";etag="";last_modified="";head_error=$_.Exception.Message}
    }
}

$queue = foreach ($row in $normalized) {
    $state = if ($schemaProbeUrls -contains $row.payload_url) { "SCHEMA_PROBE_EXCLUDED_FROM_BLIND_EVALUATION" }
        elseif (-not $row.event_date -and $row.phase_hint) { "QUARANTINE_PHASE_ONLY_DATE_UNRESOLVED" }
        elseif (-not $row.event_date) { "REFERENCE_OR_UNRESOLVED_NOT_IN_REPLAY" }
        elseif ($row.role -eq "RESULT" -and -not ($dateRole[$row.event_date] -contains "OFFER_OR_FORM")) { "RESULT_ONLY_ELIGIBILITY_AUDIT" }
        elseif (($dateRole[$row.event_date] -contains "RESULT") -and ($dateRole[$row.event_date] -contains "OFFER_OR_FORM")) { "PAIR_DISCOVERED_NOT_YET_OPENED" }
        else { "UNPAIRED_NOT_IN_REPLAY" }
    $order = switch ($row.role) { "OFFER_OR_FORM" {1}; "RESULT" {2}; "NORMALIZATION_REFERENCE" {0}; default {9} }
    $meta = $head[$row.payload_url]
    [pscustomobject]@{
        sequence=0; event_date=$row.event_date; phase_hint=$row.phase_hint; within_date_order=$order;
        role=$row.role; acquisition_state=$state; date_evidence=$row.date_evidence;
        payload_url=$row.payload_url; discovery_page=$row.discovery_page;
        head_status=$meta.status; content_type=$meta.content_type; content_length=$meta.content_length;
        etag=$meta.etag; last_modified=$meta.last_modified; head_error=$meta.head_error;
        body_opened=$false
    }
}
$queue = @($queue | Sort-Object @{Expression={if($_.event_date){$_.event_date}else{"9999-99-99"}}},within_date_order,payload_url)
for ($i=0; $i -lt $queue.Count; $i++) { $queue[$i].sequence = $i + 1 }

$resolvedOutput=[IO.Path]::GetFullPath((Join-Path (Get-Location) $OutputDir))
$queuePath=Join-Path $resolvedOutput "rmk_ordered_payload_queue_with_head.csv"
$queue|Export-Csv -NoTypeInformation -Encoding utf8 -LiteralPath $queuePath
$manifest=[ordered]@{
    schema="rmk-ordered-payload-queue/v1"; generated_at=(Get-Date -Format o);
    rows=$queue.Count; unique_urls=$uniqueUrls.Count; head_success=@($head.Values|Where-Object status -eq 200).Count;
    head_failure=@($head.Values|Where-Object status -ne 200).Count; bodies_opened=0;
    pair_rows=@($queue|Where-Object acquisition_state -eq "PAIR_DISCOVERED_NOT_YET_OPENED").Count;
    result_only_rows=@($queue|Where-Object acquisition_state -eq "RESULT_ONLY_ELIGIBILITY_AUDIT").Count;
    schema_probe_excluded_rows=@($queue|Where-Object acquisition_state -eq "SCHEMA_PROBE_EXCLUDED_FROM_BLIND_EVALUATION").Count;
    queue_sha256=(Get-FileHash -Algorithm SHA256 -LiteralPath $queuePath).Hash
}
$manifestPath=Join-Path $resolvedOutput "rmk_ordered_payload_queue_manifest.json"
[IO.File]::WriteAllText($manifestPath,($manifest|ConvertTo-Json -Depth 6),[Text.UTF8Encoding]::new($false))
$manifest|ConvertTo-Json -Depth 6
