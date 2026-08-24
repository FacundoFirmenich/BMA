param([string]$OutputPath = "governance/KCH_BAYESIAN_MARKETS_V7_AUDIT.json")
$ErrorActionPreference="Stop"
$checks=[Collections.Generic.List[object]]::new()
function Add-Check([string]$Name,[bool]$Pass,[object]$Observed,[object]$Expected){$checks.Add([pscustomobject]@{name=$Name;pass=$Pass;observed=$Observed;expected=$Expected})}
function File-Hash([string]$Path){(Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash}
function Close-To([double]$A,[double]$B,[double]$T=1e-10){[Math]::Abs($A-$B)-le$T}
if(-not(Test-Path ".artifact_probe")){New-Item -ItemType Directory ".artifact_probe"|Out-Null}
$priorPath=".artifact_probe/bma-v6-audit-$([Guid]::NewGuid().ToString('N')).json"
try{$null=& "scripts/audit_bayesian_markets_integration_v6.ps1" -OutputPath $priorPath;$prior=Get-Content -Raw $priorPath|ConvertFrom-Json;Add-Check "prior_v6.status" ($prior.status-eq"PASS") $prior.status "PASS";Add-Check "prior_v6.failures" ($prior.failures-eq 0) $prior.failures 0}finally{if(Test-Path $priorPath){Remove-Item -Force $priorPath}}
$contract=Get-Content -Raw "governance/KCH_BAYESIAN_MARKETS_EVIDENCE_CONTRACT_V7.json"|ConvertFrom-Json
$receipt=Get-Content -Raw "governance/KCH_BAYESIAN_MARKETS_INTEGRATION_RECEIPT_V7.json"|ConvertFrom-Json
$prereg=Get-Content -Raw "preregistrations/BPM_LUKE_ROUNDWOOD_PUBLIC_PROBE_V0.1.json"|ConvertFrom-Json
$amendment=Get-Content -Raw "preregistrations/BPM_LUKE_ROUNDWOOD_PUBLIC_PROBE_AMENDMENT_A1.json"|ConvertFrom-Json
$run="evidence/runs/bpm-luke-roundwood-public-probe-v0.1"
$manifest=Get-Content -Raw "$run/capture_manifest.json"|ConvertFrom-Json
$adj=Get-Content -Raw "$run/probe_adjudication.json"|ConvertFrom-Json
Add-Check "contract.prior_hash" ((File-Hash $contract.prior_contract.path)-eq$contract.prior_contract.sha256) (File-Hash $contract.prior_contract.path) $contract.prior_contract.sha256
Add-Check "contract.mission_hash" ((File-Hash $contract.mission_register.path)-eq$contract.mission_register.sha256) (File-Hash $contract.mission_register.path) $contract.mission_register.sha256
foreach($i in $contract.new_frozen_evidence){$exists=Test-Path $i.path;Add-Check "exists.$($i.path)" $exists $exists $true;if($exists){$h=File-Hash $i.path;Add-Check "hash.$($i.path)" ($h-eq$i.sha256) $h $i.sha256}}
$ch=File-Hash $receipt.evidence_contract.path;Add-Check "receipt.contract_hash" ($ch-eq$receipt.evidence_contract.sha256) $ch $receipt.evidence_contract.sha256
Add-Check "prereg.before_schema_values" ($prereg.status-eq"PREREGISTERED_BEFORE_SCHEMA_OR_DATA_BYTE_ACQUISITION") $prereg.status "PREREGISTERED_BEFORE_SCHEMA_OR_DATA_BYTE_ACQUISITION"
Add-Check "amendment.before_values" ($amendment.status-eq"FROZEN_AFTER_METADATA_ONLY_BEFORE_ANY_DATA_VALUE") $amendment.status "FROZEN_AFTER_METADATA_ONLY_BEFORE_ANY_DATA_VALUE"
Add-Check "amendment.no_values_opened" (-not$amendment.observed_metadata_only.data_values_opened) $amendment.observed_metadata_only.data_values_opened $false
Add-Check "capture.one_get" ($manifest.invariants.remote_metadata_gets-eq1) $manifest.invariants.remote_metadata_gets 1
Add-Check "capture.one_post" ($manifest.invariants.remote_data_posts-eq1) $manifest.invariants.remote_data_posts 1
Add-Check "capture.two_cells" ($manifest.data.observed_value_count-eq2) $manifest.data.observed_value_count 2
Add-Check "capture.exact_dimensions" (($manifest.data.id-join',')-eq'INFO,M,MPKH,KAUP,PTL') ($manifest.data.id-join',') 'INFO,M,MPKH,KAUP,PTL'
Add-Check "adj.pass" ($adj.status-eq"PASS_SINGLE_PRODUCT_PRICE_VOLUME_SUPPORT") $adj.status "PASS_SINGLE_PRODUCT_PRICE_VOLUME_SUPPORT"
Add-Check "adj.volume" ($adj.observation.volume_m3-eq429000) $adj.observation.volume_m3 429000
Add-Check "adj.price" (Close-To $adj.observation.price_eur_per_m3 83.14) $adj.observation.price_eur_per_m3 83.14
Add-Check "adj.months" ($adj.support.metadata_month_count-eq79) $adj.support.metadata_month_count 79
Add-Check "adj.first_last" (($adj.support.metadata_first_month+','+$adj.support.metadata_last_month)-eq'2020M01,2026M07') ($adj.support.metadata_first_month+','+$adj.support.metadata_last_month) '2020M01,2026M07'
Add-Check "adj.post_release" $adj.quality_boundaries.post_release_observation $adj.quality_boundaries.post_release_observation $true
Add-Check "adj.no_historical_vintage" (-not$adj.quality_boundaries.first_release_vintages_preserved) $adj.quality_boundaries.first_release_vintages_preserved $false
Add-Check "adj.revisions" $adj.quality_boundaries.revision_notes_present $adj.quality_boundaries.revision_notes_present $true
Add-Check "adj.official_flag_false" (-not$adj.quality_boundaries.response_extension_official_statistics_flag) $adj.quality_boundaries.response_extension_official_statistics_flag $false
foreach($f in @('model_fit','forecast','score','posterior_update','Z_post_update','historical_freeze_reconstruction','cross_source_pooling','automatic_promotion')){Add-Check "authority.$f" (-not$adj.authority.$f) $adj.authority.$f $false}
Add-Check "authority.no_global_winner" ($null-eq$adj.authority.global_winner) $adj.authority.global_winner $null
$fail=@($checks|Where-Object{-not$_.pass});$audit=[ordered]@{schema="kch-bayesian-markets-v7-audit/v1";generated_at=(Get-Date -Format o);status=if($fail.Count){"FAIL"}else{"PASS"};checks=$checks.Count;failures=$fail.Count;prior_v6_checks=$prior.checks;prior_v6_failures=$prior.failures;adverse_states_asserted=$contract.adverse_states;details=$checks}
[IO.File]::WriteAllText([IO.Path]::GetFullPath((Join-Path (Get-Location)$OutputPath)),($audit|ConvertTo-Json -Depth 12),[Text.UTF8Encoding]::new($false));$audit|ConvertTo-Json -Depth 3;if($fail.Count){exit 1}
