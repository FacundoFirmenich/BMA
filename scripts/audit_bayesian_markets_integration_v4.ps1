param(
    [string]$OutputPath = "governance/KCH_BAYESIAN_MARKETS_V4_AUDIT.json"
)

$ErrorActionPreference = "Stop"
$checks = [Collections.Generic.List[object]]::new()
function Add-Check([string]$Name, [bool]$Pass, [object]$Observed, [object]$Expected) {
    $checks.Add([pscustomobject]@{name=$Name;pass=$Pass;observed=$Observed;expected=$Expected})
}
function File-Hash([string]$Path) { return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash }
function Close-To([double]$Left,[double]$Right,[double]$Tolerance=1e-10){return [Math]::Abs($Left-$Right) -le $Tolerance}

$priorAuditPath=".artifact_probe/bma-v3-audit-$([Guid]::NewGuid().ToString('N')).json"
try {
    $null=& "scripts/audit_bayesian_markets_integration_v3.ps1" -OutputPath $priorAuditPath
    $priorAudit=Get-Content -Raw -LiteralPath $priorAuditPath|ConvertFrom-Json
    Add-Check "prior_v3.audit_status" ($priorAudit.status -eq "PASS") $priorAudit.status "PASS"
    Add-Check "prior_v3.audit_failures" ($priorAudit.failures -eq 0) $priorAudit.failures 0
} finally {
    if(Test-Path -LiteralPath $priorAuditPath){Remove-Item -LiteralPath $priorAuditPath -Force}
}

$contract=Get-Content -Raw -LiteralPath "governance/KCH_BAYESIAN_MARKETS_EVIDENCE_CONTRACT_V4.json"|ConvertFrom-Json
$receipt=Get-Content -Raw -LiteralPath "governance/KCH_BAYESIAN_MARKETS_INTEGRATION_RECEIPT_V4.json"|ConvertFrom-Json
Add-Check "contract.prior_hash" ((File-Hash $contract.prior_contract.path) -eq $contract.prior_contract.sha256) (File-Hash $contract.prior_contract.path) $contract.prior_contract.sha256
Add-Check "contract.mission_hash" ((File-Hash $contract.mission_register.path) -eq $contract.mission_register.sha256) (File-Hash $contract.mission_register.path) $contract.mission_register.sha256
foreach($item in $contract.new_frozen_evidence){
    $exists=Test-Path -LiteralPath $item.path
    Add-Check "contract.exists.$($item.path)" $exists $exists $true
    if($exists){$actual=File-Hash $item.path;Add-Check "contract.hash.$($item.path)" ($actual -eq $item.sha256) $actual $item.sha256}
}
$contractHash=File-Hash $receipt.evidence_contract.path
Add-Check "receipt.contract_hash" ($contractHash -eq $receipt.evidence_contract.sha256) $contractHash $receipt.evidence_contract.sha256

$prereg=Get-Content -Raw -LiteralPath "preregistrations/HBP_EUROSTAT_STS_ES_C_2026_07_FREEZE_V0.1.json"|ConvertFrom-Json
$runRoot="evidence/runs/hbp-eurostat-sts-es-c-v0.1-2026-07-freeze"
$headers=Get-Content -Raw -LiteralPath "$runRoot/response_headers.json"|ConvertFrom-Json
$series=Get-Content -Raw -LiteralPath "$runRoot/normalized_training_series.json"|ConvertFrom-Json
$zpost=Get-Content -Raw -LiteralPath "$runRoot/posterior_z_post.json"|ConvertFrom-Json
$freeze=Get-Content -Raw -LiteralPath "$runRoot/forecast_freeze.json"|ConvertFrom-Json
$manifest=Get-Content -Raw -LiteralPath "$runRoot/manifest.json"|ConvertFrom-Json
$raw=Get-Content -Raw -LiteralPath "$runRoot/eurostat_sts_es_c_through_2026_06.json"|ConvertFrom-Json

Add-Check "sts.prereg_status" ($prereg.status -eq "FROZEN_PRE_OUTCOME_DATA_CAPTURE_AND_EXECUTION_AUTHORIZED") $prereg.status "FROZEN_PRE_OUTCOME_DATA_CAPTURE_AND_EXECUTION_AUTHORIZED"
Add-Check "sts.target" ($prereg.temporal_contract.target_month -eq "2026-07") $prereg.temporal_contract.target_month "2026-07"
Add-Check "sts.training_end" ($prereg.temporal_contract.training_end -eq "2026-06") $prereg.temporal_contract.training_end "2026-06"
Add-Check "sts.raw_hash_headers" ((File-Hash "$runRoot/eurostat_sts_es_c_through_2026_06.json") -eq $headers.raw_sha256) (File-Hash "$runRoot/eurostat_sts_es_c_through_2026_06.json") $headers.raw_sha256
Add-Check "sts.source_updated" ($freeze.source_updated -eq "2026-08-19T11:00:00+0200") $freeze.source_updated "2026-08-19T11:00:00+0200"
Add-Check "sts.record_count" ($series.record_count -eq 138) $series.record_count 138
Add-Check "sts.transition_count" ($series.transition_count -eq 137) $series.transition_count 137
Add-Check "sts.first_month" ($series.records[0].time -eq "2015-01") $series.records[0].time "2015-01"
Add-Check "sts.last_month" ($series.records[-1].time -eq "2026-06") $series.records[-1].time "2026-06"
Add-Check "sts.all_provisional" ($series.status_counts.p -eq 138) $series.status_counts.p 138
Add-Check "sts.target_absent_normalized" (@($series.records|Where-Object time -eq "2026-07").Count -eq 0) @($series.records|Where-Object time -eq "2026-07").Count 0
$rawTimes=@($raw.dimension.time.category.index.PSObject.Properties.Name)
Add-Check "sts.target_absent_raw_dimension" ($rawTimes -notcontains "2026-07") ($rawTimes -contains "2026-07") $false
Add-Check "sts.raw_last_time" ($rawTimes[-1] -eq "2026-06") $rawTimes[-1] "2026-06"

Add-Check "sts.zpost_observations" ($zpost.observation_count -eq 138) $zpost.observation_count 138
Add-Check "sts.zpost_transitions" ($zpost.transition_count -eq 137) $zpost.transition_count 137
Add-Check "sts.no_reset" (-not $zpost.reset_occurred) $zpost.reset_occurred $false
Add-Check "sts.no_pooling" (-not $zpost.pooling_occurred) $zpost.pooling_occurred $false
Add-Check "sts.zpost_not_residual" (-not $zpost.Z_post_is_residual_z) $zpost.Z_post_is_residual_z $false
Add-Check "sts.zpost_not_zxpl" (-not $zpost.Z_post_is_Z_XPL) $zpost.Z_post_is_Z_XPL $false
Add-Check "sts.prereg_hash_zpost" ((File-Hash "preregistrations/HBP_EUROSTAT_STS_ES_C_2026_07_FREEZE_V0.1.json") -eq $zpost.preregistration_sha256) (File-Hash "preregistrations/HBP_EUROSTAT_STS_ES_C_2026_07_FREEZE_V0.1.json") $zpost.preregistration_sha256
Add-Check "sts.zpost_hash_freeze" ((File-Hash "$runRoot/posterior_z_post.json") -eq $freeze.posterior_z_post_sha256) (File-Hash "$runRoot/posterior_z_post.json") $freeze.posterior_z_post_sha256

Add-Check "sts.freeze_state" ($freeze.status -eq "FROZEN_PRE_OUTCOME") $freeze.status "FROZEN_PRE_OUTCOME"
Add-Check "sts.outcome_not_opened" (-not $freeze.outcome_opened) $freeze.outcome_opened $false
Add-Check "sts.target_not_requested" (-not $freeze.target_requested_from_source) $freeze.target_requested_from_source $false
Add-Check "sts.M0_point" (Close-To $freeze.models.M0.point_median_index $contract.model_state.M0_point_median_index) $freeze.models.M0.point_median_index $contract.model_state.M0_point_median_index
Add-Check "sts.M1_point" (Close-To $freeze.models.M1.point_median_index $contract.model_state.M1_point_median_index) $freeze.models.M1.point_median_index $contract.model_state.M1_point_median_index
Add-Check "sts.M0_interval_order" ($freeze.models.M0.lower_90_index -lt $freeze.models.M0.point_median_index -and $freeze.models.M0.point_median_index -lt $freeze.models.M0.upper_90_index) @($freeze.models.M0.lower_90_index,$freeze.models.M0.point_median_index,$freeze.models.M0.upper_90_index) "strictly increasing"
Add-Check "sts.M1_interval_order" ($freeze.models.M1.lower_90_index -lt $freeze.models.M1.point_median_index -and $freeze.models.M1.point_median_index -lt $freeze.models.M1.upper_90_index) @($freeze.models.M1.lower_90_index,$freeze.models.M1.point_median_index,$freeze.models.M1.upper_90_index) "strictly increasing"
Add-Check "sts.M2_port_abstains" ($freeze.models.M2_port.state -eq "ABSTAIN_NO_CAUSALLY_ALIGNED_OBSERVER_PANEL") $freeze.models.M2_port.state "ABSTAIN_NO_CAUSALLY_ALIGNED_OBSERVER_PANEL"
Add-Check "sts.M2_ted_abstains" ($freeze.models.M2_ted.state -eq "ABSTAIN_NO_CAUSALLY_ALIGNED_OBSERVER_PANEL") $freeze.models.M2_ted.state "ABSTAIN_NO_CAUSALLY_ALIGNED_OBSERVER_PANEL"
Add-Check "sts.M3_coral_abstains" ($freeze.models.M3_coral.state -eq "ABSTAIN_UNTIL_BOTH_NESTED_OBSERVER_PARENTS_ARE_ESTIMABLE") $freeze.models.M3_coral.state "ABSTAIN_UNTIL_BOTH_NESTED_OBSERVER_PARENTS_ARE_ESTIMABLE"
Add-Check "sts.equal_weight_M0" (Close-To $freeze.weights.M0 0.5) $freeze.weights.M0 0.5
Add-Check "sts.equal_weight_M1" (Close-To $freeze.weights.M1 0.5) $freeze.weights.M1 0.5
Add-Check "sts.no_global_winner" ($null -eq $freeze.global_winner) $freeze.global_winner $null
Add-Check "sts.no_promotion" (-not $freeze.automatic_promotion) $freeze.automatic_promotion $false

foreach($item in $manifest.files){
    $actual=File-Hash $item.path
    Add-Check "manifest.hash.$($item.path)" ($actual -eq $item.sha256) $actual $item.sha256
}
Add-Check "vintage.B-D_no_authority" (-not $contract.vintage_adjudication.ei_is_m_vtg_campaign_authority) $contract.vintage_adjudication.ei_is_m_vtg_campaign_authority $false
Add-Check "contract.no_automatic_promotion" (-not $contract.scientific_invariants.automatic_promotion) $contract.scientific_invariants.automatic_promotion $false

$failures=@($checks|Where-Object{-not $_.pass})
$audit=[ordered]@{
    schema="kch-bayesian-markets-v4-audit/v1";generated_at=(Get-Date -Format o);
    status=if($failures.Count -eq 0){"PASS"}else{"FAIL"};checks=$checks.Count;failures=$failures.Count;
    prior_v3_checks=$priorAudit.checks;prior_v3_failures=$priorAudit.failures;
    adverse_states_asserted=$contract.adverse_states;details=$checks
}
[IO.File]::WriteAllText([IO.Path]::GetFullPath((Join-Path (Get-Location) $OutputPath)),($audit|ConvertTo-Json -Depth 12),[Text.UTF8Encoding]::new($false))
$audit|ConvertTo-Json -Depth 4
if($failures.Count){exit 1}

