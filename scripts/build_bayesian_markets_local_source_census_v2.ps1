param(
    [string]$OutputDirectory = (Join-Path $PSScriptRoot '..\inventory'),
    [int64]$MaximumContentFileBytes = 20971520
)

$ErrorActionPreference = 'Stop'

$rootSpecifications = @(
    [pscustomobject]@{ Path = 'C:\Users\User\Documents\Codex'; Depth = 8 },
    [pscustomobject]@{ Path = 'C:\Users\User\Desktop'; Depth = 6 },
    [pscustomobject]@{ Path = 'C:\Users\User\Downloads'; Depth = 6 },
    [pscustomobject]@{ Path = 'C:\Users\User\OneDrive'; Depth = 8 },
    [pscustomobject]@{ Path = 'C:\Users\User\3D Objects'; Depth = 8 },
    [pscustomobject]@{ Path = 'C:\Users\User\.codex\.chatgpt-projects'; Depth = 8 },
    [pscustomobject]@{ Path = 'D:\'; Depth = 4 },
    [pscustomobject]@{ Path = 'E:\'; Depth = 4 }
)

$lineagePattern = '(?i)(^|[^a-z0-9])(bayme|bma|bayesian[ _-]*(markets|macroeconomics)|statistical[ _-]*programming[ _-]*bayme)([^a-z0-9]|$)'
$excludePattern = '(?i)[\\/](\.git|node_modules|__pycache__|\.venv|venv|\.pytest_cache|\.mypy_cache|\.ruff_cache)([\\/]|$)'
$contentExtensions = @('.md', '.txt', '.json', '.jsonl', '.csv', '.tsv', '.yaml', '.yml', '.toml', '.py', '.ps1', '.tex', '.html', '.xml')

$rootStatus = [System.Collections.Generic.List[object]]::new()
$candidateMap = @{}
$scanErrors = [System.Collections.Generic.List[object]]::new()

function Add-Candidate {
    param(
        [System.IO.FileSystemInfo]$Item,
        [string]$Root,
        [string]$MatchBasis
    )

    $key = $Item.FullName.ToLowerInvariant()
    if ($candidateMap.ContainsKey($key)) {
        $existing = $candidateMap[$key]
        if ($existing.match_basis -notmatch [regex]::Escape($MatchBasis)) {
            $existing.match_basis = "$($existing.match_basis)+$MatchBasis"
        }
        return
    }

    $isDirectory = $Item -is [System.IO.DirectoryInfo]
    $fileCount = $null
    $byteCount = $null
    $latestWrite = $Item.LastWriteTimeUtc.ToString('o')
    $sha256 = $null
    $inventoryState = 'METADATA_CAPTURED'

    if ($isDirectory) {
        $inventoryState = 'DIRECTORY_AGGREGATION_DEFERRED_TO_DEDUP_MANIFEST'
    } else {
        $fileCount = 1
        $byteCount = [int64]$Item.Length
        $inventoryState = 'FILE_HASH_DEFERRED_TO_ADJUDICATED_CUSTODY'
    }

    $candidateMap[$key] = [pscustomobject]@{
        source_path = $Item.FullName
        item_type = if ($isDirectory) { 'DIRECTORY' } else { 'FILE' }
        discovered_under = $Root
        match_basis = $MatchBasis
        file_count_recursive = $fileCount
        byte_count_recursive = $byteCount
        latest_write_time_utc = $latestWrite
        sha256_if_file = $sha256
        inventory_state = $inventoryState
        source_lineage = 'UNRESOLVED_SOURCE_LINEAGE'
        canonical_destination = 'UNCLASSIFIED_PENDING_CONTENT_REVIEW'
        disposition = 'PRESERVE_READ_ONLY_PENDING_UNIT_REVIEW'
    }
}

foreach ($spec in $rootSpecifications) {
    $root = $spec.Path
    if (-not (Test-Path -LiteralPath $root -PathType Container)) {
        $rootStatus.Add([pscustomobject]@{ root = $root; requested_depth = $spec.Depth; status = 'ROOT_NOT_PRESENT'; item_count_examined = 0; error_count = 0 })
        continue
    }

    $rootErrors = @()
    $items = @(Get-ChildItem -LiteralPath $root -Recurse -Depth $spec.Depth -Force -ErrorAction SilentlyContinue -ErrorVariable +rootErrors |
        Where-Object { $_.FullName -notmatch $excludePattern })

    foreach ($item in $items) {
        if ($item.Name -match $lineagePattern) {
            Add-Candidate -Item $item -Root $root -MatchBasis 'PATH_NAME'
        }


    }


    foreach ($err in $rootErrors) {
        $scanErrors.Add([pscustomobject]@{ root = $root; phase = 'ROOT_ENUMERATION'; path = $root; message = $err.ToString() })
    }

    $rootStatus.Add([pscustomobject]@{
        root = $root
        requested_depth = $spec.Depth
        status = if ($rootErrors.Count -eq 0) { 'SCANNED_WITHOUT_REPORTED_ERRORS' } else { 'SCANNED_WITH_ACCESS_ERRORS' }
        item_count_examined = $items.Count
        error_count = $rootErrors.Count
    })
}

$namedDirectories = @($candidateMap.Values |
    Where-Object { $_.item_type -eq 'DIRECTORY' } |
    Sort-Object { $_.source_path.Length }, source_path)
$contentScanScopes = [System.Collections.Generic.List[string]]::new()
foreach ($candidateDirectory in $namedDirectories) {
    $path = $candidateDirectory.source_path
    $isNested = $false
    foreach ($scope in $contentScanScopes) {
        if ($path.Equals($scope, [StringComparison]::OrdinalIgnoreCase) -or
            $path.StartsWith($scope.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase)) {
            $isNested = $true
            break
        }
    }
    if (-not $isNested) { $contentScanScopes.Add($path) }
}

foreach ($scope in $contentScanScopes) {
    $scopeRoot = ($candidateMap[$scope.ToLowerInvariant()]).discovered_under
    $rgArguments = @(
        '--files-with-matches', '--hidden', '--no-messages', '--max-filesize', $MaximumContentFileBytes.ToString(),
        '-g', '*.md', '-g', '*.txt', '-g', '*.json', '-g', '*.jsonl', '-g', '*.csv', '-g', '*.tsv',
        '-g', '*.yaml', '-g', '*.yml', '-g', '*.toml', '-g', '*.py', '-g', '*.ps1', '-g', '*.tex',
        '-g', '*.html', '-g', '*.xml', '-g', '!**/.git/**', '-g', '!**/node_modules/**',
        '-g', '!**/__pycache__/**', '-g', '!**/.venv/**', '-g', '!**/venv/**',
        $lineagePattern, $scope
    )
    $contentPaths = @(& rg @rgArguments 2>$null)
    if ($LASTEXITCODE -notin @(0, 1)) {
        $scanErrors.Add([pscustomobject]@{ root = $scopeRoot; phase = 'RG_BOUNDED_CONTENT_SCAN'; path = $scope; message = "rg exit code $LASTEXITCODE" })
    }
    foreach ($contentPath in $contentPaths) {
        try {
            Add-Candidate -Item (Get-Item -LiteralPath $contentPath -Force -ErrorAction Stop) -Root $scopeRoot -MatchBasis 'CONTENT_ANCHOR'
        } catch {
            $scanErrors.Add([pscustomobject]@{ root = $scopeRoot; phase = 'CONTENT_RESULT_METADATA'; path = $contentPath; message = $_.Exception.Message })
        }
    }
}

$ordered = @($candidateMap.Values | Sort-Object source_path)
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null

$csvPath = Join-Path $OutputDirectory 'BAYESIAN_MARKETS_LOCAL_SOURCE_CENSUS_V2.csv'
$jsonPath = Join-Path $OutputDirectory 'BAYESIAN_MARKETS_LOCAL_SOURCE_CENSUS_V2.json'
$errorsPath = Join-Path $OutputDirectory 'BAYESIAN_MARKETS_LOCAL_SOURCE_CENSUS_V2_ERRORS.csv'

$ordered | Export-Csv -LiteralPath $csvPath -NoTypeInformation -Encoding utf8
$scanErrors | Export-Csv -LiteralPath $errorsPath -NoTypeInformation -Encoding utf8

$payload = [ordered]@{
    schema = 'bayesian-markets-local-source-census/v2'
    generated_at = (Get-Date).ToUniversalTime().ToString('o')
    root_status = @($rootStatus)
    search_rule = [ordered]@{
        lineage_pattern = $lineagePattern
        maximum_depth_is_root_specific = $true
        maximum_content_file_bytes = $MaximumContentFileBytes
        content_extensions = $contentExtensions
        exclusions = $excludePattern
        content_scan_scopes = @($contentScanScopes)
    }
    candidate_count = $ordered.Count
    access_or_scan_error_count = $scanErrors.Count
    candidates = $ordered
    evidence_boundary = 'BOUNDED_MULTIROOT_PATH_CENSUS_AND_TEXT_SCAN_INSIDE_MINIMAL_NAMED_LINEAGE_SCOPES; ARCHIVE_INTERNAL_BYTES_NATIVE_CHATS_DRIVE_AND_GITHUB_REQUIRE_SEPARATE_REGISTRIES; OVERLAPPING_DIRECTORIES_MAY DOUBLE_COUNT_BYTES; NO_CONTENT_ADJUDICATION'
}

$payload | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $jsonPath -Encoding utf8

[pscustomobject]@{
    candidate_count = $ordered.Count
    access_or_scan_error_count = $scanErrors.Count
    csv_path = $csvPath
    json_path = $jsonPath
    errors_path = $errorsPath
} | ConvertTo-Json -Compress
