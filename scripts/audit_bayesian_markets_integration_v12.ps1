param([string]$OutputPath = "governance/KCH_BAYESIAN_MARKETS_V12_AUDIT.json")
$ErrorActionPreference="Stop";$checks=[Collections.Generic.List[object]]::new()
function Add-Check([string]$N,[bool]$P,[object]$O,[object]$E){$checks.Add([pscustomobject]@{name=$N;pass=$P;observed=$O;expected=$E})}
function File-Hash([string]$P){(Get-FileHash -Algorithm SHA256 -LiteralPath $P).Hash}
$c=Get-Content -LiteralPath 'governance/KCH_BAYESIAN_MARKETS_EVIDENCE_CONTRACT_V12.json' -Raw|ConvertFrom-Json;$v11=Get-Content -LiteralPath $c.prior_audit.path -Raw|ConvertFrom-Json
Add-Check 'prior_v11' (((File-Hash $c.prior_audit.path)-eq$c.prior_audit.sha256)-and($v11.status-eq'PASS')-and($v11.failures-eq0)) "$($v11.status)/$($v11.checks)/$($v11.failures)" 'PASS/43/0'
foreach($i in @($c.prior_contract,$c.prior_receipt,$c.mission_register,$c.checkpoint)){Add-Check "hash.$($i.path)" ((File-Hash $i.path)-eq$i.sha256) (File-Hash $i.path) $i.sha256}
foreach($i in $c.new_frozen_evidence){$e=Test-Path -LiteralPath $i.path;Add-Check "exists.$($i.path)" $e $e $true;if($e){Add-Check "hash.$($i.path)" ((File-Hash $i.path)-eq$i.sha256) (File-Hash $i.path) $i.sha256}}
$a=Get-Content -LiteralPath 'preregistrations/HBP_INDEC_UCII_LOGIT_2026_07_FREEZE_V0.2.json' -Raw|ConvertFrom-Json
Add-Check 'parent_prereg' ((File-Hash $a.parent_preregistration.path)-eq$a.parent_preregistration.sha256) (File-Hash $a.parent_preregistration.path) $a.parent_preregistration.sha256
Add-Check 'gate_failure' ((File-Hash $a.observed_gate_failure.path)-eq$a.observed_gate_failure.sha256) (File-Hash $a.observed_gate_failure.path) $a.observed_gate_failure.sha256
Add-Check 'single_repair' (($a.exposure_boundary.model_or_prior_changed_after_scan-eq$false)-and($a.hard_invariants.sector_blocks_used_in_general_likelihood-eq$false)-and($a.hard_invariants.V0_1_gate_failure_preserved)) "$($a.exposure_boundary.model_or_prior_changed_after_scan)/$($a.hard_invariants.sector_blocks_used_in_general_likelihood)/$($a.hard_invariants.V0_1_gate_failure_preserved)" 'False/False/True'
$absent=-not(Test-Path -LiteralPath $a.execution_contract.immutable_output);Add-Check 'output_absent' $absent $absent $true
Add-Check 'no_global_winner' ($null-eq$a.hard_invariants.global_winner) $a.hard_invariants.global_winner $null
$f=@($checks|Where-Object{-not$_.pass});$audit=[ordered]@{schema='kch-bayesian-markets-v12-audit/v1';generated_at=(Get-Date -Format o);status=if($f.Count){'FAIL'}else{'PASS'};checks=$checks.Count;failures=$f.Count;prior_v11_checks=$v11.checks;details=$checks}
[IO.File]::WriteAllText([IO.Path]::GetFullPath((Join-Path (Get-Location)$OutputPath)),($audit|ConvertTo-Json -Depth 10),[Text.UTF8Encoding]::new($false));$audit|ConvertTo-Json -Depth 3;if($f.Count){exit 1}
