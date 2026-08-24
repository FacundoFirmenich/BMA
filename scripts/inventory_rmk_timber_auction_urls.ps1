param(
    [string]$OutputDir = "evidence/probes/rmk-url-inventory-v1",
    [int]$MinimumYear = 2023,
    [int]$MaximumYear = 2026,
    [int]$MaximumEventPages = 64
)

$ErrorActionPreference = "Stop"
$indexUrl = "https://rmk.ee/kuulutused/metsa-ja-puidu-muuk/"
$referenceUrls = @(
    "https://rmk.ee/spetsialist/puidu-muuk/muugikalender/",
    "https://rmk.ee/spetsialist/puidu-muuk/puidumuugi-pohimotted/"
)

function Get-TextSha256([string]$Text) {
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($Text)
        return ([System.BitConverter]::ToString($sha.ComputeHash($bytes))).Replace("-", "")
    }
    finally {
        $sha.Dispose()
    }
}

function Resolve-Link([string]$BaseUrl, [string]$Href) {
    if ([string]::IsNullOrWhiteSpace($Href)) { return $null }
    return ([System.Uri]::new([System.Uri]::new($BaseUrl), $Href)).AbsoluteUri
}

function Get-Role([string]$Url, [string]$Text, [string]$Context) {
    $probe = ($Url + " " + $Text).ToLowerInvariant()
    if ($probe -match "edukad|winner|protokoll") { return "RESULT" }
    if ($probe -match "myygiobjekt|müügiobjekt|pakkumuse|offer") { return "OFFER_OR_FORM" }
    if ($probe -match "hinnastatistika|veohind|veokaugus|tariff|distance") { return "NORMALIZATION_REFERENCE" }
    if ($Context -eq "INDEX" -and $Url -match "\.xlsx(?:\?|$)") { return "RESULT_OR_REFERENCE_UNRESOLVED" }
    return "PAYLOAD_ROLE_UNRESOLVED"
}

$resolvedOutput = [System.IO.Path]::GetFullPath((Join-Path (Get-Location) $OutputDir))
New-Item -ItemType Directory -Path $resolvedOutput -Force | Out-Null

$pageRecords = [System.Collections.Generic.List[object]]::new()
$payloadRecords = [System.Collections.Generic.List[object]]::new()

function Fetch-HtmlPage([string]$Url, [string]$Kind, [string]$EventDate = "") {
    $response = Invoke-WebRequest -Uri $Url -MaximumRedirection 5
    $contentType = [string]$response.Headers["Content-Type"]
    if ($contentType -notmatch "text/html") {
        throw "Non-HTML response blocked for ${Url}: $contentType"
    }
    $content = [string]$response.Content
    $pageRecords.Add([pscustomobject]@{
        page_kind = $Kind
        event_date = $EventDate
        url = $Url
        http_status = [int]$response.StatusCode
        content_type = $contentType
        content_chars = $content.Length
        html_utf8_sha256 = Get-TextSha256 $content
    })
    return $response
}

$indexResponse = Fetch-HtmlPage -Url $indexUrl -Kind "INDEX"
$eventPages = @{}
foreach ($link in $indexResponse.Links) {
    $absolute = Resolve-Link -BaseUrl $indexUrl -Href ([string]$link.href)
    if (-not $absolute) { continue }
    if ($absolute -match "/kuulutused/metsa-ja-puidu-muuk/(?<day>\d{2})-(?<month>\d{2})-(?<year>\d{4})/?$") {
        $year = [int]$Matches.year
        if ($year -ge $MinimumYear -and $year -le $MaximumYear) {
            $date = "$($Matches.year)-$($Matches.month)-$($Matches.day)"
            $eventPages[$absolute] = $date
        }
    }
    elseif ($absolute -match "\.(xlsx|xls|csv|pdf)(?:\?|$)") {
        $payloadRecords.Add([pscustomobject]@{
            event_date = ""
            discovery_context = "INDEX"
            discovery_page = $indexUrl
            link_text = ([string]$link.innerText).Trim()
            payload_url = $absolute
            role_guess = Get-Role -Url $absolute -Text ([string]$link.innerText) -Context "INDEX"
            payload_opened = $false
        })
    }
}

if ($eventPages.Count -gt $MaximumEventPages) {
    throw "Event page cap exceeded: $($eventPages.Count) > $MaximumEventPages"
}

foreach ($entry in ($eventPages.GetEnumerator() | Sort-Object Value, Name)) {
    $eventResponse = Fetch-HtmlPage -Url $entry.Key -Kind "EVENT" -EventDate $entry.Value
    foreach ($link in $eventResponse.Links) {
        $absolute = Resolve-Link -BaseUrl $entry.Key -Href ([string]$link.href)
        if (-not $absolute -or $absolute -notmatch "\.(xlsx|xls|csv|pdf)(?:\?|$)") { continue }
        $payloadRecords.Add([pscustomobject]@{
            event_date = $entry.Value
            discovery_context = "EVENT"
            discovery_page = $entry.Key
            link_text = ([string]$link.innerText).Trim()
            payload_url = $absolute
            role_guess = Get-Role -Url $absolute -Text ([string]$link.innerText) -Context "EVENT"
            payload_opened = $false
        })
    }
}

foreach ($referenceUrl in $referenceUrls) {
    $referenceResponse = Fetch-HtmlPage -Url $referenceUrl -Kind "REFERENCE"
    foreach ($link in $referenceResponse.Links) {
        $absolute = Resolve-Link -BaseUrl $referenceUrl -Href ([string]$link.href)
        if (-not $absolute -or $absolute -notmatch "\.(xlsx|xls|csv|pdf)(?:\?|$)") { continue }
        $payloadRecords.Add([pscustomobject]@{
            event_date = ""
            discovery_context = "REFERENCE"
            discovery_page = $referenceUrl
            link_text = ([string]$link.innerText).Trim()
            payload_url = $absolute
            role_guess = Get-Role -Url $absolute -Text ([string]$link.innerText) -Context "REFERENCE"
            payload_opened = $false
        })
    }
}

$uniquePayloads = $payloadRecords |
    Sort-Object event_date, discovery_context, discovery_page, payload_url -Unique
$pageCsv = Join-Path $resolvedOutput "rmk_html_page_registry.csv"
$payloadCsv = Join-Path $resolvedOutput "rmk_payload_url_inventory.csv"
$pageRecords | Sort-Object page_kind, event_date, url | Export-Csv -NoTypeInformation -Encoding utf8 -LiteralPath $pageCsv
$uniquePayloads | Export-Csv -NoTypeInformation -Encoding utf8 -LiteralPath $payloadCsv

$manifest = [ordered]@{
    schema = "rmk-timber-url-inventory/v1"
    generated_at = (Get-Date -Format o)
    index_url = $indexUrl
    minimum_year = $MinimumYear
    maximum_year = $MaximumYear
    event_pages = $eventPages.Count
    html_pages_fetched = $pageRecords.Count
    payload_urls_discovered = @($uniquePayloads).Count
    payloads_opened = 0
    invariant = "HTML_ONLY_PAYLOAD_URL_INVENTORY_NO_XLSX_PDF_CSV_OPENED"
    outputs = [ordered]@{
        html_page_registry = [ordered]@{ path = "rmk_html_page_registry.csv"; sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $pageCsv).Hash }
        payload_url_inventory = [ordered]@{ path = "rmk_payload_url_inventory.csv"; sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $payloadCsv).Hash }
    }
}
$manifestPath = Join-Path $resolvedOutput "rmk_inventory_manifest.json"
[System.IO.File]::WriteAllText($manifestPath, ($manifest | ConvertTo-Json -Depth 8), [System.Text.UTF8Encoding]::new($false))

$manifest | ConvertTo-Json -Depth 8
