param(
    [string]$InputCsv = (Join-Path $PSScriptRoot '..\inventory\BAYESIAN_MARKETS_LOCAL_SOURCE_CENSUS_V2.csv'),
    [string]$OutputDirectory = (Join-Path $PSScriptRoot '..\inventory\deduplicated-v3'),
    [string]$RemovalReceipt = (Join-Path $PSScriptRoot '..\governance\SPACE_RECOVERY_DUPLICATE_ZIP_20260816.json')
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $InputCsv -PathType Leaf)) {
    throw "Input census not found: $InputCsv"
}

$inputHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $InputCsv).Hash
$sourceRows = @(Import-Csv -LiteralPath $InputCsv)
$fileRows = @($sourceRows | Where-Object item_type -eq 'FILE')
$directoryRows = @($sourceRows | Where-Object item_type -eq 'DIRECTORY')
$results = [Collections.Generic.List[object]]::new()
$errors = [Collections.Generic.List[object]]::new()
$containerExtensions = @('.zip', '.rar', '.7z', '.tar', '.gz', '.tgz', '.whl', '.docx', '.xlsx', '.xlsm', '.pdf')
$verifiedRemovalMap = @{}
$removalReceiptHash = $null
if (Test-Path -LiteralPath $RemovalReceipt -PathType Leaf) {
    $receipt = Get-Content -Raw -LiteralPath $RemovalReceipt | ConvertFrom-Json
    $survivorExists = Test-Path -LiteralPath $receipt.surviving_identical_path -PathType Leaf
    if (-not $survivorExists) { throw "Removal receipt survivor is missing: $($receipt.surviving_identical_path)" }
    $survivor = Get-Item -LiteralPath $receipt.surviving_identical_path -Force
    $survivorHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $receipt.surviving_identical_path).Hash
    if ($survivorHash -ne $receipt.sha256 -or [int64]$survivor.Length -ne [int64]$receipt.bytes_freed) {
        throw 'Removal receipt does not match surviving replica bytes'
    }
    $removalReceiptHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $RemovalReceipt).Hash
    $verifiedRemovalMap[$receipt.removed_path.ToLowerInvariant()] = [pscustomobject]@{
        sha256 = $survivorHash
        bytes = [int64]$survivor.Length
        receipt_path = [IO.Path]::GetFullPath($RemovalReceipt)
        receipt_sha256 = $removalReceiptHash
        surviving_path = $receipt.surviving_identical_path
    }
}

foreach ($row in $fileRows) {
    $path = $row.source_path
    $extension = [IO.Path]::GetExtension($path).ToLowerInvariant()
    $exists = Test-Path -LiteralPath $path -PathType Leaf
    $bytes = $null
    $sha256 = $null
    $state = 'MISSING_AT_V3_HASH_PASS'
    $resolutionReceipt = $null

    if ($exists) {
        try {
            $item = Get-Item -LiteralPath $path -Force -ErrorAction Stop
            $bytes = [int64]$item.Length
            $sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $path -ErrorAction Stop).Hash
            $state = 'HASHED_SHA256'
        } catch {
            $state = 'HASH_FAILED'
            $errors.Add([pscustomobject]@{
                source_path = $path
                phase = 'SHA256'
                message = $_.Exception.Message
            })
        }
    } else {
        $key = $path.ToLowerInvariant()
        if ($verifiedRemovalMap.ContainsKey($key)) {
            $resolved = $verifiedRemovalMap[$key]
            $bytes = $resolved.bytes
            $sha256 = $resolved.sha256
            $state = 'RESOLVED_BY_VERIFIED_REMOVAL_RECEIPT'
            $resolutionReceipt = $resolved.receipt_path
        } else {
            $errors.Add([pscustomobject]@{
                source_path = $path
                phase = 'EXISTENCE'
                message = 'File recorded by V2 is no longer present at the recorded path'
            })
        }
    }

    $recordedBytes = if ([string]::IsNullOrWhiteSpace($row.byte_count_recursive)) { $null } else { [int64]$row.byte_count_recursive }
    $results.Add([pscustomobject]@{
        source_path = $path
        discovered_under = $row.discovered_under
        match_basis = $row.match_basis
        extension = $extension
        is_container_or_compound_document = $extension -in $containerExtensions
        v2_recorded_bytes = $recordedBytes
        v3_observed_bytes = $bytes
        byte_count_matches_v2 = ($null -ne $bytes -and $null -ne $recordedBytes -and $bytes -eq $recordedBytes)
        sha256 = $sha256
        hash_state = $state
        resolution_receipt = $resolutionReceipt
        dedup_group_size = $null
        replica_state = 'NOT_HASHED'
        source_lineage = $row.source_lineage
        canonical_destination = $row.canonical_destination
        disposition = 'PRESERVE_READ_ONLY_PENDING_CONTENT_ADJUDICATION'
    })
}

$physicallyHashed = @($results | Where-Object hash_state -eq 'HASHED_SHA256')
$receiptResolved = @($results | Where-Object hash_state -eq 'RESOLVED_BY_VERIFIED_REMOVAL_RECEIPT')
$resolvedRows = @($results | Where-Object hash_state -in @('HASHED_SHA256', 'RESOLVED_BY_VERIFIED_REMOVAL_RECEIPT'))
$hashGroups = @($resolvedRows | Group-Object sha256)
foreach ($group in $hashGroups) {
    $size = $group.Count
    foreach ($member in $group.Group) {
        $member.dedup_group_size = $size
        $member.replica_state = if ($size -eq 1) { 'UNIQUE_BYTES_WITHIN_V2_CANDIDATE_SET' } else { 'EXACT_BYTE_REPLICA_GROUP_MEMBER' }
    }
}

$uniqueBytes = [int64]0
foreach ($group in $hashGroups) {
    $uniqueBytes += [int64]$group.Group[0].v3_observed_bytes
}
$physicalBytes = [int64](($physicallyHashed | Measure-Object v3_observed_bytes -Sum).Sum)
$duplicateGroups = @($hashGroups | Where-Object Count -gt 1)
$duplicateMembers = [int64](($duplicateGroups | Measure-Object Count -Sum).Sum)
$containers = @($results | Where-Object is_container_or_compound_document)
$gapCount = @($results | Where-Object hash_state -notin @('HASHED_SHA256', 'RESOLVED_BY_VERIFIED_REMOVAL_RECEIPT')).Count

New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
$filesCsv = Join-Path $OutputDirectory 'BAYESIAN_MARKETS_DEDUPLICATED_FILE_CENSUS_V3.csv'
$directoriesCsv = Join-Path $OutputDirectory 'BAYESIAN_MARKETS_DIRECTORY_CANDIDATES_V3.csv'
$containersCsv = Join-Path $OutputDirectory 'BAYESIAN_MARKETS_CONTAINER_REVIEW_QUEUE_V3.csv'
$errorsCsv = Join-Path $OutputDirectory 'BAYESIAN_MARKETS_DEDUPLICATION_ERRORS_V3.csv'
$manifestJson = Join-Path $OutputDirectory 'BAYESIAN_MARKETS_DEDUPLICATED_CENSUS_MANIFEST_V3.json'

$results | Sort-Object source_path | Export-Csv -LiteralPath $filesCsv -NoTypeInformation -Encoding utf8
$directoryRows | Sort-Object source_path | Export-Csv -LiteralPath $directoriesCsv -NoTypeInformation -Encoding utf8
$containers | Sort-Object source_path | Export-Csv -LiteralPath $containersCsv -NoTypeInformation -Encoding utf8
$errors | Sort-Object source_path | Export-Csv -LiteralPath $errorsCsv -NoTypeInformation -Encoding utf8

$manifest = [ordered]@{
    schema = 'bayesian-markets-deduplicated-census/v3'
    generated_at = (Get-Date).ToUniversalTime().ToString('o')
    input = [ordered]@{
        path = [IO.Path]::GetFullPath($InputCsv)
        sha256 = $inputHash
        candidate_rows = $sourceRows.Count
        file_rows = $fileRows.Count
        directory_rows = $directoryRows.Count
        removal_receipt = [ordered]@{
            path = if ($removalReceiptHash) { [IO.Path]::GetFullPath($RemovalReceipt) } else { $null }
            sha256 = $removalReceiptHash
        }
    }
    result = [ordered]@{
        files_physically_hashed = $physicallyHashed.Count
        rows_resolved_by_verified_removal_receipt = $receiptResolved.Count
        v2_file_rows_resolved = $resolvedRows.Count
        files_missing_or_failed = $gapCount
        physical_bytes = $physicalBytes
        unique_sha256_objects = $hashGroups.Count
        unique_bytes = $uniqueBytes
        exact_duplicate_groups = $duplicateGroups.Count
        exact_duplicate_members = $duplicateMembers
        exact_redundant_logical_rows = $resolvedRows.Count - $hashGroups.Count
        exact_redundant_present_files = $physicallyHashed.Count - $hashGroups.Count
        container_or_compound_document_rows = $containers.Count
        container_internal_bytes_read = $false
    }
    outputs = [ordered]@{
        file_census_csv = [IO.Path]::GetFullPath($filesCsv)
        directory_candidates_csv = [IO.Path]::GetFullPath($directoriesCsv)
        container_review_queue_csv = [IO.Path]::GetFullPath($containersCsv)
        errors_csv = [IO.Path]::GetFullPath($errorsCsv)
    }
    evidence_boundary = 'EVERY_EXISTING_FILE_ROW_FROM_V2_HASHED_BYTE_FOR_BYTE; EXACT_REPLICAS_IDENTIFIED_WITHOUT_DELETION; ARCHIVE_AND_COMPOUND_DOCUMENT_INTERNAL_MEMBERS_NOT_YET_ENUMERATED; V2_DISCOVERY_SCOPE_LIMITS_REMAIN'
    authority = [ordered]@{
        classification_authority = $false
        deletion_authority = $false
        canonical_representative_selection = $false
        global_winner = $null
    }
}

[IO.File]::WriteAllText(
    [IO.Path]::GetFullPath($manifestJson),
    ($manifest | ConvertTo-Json -Depth 8),
    [Text.UTF8Encoding]::new($false)
)

[pscustomobject]@{
    status = if ($gapCount -gt 0) { 'NONTERMINAL_GAPS_PRESERVED' } elseif ($receiptResolved.Count -gt 0) { 'COMPLETE_FOR_V2_FILE_ROWS_WITH_VERIFIED_REMOVAL_RECEIPT' } else { 'COMPLETE_FOR_V2_FILE_ROWS' }
    files_physically_hashed = $physicallyHashed.Count
    rows_resolved_by_verified_removal_receipt = $receiptResolved.Count
    unique_sha256_objects = $hashGroups.Count
    exact_duplicate_groups = $duplicateGroups.Count
    exact_redundant_logical_rows = $resolvedRows.Count - $hashGroups.Count
    exact_redundant_present_files = $physicallyHashed.Count - $hashGroups.Count
    physical_bytes = $physicalBytes
    unique_bytes = $uniqueBytes
    containers_pending_internal_review = $containers.Count
    errors = $errors.Count
    manifest = $manifestJson
} | ConvertTo-Json -Compress
