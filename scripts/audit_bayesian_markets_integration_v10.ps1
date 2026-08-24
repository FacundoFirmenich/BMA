param([string]$OutputPath = "governance/KCH_BAYESIAN_MARKETS_V10_AUDIT.json")
$ErrorActionPreference = "Stop"
$checks = [Collections.Generic.List[object]]::new()
function Add-Check([string]$Name, [bool]$Pass, [object]$Observed, [object]$Expected) {
    $checks.Add([pscustomobject]@{name = $Name; pass = $Pass; observed = $Observed; expected = $Expected})
}
function File-Hash([string]$Path) {(Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash}
$contract = Get-Content -LiteralPath "governance/KCH_BAYESIAN_MARKETS_EVIDENCE_CONTRACT_V10.json" -Raw | ConvertFrom-Json
$v9 = Get-Content -LiteralPath $contract.prior_audit.path -Raw | ConvertFrom-Json
Add-Check "prior_v9.audit_hash" ((File-Hash $contract.prior_audit.path) -eq $contract.prior_audit.sha256) (File-Hash $contract.prior_audit.path) $contract.prior_audit.sha256
Add-Check "prior_v9.status" (($v9.status -eq "PASS") -and ($v9.checks -eq 55) -and ($v9.failures -eq 0)) "$($v9.status)/$($v9.checks)/$($v9.failures)" "PASS/55/0"
Add-Check "prior.contract_hash" ((File-Hash $contract.prior_contract.path) -eq $contract.prior_contract.sha256) (File-Hash $contract.prior_contract.path) $contract.prior_contract.sha256
Add-Check "prior.receipt_hash" ((File-Hash $contract.prior_receipt.path) -eq $contract.prior_receipt.sha256) (File-Hash $contract.prior_receipt.path) $contract.prior_receipt.sha256
Add-Check "mission.hash" ((File-Hash $contract.mission_register.path) -eq $contract.mission_register.sha256) (File-Hash $contract.mission_register.path) $contract.mission_register.sha256
Add-Check "checkpoint.hash" ((File-Hash $contract.checkpoint.path) -eq $contract.checkpoint.sha256) (File-Hash $contract.checkpoint.path) $contract.checkpoint.sha256
foreach ($item in $contract.new_frozen_evidence) {
    $exists = Test-Path -LiteralPath $item.path
    Add-Check "exists.$($item.path)" $exists $exists $true
    if ($exists) {
        $observed = File-Hash $item.path
        Add-Check "hash.$($item.path)" ($observed -eq $item.sha256) $observed $item.sha256
    }
}
$euroManifest = Get-Content -LiteralPath "evidence/runs/hbp-eurostat-sts-es-c-v0.1-2026-07-freeze/manifest.json" -Raw | ConvertFrom-Json
$euroFailures = 0
foreach ($item in $euroManifest.files) {
    if ((-not (Test-Path -LiteralPath $item.path)) -or ((File-Hash $item.path) -ne $item.sha256) -or ((Get-Item -LiteralPath $item.path).Length -ne $item.bytes)) {$euroFailures++}
}
Add-Check "parent.eurostat_manifest" (($euroManifest.files.Count -eq 5) -and ($euroFailures -eq 0)) "$($euroManifest.files.Count)/$euroFailures" "5/0"
$capturePath = "evidence/runs/hbp-indec-prodcom-public-custody-probe-v0.1/capture_manifest.json"
$capture = Get-Content -LiteralPath $capturePath -Raw | ConvertFrom-Json
$captureFailures = 0
foreach ($item in $capture.records) {
    $path = Join-Path (Split-Path $capturePath) $item.name
    if ((-not (Test-Path -LiteralPath $path)) -or ((File-Hash $path) -ne $item.sha256) -or ((Get-Item -LiteralPath $path).Length -ne $item.byte_count)) {$captureFailures++}
}
Add-Check "parent.indec_prodcom_capture" (($capture.records.Count -eq 6) -and ($captureFailures -eq 0)) "$($capture.records.Count)/$captureFailures" "6/0"
$ipi = Get-Content -LiteralPath "preregistrations/HBP_INDEC_IPI_SA_2026_07_FREEZE_V0.1.json" -Raw | ConvertFrom-Json
Add-Check "ipi.source_hash" ((File-Hash $ipi.jurisdiction.source_workbook) -eq $ipi.jurisdiction.source_workbook_sha256) (File-Hash $ipi.jurisdiction.source_workbook) $ipi.jurisdiction.source_workbook_sha256
Add-Check "ipi.target" (($ipi.target.month -eq "2026-07") -and $ipi.target.one_step_only -and $ipi.target.must_be_absent_from_workbook) "$($ipi.target.month)/$($ipi.target.one_step_only)/$($ipi.target.must_be_absent_from_workbook)" "2026-07/True/True"
$euro = Get-Content -LiteralPath "preregistrations/HBP_EUROSTAT_STS_ES_C_2026_07_ADJUDICATION_V0.1.json" -Raw | ConvertFrom-Json
Add-Check "euro.parent_hash" ((File-Hash $euro.parent_freeze) -eq $euro.parent_freeze_sha256) (File-Hash $euro.parent_freeze) $euro.parent_freeze_sha256
Add-Check "euro.one_get" ($euro.capture_contract.one_get_only -and ($euro.target_month -eq "2026-07")) "$($euro.capture_contract.one_get_only)/$($euro.target_month)" "True/2026-07"
$ucii = Get-Content -LiteralPath "preregistrations/HBP_INDEC_UCII_2026_07_CAPTURE_V0.1.json" -Raw | ConvertFrom-Json
Add-Check "ucii.schema_only" (($ucii.status -eq "FROZEN_BEFORE_WORKBOOK_ACQUISITION_SCHEMA_CAPTURE_ONLY") -and ($ucii.forbidden_operations -contains "FIT") -and ($ucii.forbidden_operations -contains "FORECAST")) $ucii.status "FROZEN_BEFORE_WORKBOOK_ACQUISITION_SCHEMA_CAPTURE_ONLY"
foreach ($path in $contract.pre_execution_absence) {
    $absent = -not (Test-Path -LiteralPath $path)
    Add-Check "pre_execution_absent.$path" $absent $absent $true
}
Add-Check "invariants.no_global_winner" ($null -eq $contract.hard_invariants.global_winner) $contract.hard_invariants.global_winner $null
Add-Check "invariants.no_pooling" $contract.hard_invariants.N_to_1_pooling_forbidden $contract.hard_invariants.N_to_1_pooling_forbidden $true
$failures = @($checks | Where-Object {-not $_.pass})
$audit = [ordered]@{
    schema = "kch-bayesian-markets-v10-audit/v1"
    generated_at = Get-Date -Format o
    status = if ($failures.Count) {"FAIL"} else {"PASS"}
    checks = $checks.Count
    failures = $failures.Count
    prior_v9_checks = $v9.checks
    prior_v9_failures = $v9.failures
    adverse_states_asserted = $contract.adverse_states
    details = $checks
}
[IO.File]::WriteAllText([IO.Path]::GetFullPath((Join-Path (Get-Location) $OutputPath)), ($audit | ConvertTo-Json -Depth 12), [Text.UTF8Encoding]::new($false))
$audit | ConvertTo-Json -Depth 3
if ($failures.Count) {exit 1}
