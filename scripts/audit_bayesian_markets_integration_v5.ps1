param(
    [string]$OutputPath = "governance/KCH_BAYESIAN_MARKETS_V5_AUDIT.json"
)

$ErrorActionPreference = "Stop"
$checks = [Collections.Generic.List[object]]::new()
function Add-Check([string]$Name, [bool]$Pass, [object]$Observed, [object]$Expected) {
    $checks.Add([pscustomobject]@{name=$Name;pass=$Pass;observed=$Observed;expected=$Expected})
}
function File-Hash([string]$Path) { return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash }
function Close-To([double]$Left,[double]$Right,[double]$Tolerance=1e-10){return [Math]::Abs($Left-$Right) -le $Tolerance}

if(-not(Test-Path -LiteralPath ".artifact_probe")){New-Item -ItemType Directory -Path ".artifact_probe"|Out-Null}
$priorAuditPath=".artifact_probe/bma-v4-audit-$([Guid]::NewGuid().ToString('N')).json"
try {
    $null=& "scripts/audit_bayesian_markets_integration_v4.ps1" -OutputPath $priorAuditPath
    $priorAudit=Get-Content -Raw -LiteralPath $priorAuditPath|ConvertFrom-Json
    Add-Check "prior_v4.audit_status" ($priorAudit.status -eq "PASS") $priorAudit.status "PASS"
    Add-Check "prior_v4.audit_failures" ($priorAudit.failures -eq 0) $priorAudit.failures 0
} finally {
    if(Test-Path -LiteralPath $priorAuditPath){Remove-Item -LiteralPath $priorAuditPath -Force}
}

$contract=Get-Content -Raw -LiteralPath "governance/KCH_BAYESIAN_MARKETS_EVIDENCE_CONTRACT_V5.json"|ConvertFrom-Json
$receipt=Get-Content -Raw -LiteralPath "governance/KCH_BAYESIAN_MARKETS_INTEGRATION_RECEIPT_V5.json"|ConvertFrom-Json
Add-Check "contract.prior_hash" ((File-Hash $contract.prior_contract.path) -eq $contract.prior_contract.sha256) (File-Hash $contract.prior_contract.path) $contract.prior_contract.sha256
Add-Check "contract.mission_hash" ((File-Hash $contract.mission_register.path) -eq $contract.mission_register.sha256) (File-Hash $contract.mission_register.path) $contract.mission_register.sha256
foreach($item in $contract.new_frozen_evidence){
    $exists=Test-Path -LiteralPath $item.path
    Add-Check "contract.exists.$($item.path)" $exists $exists $true
    if($exists){$actual=File-Hash $item.path;Add-Check "contract.hash.$($item.path)" ($actual -eq $item.sha256) $actual $item.sha256}
}
$contractHash=File-Hash $receipt.evidence_contract.path
Add-Check "receipt.contract_hash" ($contractHash -eq $receipt.evidence_contract.sha256) $contractHash $receipt.evidence_contract.sha256

$prereg=Get-Content -Raw -LiteralPath "preregistrations/HBP_INDEC_PRODCOM_PUBLIC_CUSTODY_PROBE_V0.1.json"|ConvertFrom-Json
$runRoot="evidence/runs/hbp-indec-prodcom-public-custody-probe-v0.1"
$manifest=Get-Content -Raw -LiteralPath "$runRoot/capture_manifest.json"|ConvertFrom-Json
$adjudication=Get-Content -Raw -LiteralPath "$runRoot/probe_adjudication.json"|ConvertFrom-Json
$prodcom=Get-Content -Raw -LiteralPath "$runRoot/eurostat_prodcom_es_16101035_2024_primary.json"|ConvertFrom-Json
$workbookInspection=Get-Content -Raw -LiteralPath "$runRoot/indec_ipi_series_2026_workbook_inspection.json"|ConvertFrom-Json

Add-Check "probe.preregistered_before_acquisition" ($prereg.status -eq "PREREGISTERED_BEFORE_BYTE_ACQUISITION") $prereg.status "PREREGISTERED_BEFORE_BYTE_ACQUISITION"
Add-Check "probe.prereg_hash_manifest" ((File-Hash "preregistrations/HBP_INDEC_PRODCOM_PUBLIC_CUSTODY_PROBE_V0.1.json") -eq $manifest.preregistration_sha256) (File-Hash "preregistrations/HBP_INDEC_PRODCOM_PUBLIC_CUSTODY_PROBE_V0.1.json") $manifest.preregistration_sha256
Add-Check "probe.capture_count" ($manifest.records.Count -eq 6) $manifest.records.Count 6
foreach($record in $manifest.records){
    $rawPath="$runRoot/$($record.name)"
    $headerPath="$runRoot/$($record.headers_file)"
    Add-Check "capture.http_200.$($record.name)" ($record.http_status -eq 200) $record.http_status 200
    Add-Check "capture.raw_hash.$($record.name)" ((File-Hash $rawPath) -eq $record.sha256) (File-Hash $rawPath) $record.sha256
    Add-Check "capture.header_hash.$($record.name)" ((File-Hash $headerPath) -eq $record.headers_sha256) (File-Hash $headerPath) $record.headers_sha256
}

Add-Check "probe.no_fit" (-not $manifest.invariants.fit_performed) $manifest.invariants.fit_performed $false
Add-Check "probe.no_forecast" (-not $manifest.invariants.forecast_performed) $manifest.invariants.forecast_performed $false
Add-Check "probe.no_score" (-not $manifest.invariants.score_performed) $manifest.invariants.score_performed $false
Add-Check "probe.no_reconstruction" (-not $manifest.invariants.historical_freeze_reconstructed) $manifest.invariants.historical_freeze_reconstructed $false
Add-Check "probe.no_pooling" (-not $manifest.invariants.cross_source_likelihood_pooling) $manifest.invariants.cross_source_likelihood_pooling $false
Add-Check "probe.no_bulk" (-not $manifest.invariants.bulk_download) $manifest.invariants.bulk_download $false

Add-Check "prodcom.dimensions" (($prodcom.id -join ',') -eq 'freq,reporter,product,indicators,time') ($prodcom.id -join ',') 'freq,reporter,product,indicators,time'
Add-Check "prodcom.shape" (($prodcom.size -join ',') -eq '1,1,1,3,1') ($prodcom.size -join ',') '1,1,1,3,1'
Add-Check "prodcom.reporter_ES" ($prodcom.dimension.reporter.category.index.ES -eq 0) $prodcom.dimension.reporter.category.index.ES 0
Add-Check "prodcom.product_16101035" ($prodcom.dimension.product.category.index.'16101035' -eq 0) $prodcom.dimension.product.category.index.'16101035' 0
Add-Check "prodcom.time_2024" ($prodcom.dimension.time.category.index.'2024' -eq 0) $prodcom.dimension.time.category.index.'2024' 0
$prodcomValueCount=@($prodcom.value.PSObject.Properties).Count
Add-Check "prodcom.empty_value" ($prodcomValueCount -eq 0) $prodcomValueCount 0
Add-Check "prodcom.not_estimable" ($adjudication.eurostat_prodcom.status -eq 'NOT_ESTIMABLE_NO_CELL') $adjudication.eurostat_prodcom.status 'NOT_ESTIMABLE_NO_CELL'
Add-Check "prodcom.no_post_hoc_substitution" (-not $contract.prodcom_state.post_hoc_product_substitution) $contract.prodcom_state.post_hoc_product_substitution $false

Add-Check "indec.raw_integrity" ($adjudication.raw_integrity -eq 'PASS_ALL_CAPTURE_HASHES_RECOMPUTED') $adjudication.raw_integrity 'PASS_ALL_CAPTURE_HASHES_RECOMPUTED'
Add-Check "indec.IPI_original" (Close-To $adjudication.indec_ipi.national_general.original_index_base_2004_100 119.9) $adjudication.indec_ipi.national_general.original_index_base_2004_100 119.9
Add-Check "indec.IPI_yoy" (Close-To $adjudication.indec_ipi.national_general.year_over_year_percent 2.0) $adjudication.indec_ipi.national_general.year_over_year_percent 2.0
Add-Check "indec.IPI_ytd" (Close-To $adjudication.indec_ipi.national_general.year_to_date_percent -2.2) $adjudication.indec_ipi.national_general.year_to_date_percent -2.2
Add-Check "indec.IPI_rising_9_of_16" ($adjudication.indec_ipi.division_breadth.rising -eq 9 -and $adjudication.indec_ipi.division_breadth.total -eq 16) @($adjudication.indec_ipi.division_breadth.rising,$adjudication.indec_ipi.division_breadth.total) @(9,16)
Add-Check "indec.IPI_wood_yoy" (Close-To $adjudication.indec_ipi.wood_evidence.wood_year_over_year_percent 17.3) $adjudication.indec_ipi.wood_evidence.wood_year_over_year_percent 17.3
Add-Check "indec.IPI_abstains" ($adjudication.indec_ipi.forecast_authority -eq 'ABSTAIN_UNTIL_STRUCTURED_SERIES_OR_FUTURE_FREEZE') $adjudication.indec_ipi.forecast_authority 'ABSTAIN_UNTIL_STRUCTURED_SERIES_OR_FUTURE_FREEZE'
Add-Check "indec.UCII_general" (Close-To $adjudication.indec_ucii.general_capacity_utilization_percent 59.1) $adjudication.indec_ucii.general_capacity_utilization_percent 59.1
Add-Check "indec.UCII_observer_only" ($adjudication.indec_ucii.forecast_authority -eq 'OBSERVER_ONLY_UNTIL_SEPARATE_CAUSAL_PREREGISTRATION') $adjudication.indec_ucii.forecast_authority 'OBSERVER_ONLY_UNTIL_SEPARATE_CAUSAL_PREREGISTRATION'
Add-Check "indec.XLS_blocker_preserved" ($workbookInspection.classification -eq 'READ_ONLY_XLS_BINARY_INSPECTION_BLOCKED') $workbookInspection.classification 'READ_ONLY_XLS_BINARY_INSPECTION_BLOCKED'
Add-Check "coral.no_new_causal_score" ($adjudication.coral_adjudication.position_change -eq 'BETTER_OBSERVATIONAL_CUSTODY_BUT_NO_NEW_CAUSAL_SCORE') $adjudication.coral_adjudication.position_change 'BETTER_OBSERVATIONAL_CUSTODY_BUT_NO_NEW_CAUSAL_SCORE'
Add-Check "contract.no_global_winner" ($null -eq $contract.scientific_invariants.global_winner) $contract.scientific_invariants.global_winner $null
Add-Check "contract.no_automatic_promotion" (-not $contract.scientific_invariants.automatic_promotion) $contract.scientific_invariants.automatic_promotion $false

$failures=@($checks|Where-Object{-not $_.pass})
$audit=[ordered]@{
    schema="kch-bayesian-markets-v5-audit/v1";generated_at=(Get-Date -Format o);
    status=if($failures.Count -eq 0){"PASS"}else{"FAIL"};checks=$checks.Count;failures=$failures.Count;
    prior_v4_checks=$priorAudit.checks;prior_v4_failures=$priorAudit.failures;
    adverse_states_asserted=$contract.adverse_states;details=$checks
}
[IO.File]::WriteAllText([IO.Path]::GetFullPath((Join-Path (Get-Location) $OutputPath)),($audit|ConvertTo-Json -Depth 12),[Text.UTF8Encoding]::new($false))
$audit|ConvertTo-Json -Depth 4
if($failures.Count){exit 1}


