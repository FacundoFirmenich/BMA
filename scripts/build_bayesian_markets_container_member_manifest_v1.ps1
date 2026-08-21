param(
    [string]$ContainerQueue = (Join-Path $PSScriptRoot '..\inventory\deduplicated-v3\BAYESIAN_MARKETS_CONTAINER_REVIEW_QUEUE_V3.csv'),
    [string]$OutputDirectory = (Join-Path $PSScriptRoot '..\inventory\container-members-v1')
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $ContainerQueue -PathType Leaf)) {
    throw "Container queue not found: $ContainerQueue"
}

Add-Type -AssemblyName System.IO.Compression.FileSystem
$queueHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $ContainerQueue).Hash
$queue = @(Import-Csv -LiteralPath $ContainerQueue)
$members = [Collections.Generic.List[object]]::new()
$containers = [Collections.Generic.List[object]]::new()
$errors = [Collections.Generic.List[object]]::new()
$zipLike = @('.zip', '.whl', '.docx', '.xlsx', '.xlsm')

function Get-StreamSha256 {
    param([System.IO.Stream]$Stream)
    $algorithm = [Security.Cryptography.SHA256]::Create()
    try {
        return [Convert]::ToHexString($algorithm.ComputeHash($Stream))
    } finally {
        $algorithm.Dispose()
    }
}

$groups = @($queue | Where-Object { -not [string]::IsNullOrWhiteSpace($_.sha256) } | Group-Object sha256)
foreach ($group in $groups) {
    $representative = @($group.Group | Where-Object { $_.hash_state -eq 'HASHED_SHA256' -and (Test-Path -LiteralPath $_.source_path -PathType Leaf) } | Sort-Object source_path | Select-Object -First 1)
    if ($representative.Count -ne 1) {
        $errors.Add([pscustomobject]@{ container_sha256 = $group.Name; phase = 'REPRESENTATIVE'; path = $null; message = 'No present byte-verified representative available' })
        continue
    }

    $row = $representative[0]
    $path = $row.source_path
    $extension = $row.extension.ToLowerInvariant()
    $memberCountBefore = $members.Count
    $state = 'UNSUPPORTED_CONTAINER_FORMAT'

    try {
        if ($extension -in $zipLike) {
            $archive = [IO.Compression.ZipFile]::OpenRead($path)
            try {
                foreach ($entry in @($archive.Entries | Sort-Object FullName)) {
                    $isDirectory = $entry.FullName.EndsWith('/') -or $entry.FullName.EndsWith('\')
                    $memberHash = $null
                    if (-not $isDirectory) {
                        $stream = $entry.Open()
                        try { $memberHash = Get-StreamSha256 -Stream $stream } finally { $stream.Dispose() }
                    }
                    $members.Add([pscustomobject]@{
                        container_sha256 = $group.Name
                        container_extension = $extension
                        representative_path = $path
                        member_path = $entry.FullName
                        member_type = if ($isDirectory) { 'DIRECTORY' } else { 'FILE' }
                        uncompressed_bytes = [int64]$entry.Length
                        compressed_bytes = [int64]$entry.CompressedLength
                        member_sha256 = $memberHash
                        read_state = if ($isDirectory) { 'DIRECTORY_ENTRY' } else { 'DECOMPRESSED_BYTES_HASHED' }
                    })
                }
            } finally {
                $archive.Dispose()
            }
            $state = 'ZIP_CENTRAL_DIRECTORY_AND_ALL_MEMBER_BYTES_READ'
        } elseif ($extension -eq '.rar') {
            $detailedListing = @(& tar -tvf $path)
            if ($LASTEXITCODE -ne 0) { throw "tar detailed list failed with exit code $LASTEXITCODE" }
            foreach ($line in $detailedListing) {
                $parts = @($line -split '\s+' | Where-Object { $_ -ne '' })
                if ($parts.Count -lt 2) { throw "Unparseable tar listing line: $line" }
                $memberPath = $parts[-1]
                $isDirectory = $line.StartsWith('d')
                $memberHash = $null
                $bytes = [int64]0
                if (-not $isDirectory) {
                    $psi = [Diagnostics.ProcessStartInfo]::new()
                    $psi.FileName = (Get-Command tar).Source
                    $psi.UseShellExecute = $false
                    $psi.RedirectStandardOutput = $true
                    $psi.RedirectStandardError = $true
                    $psi.ArgumentList.Add('-xOf')
                    $psi.ArgumentList.Add($path)
                    $psi.ArgumentList.Add('--')
                    $psi.ArgumentList.Add($memberPath)
                    $process = [Diagnostics.Process]::new()
                    $process.StartInfo = $psi
                    $memory = [IO.MemoryStream]::new()
                    try {
                        if (-not $process.Start()) { throw "Could not start tar for member: $memberPath" }
                        $stderrTask = $process.StandardError.ReadToEndAsync()
                        $process.StandardOutput.BaseStream.CopyTo($memory)
                        $process.WaitForExit()
                        $stderr = $stderrTask.GetAwaiter().GetResult()
                        if ($process.ExitCode -ne 0) { throw ('tar member stream failed for ' + $memberPath + ': ' + $stderr) }
                        $bytes = [int64]$memory.Length
                        $memory.Position = 0
                        $memberHash = Get-StreamSha256 -Stream $memory
                    } finally {
                        $memory.Dispose()
                        $process.Dispose()
                    }
                }
                $members.Add([pscustomobject]@{
                    container_sha256 = $group.Name
                    container_extension = $extension
                    representative_path = $path
                    member_path = $memberPath
                    member_type = if ($isDirectory) { 'DIRECTORY' } else { 'FILE' }
                    uncompressed_bytes = $bytes
                    compressed_bytes = $null
                    member_sha256 = $memberHash
                    read_state = if ($isDirectory) { 'DIRECTORY_ENTRY' } else { 'STREAMED_FROM_ARCHIVE_AND_HASHED_IN_MEMORY' }
                })
            }
            $state = 'RAR_DIRECTORY_AND_ALL_MEMBER_BYTES_STREAMED_AND_HASHED'        } elseif ($extension -eq '.pdf') {
            $members.Add([pscustomobject]@{
                container_sha256 = $group.Name
                container_extension = $extension
                representative_path = $path
                member_path = '[PDF_OUTER_OBJECT]'
                member_type = 'COMPOUND_DOCUMENT'
                uncompressed_bytes = [int64](Get-Item -LiteralPath $path).Length
                compressed_bytes = $null
                member_sha256 = $group.Name
                read_state = 'OUTER_BYTES_HASHED_SEMANTIC_PDF_READ_PENDING'
            })
            $state = 'PDF_OUTER_BYTES_HASHED_SEMANTIC_READ_PENDING'
        }
    } catch {
        $state = 'CONTAINER_READ_FAILED'
        $errors.Add([pscustomobject]@{ container_sha256 = $group.Name; phase = 'MEMBER_READ'; path = $path; message = $_.Exception.Message })
    }

    $containers.Add([pscustomobject]@{
        container_sha256 = $group.Name
        extension = $extension
        physical_replica_count = $group.Count
        representative_path = $path
        representative_bytes = [int64]$row.v3_observed_bytes
        member_rows = $members.Count - $memberCountBefore
        state = $state
    })
}

New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
$membersCsv = Join-Path $OutputDirectory 'BAYESIAN_MARKETS_CONTAINER_MEMBER_MANIFEST_V1.csv'
$containersCsv = Join-Path $OutputDirectory 'BAYESIAN_MARKETS_UNIQUE_CONTAINER_SUMMARY_V1.csv'
$errorsCsv = Join-Path $OutputDirectory 'BAYESIAN_MARKETS_CONTAINER_READ_ERRORS_V1.csv'
$manifestJson = Join-Path $OutputDirectory 'BAYESIAN_MARKETS_CONTAINER_CUSTODY_MANIFEST_V1.json'

$members | Export-Csv -LiteralPath $membersCsv -NoTypeInformation -Encoding utf8
$containers | Export-Csv -LiteralPath $containersCsv -NoTypeInformation -Encoding utf8
$errors | Export-Csv -LiteralPath $errorsCsv -NoTypeInformation -Encoding utf8

$memberFiles = @($members | Where-Object member_type -eq 'FILE')
$uniqueMemberHashes = @($memberFiles | Where-Object member_sha256 | Select-Object -ExpandProperty member_sha256 -Unique)
$pendingPdf = @($containers | Where-Object state -eq 'PDF_OUTER_BYTES_HASHED_SEMANTIC_READ_PENDING').Count
$manifest = [ordered]@{
    schema = 'bayesian-markets-container-custody/v1'
    generated_at = (Get-Date).ToUniversalTime().ToString('o')
    input = [ordered]@{ path = [IO.Path]::GetFullPath($ContainerQueue); sha256 = $queueHash; physical_rows = $queue.Count }
    result = [ordered]@{
        unique_containers = $groups.Count
        container_summaries = $containers.Count
        member_rows = $members.Count
        member_file_rows = $memberFiles.Count
        unique_member_sha256 = $uniqueMemberHashes.Count
        read_errors = $errors.Count
        pdf_semantic_reads_pending = $pendingPdf
    }
    evidence_boundary = 'ONE_PRESENT_REPRESENTATIVE_PER_OUTER_SHA256; ZIP_LIKE_AND_RAR_MEMBER_BYTES_READ_AND_HASHED; REPLICA CONTAINERS NOT REOPENED; PDF OUTER BYTES ONLY AND SEMANTIC READ PENDING; NO SOURCE MUTATION'
    authority = [ordered]@{ classification_authority = $false; deletion_authority = $false; global_winner = $null }
}
[IO.File]::WriteAllText([IO.Path]::GetFullPath($manifestJson), ($manifest | ConvertTo-Json -Depth 8), [Text.UTF8Encoding]::new($false))

[pscustomobject]@{
    status = if ($errors.Count -gt 0) { 'NONTERMINAL_CONTAINER_READ_ERRORS' } elseif ($pendingPdf -gt 0) { 'MEMBER_BYTES_COMPLETE_PDF_SEMANTIC_READ_PENDING' } else { 'COMPLETE_FOR_UNIQUE_CONTAINERS' }
    unique_containers = $groups.Count
    member_rows = $members.Count
    member_file_rows = $memberFiles.Count
    unique_member_sha256 = $uniqueMemberHashes.Count
    errors = $errors.Count
    pdf_semantic_reads_pending = $pendingPdf
    manifest = $manifestJson
} | ConvertTo-Json -Compress
