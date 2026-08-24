param(
    [string]$OutputPath = "governance/KCH_BAYESIAN_MARKETS_V6_AUDIT.json"
)

$ErrorActionPreference = "Stop"
$checks = [Collections.Generic.List[object]]::new()
function Add-Check([string]$Name, [bool]$Pass, [object]$Observed, [object]$Expected) {
    $checks.Add([pscustomobject]@{name=$Name;pass=$Pass;observed=$Observed;expected=$Expected})
}
function File-Hash([string]$Path) { return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash }
function Close-To([double]$Left,[double]$Right,[double]$Tolerance=1e-9){return [Math]::Abs($Left-$Right) -le $Tolerance}

if(-not(Test-Path -LiteralPath ".artifact_probe")){New-Item -ItemType Directory -Path ".artifact_probe"|Out-Null}
$priorAuditPath=".artifact_probe/bma-v5-audit-$([Guid]::NewGuid().ToString('N')).json"
try {
    $null=& "scripts/audit_bayesian_markets_integration_v5.ps1" -OutputPath $priorAuditPath
    $priorAudit=Get-Content -Raw -LiteralPath $priorAuditPath|ConvertFrom-Json
    Add-Check "prior_v5.audit_status" ($priorAudit.status -eq "PASS") $priorAudit.status "PASS"
    Add-Check "prior_v5.audit_failures" ($priorAudit.failures -eq 0) $priorAudit.failures 0
} finally {
    if(Test-Path -LiteralPath $priorAuditPath){Remove-Item -LiteralPath $priorAuditPath -Force}
}

$contract=Get-Content -Raw -LiteralPath "governance/KCH_BAYESIAN_MARKETS_EVIDENCE_CONTRACT_V6.json"|ConvertFrom-Json
$receipt=Get-Content -Raw -LiteralPath "governance/KCH_BAYESIAN_MARKETS_INTEGRATION_RECEIPT_V6.json"|ConvertFrom-Json
$prereg=Get-Content -Raw -LiteralPath "preregistrations/HBP_PORT_TED_PROSPECTIVE_OBSERVER_CHAIN_V0.1.json"|ConvertFrom-Json
$adjudication=Get-Content -Raw -LiteralPath "evidence/runs/hbp-port-ted-prospective-observer-chain-v0.1/observer_adjudication.json"|ConvertFrom-Json

Add-Check "contract.prior_hash" ((File-Hash $contract.prior_contract.path) -eq $contract.prior_contract.sha256) (File-Hash $contract.prior_contract.path) $contract.prior_contract.sha256
Add-Check "contract.mission_hash" ((File-Hash $contract.mission_register.path) -eq $contract.mission_register.sha256) (File-Hash $contract.mission_register.path) $contract.mission_register.sha256
foreach($item in $contract.new_frozen_evidence){
    $exists=Test-Path -LiteralPath $item.path
    Add-Check "contract.exists.$($item.path)" $exists $exists $true
    if($exists){$actual=File-Hash $item.path;Add-Check "contract.hash.$($item.path)" ($actual -eq $item.sha256) $actual $item.sha256}
}
foreach($item in $contract.anchor_evidence){
    $exists=Test-Path -LiteralPath $item.path
    Add-Check "anchor.exists.$($item.path)" $exists $exists $true
    if($exists){$actual=File-Hash $item.path;Add-Check "anchor.hash.$($item.path)" ($actual -eq $item.sha256) $actual $item.sha256}
}
$contractHash=File-Hash $receipt.evidence_contract.path
Add-Check "receipt.contract_hash" ($contractHash -eq $receipt.evidence_contract.sha256) $contractHash $receipt.evidence_contract.sha256

Add-Check "prereg.before_future_acquisition" ($prereg.status -eq "PREREGISTERED_BEFORE_ANY_FUTURE_RELEASE_ACQUISITION") $prereg.status "PREREGISTERED_BEFORE_ANY_FUTURE_RELEASE_ACQUISITION"
Add-Check "prereg.hash_in_adjudication" ((File-Hash "preregistrations/HBP_PORT_TED_PROSPECTIVE_OBSERVER_CHAIN_V0.1.json") -eq $adjudication.preregistration.sha256) (File-Hash "preregistrations/HBP_PORT_TED_PROSPECTIVE_OBSERVER_CHAIN_V0.1.json") $adjudication.preregistration.sha256
Add-Check "prereg.puertos_12_pairs" ($prereg.puertos_chain.model_candidacy_gate.minimum_prospectively_paired_months -eq 12) $prereg.puertos_chain.model_candidacy_gate.minimum_prospectively_paired_months 12
Add-Check "prereg.ted_12_pairs" ($prereg.ted_chain.model_candidacy_gate.minimum_prospectively_paired_months -eq 12) $prereg.ted_chain.model_candidacy_gate.minimum_prospectively_paired_months 12
Add-Check "prereg.no_auto_M2_M3" (-not $prereg.coral_rule.automatic_M2_or_M3_entry) $prereg.coral_rule.automatic_M2_or_M3_entry $false
Add-Check "prereg.no_pooling" (-not $prereg.coral_rule.cross_source_pooling) $prereg.coral_rule.cross_source_pooling $false

Add-Check "execution.existing_bytes_only" ($adjudication.classification -eq "EXISTING_BYTES_ONLY_NO_NEW_REMOTE_ACQUISITION") $adjudication.classification "EXISTING_BYTES_ONLY_NO_NEW_REMOTE_ACQUISITION"
foreach($field in @("fit_performed","forecast_performed","score_performed","posterior_updated","Z_post_updated","historical_freeze_reconstructed","cross_source_likelihood_pooling","automatic_promotion")){
    Add-Check "execution.$field" (-not $adjudication.invariants.$field) $adjudication.invariants.$field $false
}
Add-Check "execution.no_global_winner" ($null -eq $adjudication.invariants.global_winner) $adjudication.invariants.global_winner $null

Add-Check "puertos.sheets_45" ($adjudication.puertos.workbook.sheet_count -eq 45) $adjudication.puertos.workbook.sheet_count 45
Add-Check "puertos.total_june_2026" (Close-To $adjudication.puertos.national_physical_activity.total_traffic.june_2026_tonnes 47026235.533) $adjudication.puertos.national_physical_activity.total_traffic.june_2026_tonnes 47026235.533
Add-Check "puertos.general_cargo_june_2026" (Close-To $adjudication.puertos.national_physical_activity.general_cargo.june_2026_tonnes 24462278) $adjudication.puertos.national_physical_activity.general_cargo.june_2026_tonnes 24462278
Add-Check "puertos.wood_solid_ytd" (Close-To $adjudication.puertos.selected_non_energy_natures.wood_and_cork.solid_bulk.january_to_june_2026_tonnes 163148) $adjudication.puertos.selected_non_energy_natures.wood_and_cork.solid_bulk.january_to_june_2026_tonnes 163148
Add-Check "puertos.wood_general_ytd" (Close-To $adjudication.puertos.selected_non_energy_natures.wood_and_cork.general_cargo.january_to_june_2026_tonnes 2839117) $adjudication.puertos.selected_non_energy_natures.wood_and_cork.general_cargo.january_to_june_2026_tonnes 2839117
Add-Check "puertos.historic_years" (($adjudication.puertos.historic_monthly_presentation_schema.years_exposed -join ',') -eq '2019,2020,2021,2022') ($adjudication.puertos.historic_monthly_presentation_schema.years_exposed -join ',') '2019,2020,2021,2022'
Add-Check "puertos.no_current_monthly_nature" (-not $adjudication.puertos.historic_monthly_presentation_schema.current_2026_monthly_by_nature_exposed) $adjudication.puertos.historic_monthly_presentation_schema.current_2026_monthly_by_nature_exposed $false
Add-Check "puertos.nature_not_estimable" ($adjudication.puertos.nature_monthly_status -eq "NOT_ESTIMABLE_NO_CURRENT_MONTHLY_NATURE_CELL") $adjudication.puertos.nature_monthly_status "NOT_ESTIMABLE_NO_CURRENT_MONTHLY_NATURE_CELL"
Add-Check "puertos.revision_mixed_forbidden" ($adjudication.puertos.cumulative_difference_status -eq "FORBIDDEN_REVISION_MIXED_INCREMENT_UNLESS_SEPARATELY_RECONCILED") $adjudication.puertos.cumulative_difference_status "FORBIDDEN_REVISION_MIXED_INCREMENT_UNLESS_SEPARATELY_RECONCILED"

Add-Check "ted.total_3132" ($adjudication.ted.response.reported_total_notice_count -eq 3132) $adjudication.ted.response.reported_total_notice_count 3132
Add-Check "ted.sample_10" ($adjudication.ted.response.sampled_notices -eq 10) $adjudication.ted.response.sampled_notices 10
Add-Check "ted.unique_10" ($adjudication.ted.response.unique_publication_numbers -eq 10) $adjudication.ted.response.unique_publication_numbers 10
foreach($field in @("publication_number","publication_date","notice_type","cpv","place")){
    Add-Check "ted.coverage.$field" ($adjudication.ted.response.field_coverage.$field -eq 10) $adjudication.ted.response.field_coverage.$field 10
}
Add-Check "ted.value_4" ($adjudication.ted.response.field_coverage.award_value -eq 4) $adjudication.ted.response.field_coverage.award_value 4
Add-Check "ted.currency_5" ($adjudication.ted.response.field_coverage.currency -eq 5) $adjudication.ted.response.field_coverage.currency 5
Add-Check "ted.quantity_0" ($adjudication.ted.response.field_coverage.quantity_fields -eq 0) $adjudication.ted.response.field_coverage.quantity_fields 0
Add-Check "ted.event_only" ($adjudication.ted.authority -eq "INSTITUTIONAL_DEMAND_EVENT_COUNT_OBSERVER_ONLY") $adjudication.ted.authority "INSTITUTIONAL_DEMAND_EVENT_COUNT_OBSERVER_ONLY"

Add-Check "coral.position" ($adjudication.coral_adjudication.position_change -eq "BETTER_TYPED_OBSERVER_DESIGN_WITHOUT_NEW_PREDICTIVE_AUTHORITY") $adjudication.coral_adjudication.position_change "BETTER_TYPED_OBSERVER_DESIGN_WITHOUT_NEW_PREDICTIVE_AUTHORITY"
Add-Check "coral.M2_abstains" ($adjudication.coral_adjudication.M2_status -eq "ABSTAIN_UNTIL_TARGET_SPECIFIC_FREEZE_AND_SUPPORT_GATE") $adjudication.coral_adjudication.M2_status "ABSTAIN_UNTIL_TARGET_SPECIFIC_FREEZE_AND_SUPPORT_GATE"
Add-Check "coral.M3_abstains" ($adjudication.coral_adjudication.M3_status -eq "ABSTAIN_NO_CAUSALLY_ALIGNED_MULTI_SOURCE_LIKELIHOOD") $adjudication.coral_adjudication.M3_status "ABSTAIN_NO_CAUSALLY_ALIGNED_MULTI_SOURCE_LIKELIHOOD"

$failures=@($checks|Where-Object{-not $_.pass})
$audit=[ordered]@{
    schema="kch-bayesian-markets-v6-audit/v1";generated_at=(Get-Date -Format o);
    status=if($failures.Count -eq 0){"PASS"}else{"FAIL"};checks=$checks.Count;failures=$failures.Count;
    prior_v5_checks=$priorAudit.checks;prior_v5_failures=$priorAudit.failures;
    adverse_states_asserted=$contract.adverse_states;details=$checks
}
[IO.File]::WriteAllText([IO.Path]::GetFullPath((Join-Path (Get-Location) $OutputPath)),($audit|ConvertTo-Json -Depth 12),[Text.UTF8Encoding]::new($false))
$audit|ConvertTo-Json -Depth 4
if($failures.Count){exit 1}
