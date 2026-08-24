param(
    [string]$OutputPath = "governance/KCH_BAYESIAN_MARKETS_V3_AUDIT.json"
)

$ErrorActionPreference = "Stop"
$checks = [Collections.Generic.List[object]]::new()
function Add-Check([string]$Name, [bool]$Pass, [object]$Observed, [object]$Expected) {
    $checks.Add([pscustomobject]@{name=$Name;pass=$Pass;observed=$Observed;expected=$Expected})
}
function File-Hash([string]$Path) { return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash }

$contract=Get-Content -Raw -LiteralPath "governance/KCH_BAYESIAN_MARKETS_EVIDENCE_CONTRACT_V3.json"|ConvertFrom-Json
$receipt=Get-Content -Raw -LiteralPath "governance/KCH_BAYESIAN_MARKETS_INTEGRATION_RECEIPT_V3.json"|ConvertFrom-Json
foreach($item in $contract.frozen_evidence){
    $exists=Test-Path -LiteralPath $item.path
    Add-Check "contract.exists.$($item.path)" $exists $exists $true
    if($exists){$actual=File-Hash $item.path;Add-Check "contract.hash.$($item.path)" ($actual -eq $item.sha256) $actual $item.sha256}
}
$missionHash=File-Hash $contract.mission_register.path
Add-Check "contract.mission_hash" ($missionHash -eq $contract.mission_register.sha256) $missionHash $contract.mission_register.sha256
$contractHash=File-Hash $receipt.evidence_contract.path
Add-Check "receipt.contract_hash" ($contractHash -eq $receipt.evidence_contract.sha256) $contractHash $receipt.evidence_contract.sha256

$index=Import-Csv -LiteralPath "canonical/CLASSIFICATION_INDEX_V7.csv"
Add-Check "index.rows" ($index.Count -eq 31) $index.Count 31
Add-Check "index.bpm" (@($index|Where-Object canonical_family -eq "BPM").Count -eq 11) @($index|Where-Object canonical_family -eq "BPM").Count 11
Add-Check "index.bum" (@($index|Where-Object canonical_family -eq "BUM").Count -eq 1) @($index|Where-Object canonical_family -eq "BUM").Count 1
Add-Check "index.hbp" (@($index|Where-Object canonical_family -eq "HBP").Count -eq 15) @($index|Where-Object canonical_family -eq "HBP").Count 15
Add-Check "index.unclassified" (@($index|Where-Object canonical_family -eq "UNCLASSIFIED_PENDING_CONTENT_REVIEW").Count -eq 4) @($index|Where-Object canonical_family -eq "UNCLASSIFIED_PENDING_CONTENT_REVIEW").Count 4
foreach($id in @("bpm-rmk-estonia-timber","bpm-spain-port-activity-observer","hbp-eurostat-sts-industrial-production","hbp-eurostat-prodcom-product-support","hbp-eu-ted-institutional-demand-observer")){
    Add-Check "index.unit.$id" (@($index|Where-Object canonical_unit_id -eq $id).Count -eq 1) @($index|Where-Object canonical_unit_id -eq $id).Count 1
}

$eventRoot="evidence/runs/bpm-rmk-timber-v0.1-2025-causal/events"
$audits=@(Get-ChildItem -LiteralPath $eventRoot -Recurse -Filter AUDIT.json|ForEach-Object{Get-Content -Raw $_.FullName|ConvertFrom-Json})
Add-Check "rmk.audited_events" ($audits.Count -eq 14) $audits.Count 14
Add-Check "rmk.audits_pass" (@($audits|Where-Object status -ne "PASS").Count -eq 0) @($audits|Where-Object status -ne "PASS").Count 0
$auditChecks=($audits|Measure-Object checks -Sum).Sum
Add-Check "rmk.audit_checks" ($auditChecks -eq 646) $auditChecks 646
$posterior=Get-Content -Raw -LiteralPath "$eventRoot/2026-05-28/closure/prior_after_2026-05-28.json"|ConvertFrom-Json
$z=Get-Content -Raw -LiteralPath "$eventRoot/2026-05-28/closure/z_post_2026-05-28.json"|ConvertFrom-Json
Add-Check "rmk.posterior_cells" ($posterior.local_cell_count -eq 388) $posterior.local_cell_count 388
Add-Check "rmk.posterior_observations" ($posterior.posterior_observation_count -eq 1008) $posterior.posterior_observation_count 1008
$m1=@($z.cells.PSObject.Properties.Value|Where-Object{$_.price.M1.state -eq "ESTIMABLE"}).Count
$m2=@($z.cells.PSObject.Properties.Value|Where-Object{$_.price.M2.state -eq "ESTIMABLE_FOR_LISTED_PHASES"}).Count
Add-Check "rmk.M1_cells" ($m1 -eq 30) $m1 30
Add-Check "rmk.M2_cells" ($m2 -eq 0) $m2 0
Add-Check "rmk.no_reset" (-not $posterior.reset_occurred) $posterior.reset_occurred $false
Add-Check "rmk.no_pooling" (-not $posterior.pooling_occurred) $posterior.pooling_occurred $false
$april=Get-Content -Raw -LiteralPath "$eventRoot/2026-04-28/closure/NOT_ESTIMABLE_NO_FROZEN_OFFER.json"|ConvertFrom-Json
$june=Get-Content -Raw -LiteralPath "$eventRoot/2026-06-30/closure/NOT_ESTIMABLE_SCHEMA_PROBE_PREEXPOSURE.json"|ConvertFrom-Json
$future=Get-Content -Raw -LiteralPath "$eventRoot/2026-08-26/gates/FUTURE_EVENT_NOT_OCCURRED_20260821.json"|ConvertFrom-Json
Add-Check "rmk.april_not_estimable" ($april.state -eq "NOT_ESTIMABLE_NO_FROZEN_OFFER") $april.state "NOT_ESTIMABLE_NO_FROZEN_OFFER"
Add-Check "rmk.june_preexposed" ($june.state -eq "NOT_ESTIMABLE_SCHEMA_PROBE_PREEXPOSURE") $june.state "NOT_ESTIMABLE_SCHEMA_PROBE_PREEXPOSURE"
Add-Check "rmk.future_closed" ($future.state -eq "FUTURE_EVENT_NOT_OCCURRED_BODY_CLOSED") $future.state "FUTURE_EVENT_NOT_OCCURRED_BODY_CLOSED"

$ledger=Import-Csv -LiteralPath "governance/HBP_ARGENTINA_EUROSTAT_CAMPAIGN_LEDGER_V1.csv"
Add-Check "hbp.ledger_rows" ($ledger.Count -eq 6) $ledger.Count 6
Add-Check "hbp.ucii_legacy" (@($ledger|Where-Object scientific_state -match "LEGACY").Count -eq 1) @($ledger|Where-Object scientific_state -match "LEGACY").Count 1
Add-Check "hbp.eurostat_not_estimable" (@($ledger|Where-Object scientific_state -match "NOT_ESTIMABLE").Count -eq 1) @($ledger|Where-Object scientific_state -match "NOT_ESTIMABLE").Count 1

$screen=Import-Csv -LiteralPath "governance/BPM_HBP_PUBLIC_EXPANSION_SOURCE_SCREEN_V2.csv"
Add-Check "screen.rows" ($screen.Count -eq 8) $screen.Count 8
Add-Check "screen.indec" (@($screen|Where-Object source_id -eq "indec-argentina-ipi-ucii").Count -eq 1) @($screen|Where-Object source_id -eq "indec-argentina-ipi-ucii").Count 1
Add-Check "screen.prodcom" (@($screen|Where-Object source_id -eq "eurostat-prodcom-product-production").Count -eq 1) @($screen|Where-Object source_id -eq "eurostat-prodcom-product-production").Count 1
Add-Check "screen.comtrade_quarantine" (@($screen|Where-Object screen_decision -eq "QUARANTINE_NO_MODEL_AUTHORITY").Count -eq 1) @($screen|Where-Object screen_decision -eq "QUARANTINE_NO_MODEL_AUTHORITY").Count 1

$coral=Get-Content -Raw -LiteralPath "governance/BAYME_CROSS_FAMILY_CORAL_INTEGRATION_CONTRACT_V1.json"|ConvertFrom-Json
Add-Check "coral.no_posterior_transfer" (@($coral.typed_edges|Where-Object posterior_transfer -ne $false).Count -eq 0) @($coral.typed_edges|Where-Object posterior_transfer -ne $false).Count 0
Add-Check "coral.no_global_winner" ($null -eq $coral.hard_invariants.aggregate_winner) $coral.hard_invariants.aggregate_winner $null
Add-Check "coral.no_promotion" (-not $coral.hard_invariants.automatic_promotion) $coral.hard_invariants.automatic_promotion $false
$pre=Get-Content -Raw -LiteralPath "preregistrations/BAYME_INDUSTRIAL_CORAL_PROGRAM_V0.2.json"|ConvertFrom-Json
Add-Check "prereg.not_started" ($pre.status -eq "FROZEN_DESIGN_NEW_DATA_ACQUISITION_NOT_STARTED") $pre.status "FROZEN_DESIGN_NEW_DATA_ACQUISITION_NOT_STARTED"
Add-Check "receipt.custody_gap" (-not $receipt.custody.argentina_eurostat_exact_payload_recovery_complete) $receipt.custody.argentina_eurostat_exact_payload_recovery_complete $false
Add-Check "contract.no_automatic_promotion" (-not $contract.scientific_invariants.automatic_promotion) $contract.scientific_invariants.automatic_promotion $false

$failures=@($checks|Where-Object{-not $_.pass})
$audit=[ordered]@{
    schema="kch-bayesian-markets-v3-audit/v1";generated_at=(Get-Date -Format o);
    status=if($failures.Count -eq 0){"PASS"}else{"FAIL"};checks=$checks.Count;failures=$failures.Count;
    adverse_states_asserted=$contract.adverse_states;details=$checks
}
[IO.File]::WriteAllText([IO.Path]::GetFullPath((Join-Path (Get-Location) $OutputPath)),($audit|ConvertTo-Json -Depth 12),[Text.UTF8Encoding]::new($false))
$audit|ConvertTo-Json -Depth 4
if($failures.Count){exit 1}
