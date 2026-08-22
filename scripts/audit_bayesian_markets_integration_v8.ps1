param([string]$OutputPath = "governance/KCH_BAYESIAN_MARKETS_V8_AUDIT.json")
$ErrorActionPreference="Stop"
$checks=[Collections.Generic.List[object]]::new()
function Add-Check([string]$Name,[bool]$Pass,[object]$Observed,[object]$Expected){$checks.Add([pscustomobject]@{name=$Name;pass=$Pass;observed=$Observed;expected=$Expected})}
function File-Hash([string]$Path){(Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash}
if(-not(Test-Path ".artifact_probe")){New-Item -ItemType Directory ".artifact_probe"|Out-Null}
$priorPath=".artifact_probe/bma-v7-audit-$([Guid]::NewGuid().ToString('N')).json"
try{$null=& "scripts/audit_bayesian_markets_integration_v7.ps1" -OutputPath $priorPath;$prior=Get-Content -Raw $priorPath|ConvertFrom-Json;Add-Check "prior_v7.status" ($prior.status-eq"PASS") $prior.status "PASS";Add-Check "prior_v7.failures" ($prior.failures-eq 0) $prior.failures 0}finally{if(Test-Path $priorPath){Remove-Item -Force $priorPath}}
$contract=Get-Content -Raw "governance/KCH_BAYESIAN_MARKETS_EVIDENCE_CONTRACT_V8.json"|ConvertFrom-Json
$prereg=Get-Content -Raw "preregistrations/BPM_LUKE_ROUNDWOOD_MONTHLY_2020_2026_V0.1.json"|ConvertFrom-Json
$addendum=Get-Content -Raw "preregistrations/BPM_LUKE_ROUNDWOOD_MONTHLY_2020_2026_V0.1_SOFTWARE_ADDENDUM.json"|ConvertFrom-Json
Add-Check "contract.prior_hash" ((File-Hash $contract.prior_contract.path)-eq$contract.prior_contract.sha256) (File-Hash $contract.prior_contract.path) $contract.prior_contract.sha256
Add-Check "contract.mission_hash" ((File-Hash $contract.mission_register.path)-eq$contract.mission_register.sha256) (File-Hash $contract.mission_register.path) $contract.mission_register.sha256
foreach($i in $contract.new_frozen_evidence){$exists=Test-Path $i.path;Add-Check "exists.$($i.path)" $exists $exists $true;if($exists){$h=File-Hash $i.path;Add-Check "hash.$($i.path)" ($h-eq$i.sha256) $h $i.sha256}}
foreach($i in $addendum.source_anchors){$h=File-Hash $i.path;Add-Check "source_anchor.$($i.path)" ($h-eq$i.sha256) $h $i.sha256}
foreach($i in $addendum.frozen_software){$h=File-Hash $i.path;Add-Check "software_hash.$($i.path)" ($h-eq$i.sha256) $h $i.sha256}
Add-Check "prereg.status" ($prereg.status-eq"FROZEN_BEFORE_HISTORICAL_VALUE_ACQUISITION") $prereg.status "FROZEN_BEFORE_HISTORICAL_VALUE_ACQUISITION"
Add-Check "addendum.status" ($addendum.status-eq"FROZEN_BEFORE_HISTORICAL_VALUE_ACQUISITION") $addendum.status "FROZEN_BEFORE_HISTORICAL_VALUE_ACQUISITION"
Add-Check "acquisition.one_post" ($prereg.bounded_acquisition.remote_data_posts-eq1) $prereg.bounded_acquisition.remote_data_posts 1
Add-Check "acquisition.no_get" ($prereg.bounded_acquisition.remote_metadata_gets-eq0) $prereg.bounded_acquisition.remote_metadata_gets 0
Add-Check "acquisition.cells" ($prereg.bounded_acquisition.maximum_cells-eq158) $prereg.bounded_acquisition.maximum_cells 158
Add-Check "sequence.transitions" ($prereg.sequence.retrospective_transition_count-eq78) $prereg.sequence.retrospective_transition_count 78
Add-Check "sequence.no_posterior_reset" (-not$prereg.sequence.posterior_reset_at_year_boundary) $prereg.sequence.posterior_reset_at_year_boundary $false
Add-Check "sequence.no_Z_post_reset" (-not$prereg.sequence.Z_post_reset_at_year_boundary) $prereg.sequence.Z_post_reset_at_year_boundary $false
Add-Check "sequence.future_unopened" (-not$prereg.sequence.future_target_present_in_capture) $prereg.sequence.future_target_present_in_capture $false
Add-Check "evaluation.no_historical_causal_authority" (-not$prereg.evaluation.historical_first_release_causal_score_authority) $prereg.evaluation.historical_first_release_causal_score_authority $false
Add-Check "evaluation.preopened_excluded" (-not$prereg.evaluation.'2026_07_score_authority') $prereg.evaluation.'2026_07_score_authority' $false
Add-Check "evaluation.no_global_winner" ($null-eq$prereg.evaluation.global_winner) $prereg.evaluation.global_winner $null
Add-Check "tests.focused" ($addendum.pre_freeze_validation.focused_pytest-eq"12 passed") $addendum.pre_freeze_validation.focused_pytest "12 passed"
Add-Check "tests.no_remote" (-not$addendum.pre_freeze_validation.remote_access_during_validation) $addendum.pre_freeze_validation.remote_access_during_validation $false
Add-Check "capture.absent_before_audit" (-not(Test-Path "evidence/runs/bpm-luke-roundwood-monthly-v0.1-history-capture")) (Test-Path "evidence/runs/bpm-luke-roundwood-monthly-v0.1-history-capture") $false
Add-Check "run.absent_before_audit" (-not(Test-Path "evidence/runs/bpm-luke-roundwood-monthly-v0.1-causal")) (Test-Path "evidence/runs/bpm-luke-roundwood-monthly-v0.1-causal") $false
$fail=@($checks|Where-Object{-not$_.pass});$audit=[ordered]@{schema="kch-bayesian-markets-v8-audit/v1";generated_at=(Get-Date -Format o);status=if($fail.Count){"FAIL"}else{"PASS"};checks=$checks.Count;failures=$fail.Count;prior_v7_checks=$prior.checks;prior_v7_failures=$prior.failures;adverse_states_asserted=$contract.adverse_states;details=$checks}
[IO.File]::WriteAllText([IO.Path]::GetFullPath((Join-Path (Get-Location)$OutputPath)),($audit|ConvertTo-Json -Depth 12),[Text.UTF8Encoding]::new($false));$audit|ConvertTo-Json -Depth 3;if($fail.Count){exit 1}
