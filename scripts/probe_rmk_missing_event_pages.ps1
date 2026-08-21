param(
    [string]$InputCsv = "evidence/probes/rmk-url-inventory-v1/rmk_dated_payload_url_inventory.csv",
    [string]$OutputDir = "evidence/probes/rmk-url-inventory-v1",
    [int]$MaximumPages = 32
)

$ErrorActionPreference = "Stop"
$rows = Import-Csv -LiteralPath $InputCsv
$dates = @(
    $rows | Where-Object { $_.resolved_event_date -and $_.role_guess -eq "RESULT" } |
        Select-Object -ExpandProperty resolved_event_date -Unique |
        Where-Object {
            $date = $_
            -not ($rows | Where-Object { $_.resolved_event_date -eq $date -and $_.role_guess -eq "OFFER_OR_FORM" })
        } | Sort-Object
)
if ($dates.Count -gt $MaximumPages) { throw "Candidate page cap exceeded" }

function Get-TextSha256([string]$Text) {
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($Text)))).Replace("-", "") }
    finally { $sha.Dispose() }
}

$pageRows = [Collections.Generic.List[object]]::new()
$linkRows = [Collections.Generic.List[object]]::new()
foreach ($date in $dates) {
    $parsed = [DateTime]::ParseExact($date, "yyyy-MM-dd", [Globalization.CultureInfo]::InvariantCulture)
    $url = "https://rmk.ee/kuulutused/metsa-ja-puidu-muuk/$($parsed.ToString('dd-MM-yyyy'))/"
    try {
        $response = Invoke-WebRequest -Uri $url -MaximumRedirection 5
        $contentType = [string]$response.Headers["Content-Type"]
        if ($contentType -notmatch "text/html") { throw "Non-HTML response: $contentType" }
        $pageRows.Add([pscustomobject]@{event_date=$date;candidate_url=$url;state="HTML_FOUND";http_status=[int]$response.StatusCode;html_utf8_sha256=Get-TextSha256 ([string]$response.Content);error=""})
        foreach ($link in $response.Links) {
            if ([string]::IsNullOrWhiteSpace([string]$link.href)) { continue }
            $absolute = ([Uri]::new([Uri]::new($url), [string]$link.href)).AbsoluteUri
            if ($absolute -notmatch "\.(xlsx|xls|csv|pdf)(?:\?|$)") { continue }
            $role = if ($absolute.ToLowerInvariant() -match "edukad|winner|protokoll") { "RESULT" } elseif ($absolute.ToLowerInvariant() -match "muugiobjekt|myygiobjekt|müügiobjekt|pakkumuse") { "OFFER_OR_FORM" } else { "UNRESOLVED" }
            $linkRows.Add([pscustomobject]@{event_date=$date;discovery_page=$url;payload_url=$absolute;role_guess=$role;payload_opened=$false})
        }
    }
    catch {
        $status = if ($_.Exception.Response -and $_.Exception.Response.StatusCode) { [int]$_.Exception.Response.StatusCode } else { 0 }
        $pageRows.Add([pscustomobject]@{event_date=$date;candidate_url=$url;state="NOT_FOUND_OR_ERROR";http_status=$status;html_utf8_sha256="";error=$_.Exception.Message})
    }
}

$resolvedOutput = [IO.Path]::GetFullPath((Join-Path (Get-Location) $OutputDir))
$pagesPath = Join-Path $resolvedOutput "rmk_candidate_event_page_probe.csv"
$linksPath = Join-Path $resolvedOutput "rmk_candidate_event_page_links.csv"
$pageRows | Export-Csv -NoTypeInformation -Encoding utf8 -LiteralPath $pagesPath
$linkRows | Sort-Object event_date,payload_url -Unique | Export-Csv -NoTypeInformation -Encoding utf8 -LiteralPath $linksPath
$manifest = [ordered]@{
    schema="rmk-candidate-event-page-probe/v1"
    generated_at=(Get-Date -Format o)
    candidate_pages=$dates.Count
    html_found=@($pageRows|Where-Object state -eq "HTML_FOUND").Count
    not_found_or_error=@($pageRows|Where-Object state -eq "NOT_FOUND_OR_ERROR").Count
    payload_links_discovered=@($linkRows).Count
    offer_links_discovered=@($linkRows|Where-Object role_guess -eq "OFFER_OR_FORM").Count
    payloads_opened=0
    pages_sha256=(Get-FileHash -Algorithm SHA256 -LiteralPath $pagesPath).Hash
    links_sha256=(Get-FileHash -Algorithm SHA256 -LiteralPath $linksPath).Hash
}
$manifestPath=Join-Path $resolvedOutput "rmk_candidate_event_page_probe_manifest.json"
[IO.File]::WriteAllText($manifestPath,($manifest|ConvertTo-Json -Depth 6),[Text.UTF8Encoding]::new($false))
$manifest|ConvertTo-Json -Depth 6
