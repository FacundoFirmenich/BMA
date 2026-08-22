param([string]$OutputPath = "governance/KCH_BAYESIAN_MARKETS_V9_AUDIT.json")
$ErrorActionPreference="Stop"
$checks=[Collections.Generic.List[object]]::new()
function Add-Check([string]$Name,[bool]$Pass,[object]$Observed,[object]$Expected){$checks.Add([pscustomobject]@{name=$Name;pass=$Pass;observed=$Observed;expected=$Expected})}
function File-Hash([string]$Path){(Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash}
function Close-To([double]$A,[double]$B,[double]$T=1e-10){[Math]::Abs($A-$B)-le$T}
$contract=Get-Content -Raw "governance/KCH_BAYESIAN_MARKETS_EVIDENCE_CONTRACT_V9.json"|ConvertFrom-Json
$v8=Get-Content -Raw "governance/KCH_BAYESIAN_MARKETS_V8_AUDIT.json"|ConvertFrom-Json
Add-Check "prior_v8.audit_hash" ((File-Hash "governance/KCH_BAYESIAN_MARKETS_V8_AUDIT.json")-eq"F0D6899B44668518E72AEDA6D6D16E4343CFD40C9DFFA87ABA8FBAB1022564FC") (File-Hash "governance/KCH_BAYESIAN_MARKETS_V8_AUDIT.json") "F0D6899B44668518E72AEDA6D6D16E4343CFD40C9DFFA87ABA8FBAB1022564FC"
Add-Check "prior_v8.status" ($v8.status-eq"PASS") $v8.status "PASS"
Add-Check "prior_v8.checks" (($v8.checks-eq48)-and($v8.failures-eq0)) "$($v8.checks)/$($v8.failures)" "48/0"
Add-Check "contract.prior_hash" ((File-Hash $contract.prior_contract.path)-eq$contract.prior_contract.sha256) (File-Hash $contract.prior_contract.path) $contract.prior_contract.sha256
Add-Check "contract.mission_hash" ((File-Hash $contract.mission_register.path)-eq$contract.mission_register.sha256) (File-Hash $contract.mission_register.path) $contract.mission_register.sha256
foreach($i in $contract.new_frozen_evidence){$exists=Test-Path $i.path;Add-Check "exists.$($i.path)" $exists $exists $true;if($exists){$h=File-Hash $i.path;Add-Check "hash.$($i.path)" ($h-eq$i.sha256) $h $i.sha256}}
$capture="evidence/runs/bpm-luke-roundwood-monthly-v0.1-history-capture"
$captureManifest=Get-Content -Raw "$capture/capture_manifest.json"|ConvertFrom-Json
$raw=Get-Content -Raw "$capture/$($captureManifest.response.path)"|ConvertFrom-Json
Add-Check "capture.http" ($captureManifest.source.http_status-eq200) $captureManifest.source.http_status 200
Add-Check "capture.response_hash" ((File-Hash "$capture/$($captureManifest.response.path)")-eq$captureManifest.response.sha256) (File-Hash "$capture/$($captureManifest.response.path)") $captureManifest.response.sha256
Add-Check "capture.cells" (($raw.value.Count-eq158)-and($captureManifest.response.cell_count-eq158)) "$($raw.value.Count)/$($captureManifest.response.cell_count)" "158/158"
Add-Check "capture.no_missing" (@($raw.value|Where-Object{$null-eq$_}).Count-eq0) (@($raw.value|Where-Object{$null-eq$_}).Count) 0
Add-Check "capture.no_status" ($null-eq$raw.status) $raw.status $null
Add-Check "capture.one_post" ($captureManifest.source.remote_data_posts-eq1) $captureManifest.source.remote_data_posts 1
Add-Check "capture.no_get" ($captureManifest.source.remote_metadata_gets-eq0) $captureManifest.source.remote_metadata_gets 0
$run="evidence/runs/bpm-luke-roundwood-monthly-v0.1-causal"
$manifest=Get-Content -Raw "$run/MANIFEST.json"|ConvertFrom-Json
$artifactFailures=0
foreach($i in $manifest.artifacts){$p="$run/$($i.path)";if((-not(Test-Path $p))-or((Get-Item $p).Length-ne$i.bytes)-or((File-Hash $p)-ne$i.sha256)){$artifactFailures++}}
Add-Check "run.manifest_count" (($manifest.artifact_count_excluding_manifest-eq713)-and($manifest.artifacts.Count-eq713)) "$($manifest.artifact_count_excluding_manifest)/$($manifest.artifacts.Count)" "713/713"
Add-Check "run.manifest_failures" ($artifactFailures-eq0) $artifactFailures 0
$result=Get-Content -Raw "$run/RESULT.json"|ConvertFrom-Json
$forecast=Get-Content -Raw "$run/FORECAST_2026-08.json"|ConvertFrom-Json
Add-Check "run.status" ($result.status-eq"RETROSPECTIVE_REPLAY_COMPLETE_PROSPECTIVE_2026_08_FROZEN") $result.status "RETROSPECTIVE_REPLAY_COMPLETE_PROSPECTIVE_2026_08_FROZEN"
Add-Check "run.transitions" (($result.target_count-eq78)-and($result.scored_target_count-eq77)) "$($result.target_count)/$($result.scored_target_count)" "78/77"
Add-Check "run.preopened_exclusion" (($result.preopened_targets_excluded_from_weights_and_aggregates.Count-eq1)-and($result.preopened_targets_excluded_from_weights_and_aggregates[0]-eq"2026-07")) ($result.preopened_targets_excluded_from_weights_and_aggregates-join',') "2026-07"
Add-Check "run.no_global_winner" ($null-eq$result.global_winner) $result.global_winner $null
$z=@(Get-ChildItem "$run/z_post/*.json"|ForEach-Object{Get-Content -Raw $_.FullName|ConvertFrom-Json})
Add-Check "run.z_post_count" ($z.Count-eq156) $z.Count 156
Add-Check "run.no_resets" (@($z|Where-Object{$_.reset}).Count-eq0) (@($z|Where-Object{$_.reset}).Count) 0
Add-Check "run.weight_quarantine" (@($z|Where-Object{-not$_.weight_evidence_updated}).Count-eq2) (@($z|Where-Object{-not$_.weight_evidence_updated}).Count) 2
$freezes=@(Get-ChildItem "$run/freezes/*.json"|ForEach-Object{Get-Content -Raw $_.FullName|ConvertFrom-Json})
Add-Check "run.bootstrap_freezes" (@($freezes|Where-Object{$_.bootstrap_seasonality}).Count-eq22) (@($freezes|Where-Object{$_.bootstrap_seasonality}).Count) 22
$years=@(Get-ChildItem "$run/checkpoints/*.json"|ForEach-Object{Get-Content -Raw $_.FullName|ConvertFrom-Json})
Add-Check "run.year_checkpoints" (($years.Count-eq7)-and(@($years|Where-Object{-not$_.no_reset}).Count-eq0)) "$($years.Count)/$(@($years|Where-Object{-not$_.no_reset}).Count)" "7/0"
Add-Check "forecast.target" (($forecast.target_period-eq"2026-08")-and(-not$forecast.target_opened)-and(-not$forecast.target_available_in_raw_capture)) "$($forecast.target_period)/$($forecast.target_opened)/$($forecast.target_available_in_raw_capture)" "2026-08/False/False"
Add-Check "forecast.volume" (Close-To $forecast.targets.volume.mixture_raw_location 439468.29700852797 1e-6) $forecast.targets.volume.mixture_raw_location 439468.29700852797
Add-Check "forecast.price" (Close-To $forecast.targets.price.mixture_raw_location 82.43425966475738 1e-9) $forecast.targets.price.mixture_raw_location 82.43425966475738
$cart=Get-Content -Raw "outputs/BPM_LUKE_ROUNDWOOD_MONTHLY_LOCAL_CARTOGRAPHY_20260822.json"|ConvertFrom-Json
Add-Check "cartography.classification" ($cart.classification-eq"POST_OUTCOME_DESCRIPTIVE_DERIVATIVE_NO_MODEL_SELECTION_OR_AUTHORITY_PROMOTION") $cart.classification "POST_OUTCOME_DESCRIPTIVE_DERIVATIVE_NO_MODEL_SELECTION_OR_AUTHORITY_PROMOTION"
Add-Check "cartography.no_global_winner" ($null-eq$cart.global_winner) $cart.global_winner $null
Add-Check "cartography.volume_M2_reduction" (Close-To $cart.targets.volume.whole_history_diagnostic.relative_absolute_error_reduction_vs_M0.M2 0.048495962306504194) $cart.targets.volume.whole_history_diagnostic.relative_absolute_error_reduction_vs_M0.M2 0.048495962306504194
Add-Check "cartography.price_M2_reduction" (Close-To $cart.targets.price.whole_history_diagnostic.relative_absolute_error_reduction_vs_M0.M2 0.17790827189812194) $cart.targets.price.whole_history_diagnostic.relative_absolute_error_reduction_vs_M0.M2 0.17790827189812194
$staging=@(Get-ChildItem -Force "evidence/runs"|Where-Object{$_.Name-like'.bpm-luke-roundwood-monthly-v0.1*'})
Add-Check "no_staging" ($staging.Count-eq0) $staging.Count 0
$fail=@($checks|Where-Object{-not$_.pass});$audit=[ordered]@{schema="kch-bayesian-markets-v9-audit/v1";generated_at=(Get-Date -Format o);status=if($fail.Count){"FAIL"}else{"PASS"};checks=$checks.Count;failures=$fail.Count;prior_v8_checks=$v8.checks;prior_v8_failures=$v8.failures;adverse_states_asserted=$contract.adverse_states;details=$checks}
[IO.File]::WriteAllText([IO.Path]::GetFullPath((Join-Path (Get-Location)$OutputPath)),($audit|ConvertTo-Json -Depth 12),[Text.UTF8Encoding]::new($false));$audit|ConvertTo-Json -Depth 3;if($fail.Count){exit 1}
