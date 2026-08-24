param([string]$OutputPath = "governance/KCH_BAYESIAN_MARKETS_V11_AUDIT.json")
$ErrorActionPreference = "Stop"
$checks = [Collections.Generic.List[object]]::new()
function Add-Check([string]$Name, [bool]$Pass, [object]$Observed, [object]$Expected) {$checks.Add([pscustomobject]@{name=$Name;pass=$Pass;observed=$Observed;expected=$Expected})}
function File-Hash([string]$Path) {(Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash}
$contract = Get-Content -LiteralPath "governance/KCH_BAYESIAN_MARKETS_EVIDENCE_CONTRACT_V11.json" -Raw | ConvertFrom-Json
$v10 = Get-Content -LiteralPath $contract.prior_audit.path -Raw | ConvertFrom-Json
Add-Check "prior_v10" (((File-Hash $contract.prior_audit.path)-eq$contract.prior_audit.sha256)-and($v10.status-eq"PASS")-and($v10.failures-eq0)) "$($v10.status)/$($v10.checks)/$($v10.failures)" "PASS/42/0"
foreach($item in @($contract.prior_contract,$contract.prior_receipt,$contract.mission_register,$contract.checkpoint)){Add-Check "hash.$($item.path)" ((File-Hash $item.path)-eq$item.sha256) (File-Hash $item.path) $item.sha256}
foreach($item in $contract.new_frozen_evidence){$exists=Test-Path -LiteralPath $item.path;Add-Check "exists.$($item.path)" $exists $exists $true;if($exists){Add-Check "hash.$($item.path)" ((File-Hash $item.path)-eq$item.sha256) (File-Hash $item.path) $item.sha256}}
foreach($run in @('evidence/runs/hbp-indec-ipi-sa-v0.1-2026-07-freeze','evidence/runs/hbp-eurostat-sts-es-c-v0.1-2026-07-adjudication-20260822','evidence/runs/hbp-indec-ucii-v0.1-2026-07-schema-capture')){$manifest=Get-Content -LiteralPath "$run/manifest.json" -Raw|ConvertFrom-Json;$bad=0;foreach($item in $manifest.files){if((-not(Test-Path -LiteralPath $item.path))-or((File-Hash $item.path)-ne$item.sha256)-or((Get-Item -LiteralPath $item.path).Length-ne$item.bytes)){$bad++}};Add-Check "manifest.$run" ($bad-eq0) $bad 0}
$ipi=Get-Content -LiteralPath 'evidence/runs/hbp-indec-ipi-sa-v0.1-2026-07-freeze/forecast_freeze.json' -Raw|ConvertFrom-Json
Add-Check "ipi.freeze" (($ipi.status-eq'FROZEN_PRE_OUTCOME')-and($ipi.target_month-eq'2026-07')-and(-not$ipi.outcome_opened)-and($null-eq$ipi.global_winner)) "$($ipi.status)/$($ipi.target_month)/$($ipi.outcome_opened)" 'FROZEN_PRE_OUTCOME/2026-07/False'
$euro=Get-Content -LiteralPath 'evidence/runs/hbp-eurostat-sts-es-c-v0.1-2026-07-adjudication-20260822/adjudication.json' -Raw|ConvertFrom-Json
Add-Check "euro.pending" (($euro.outcome_state-eq'OUTCOME_PENDING')-and(-not$euro.posterior_updated)-and(-not$euro.next_target_frozen)) "$($euro.outcome_state)/$($euro.posterior_updated)/$($euro.next_target_frozen)" 'OUTCOME_PENDING/False/False'
$gate=Get-Content -LiteralPath 'evidence/runs/hbp-indec-ucii-logit-v0.1-2026-07-gate-fail/GATE_FAILURE.json' -Raw|ConvertFrom-Json
Add-Check "ucii.gate" (($gate.status-eq'GATE_FAIL_SECTOR_BOUNDARY_VALUE_BEFORE_FIT')-and($gate.sector_boundary_events.Count-eq2)-and(-not$gate.fit_performed)-and(-not$gate.forecast_performed)) "$($gate.status)/$($gate.sector_boundary_events.Count)/$($gate.fit_performed)" 'GATE_FAIL_SECTOR_BOUNDARY_VALUE_BEFORE_FIT/2/False'
$fail=@($checks|Where-Object{-not$_.pass});$audit=[ordered]@{schema='kch-bayesian-markets-v11-audit/v1';generated_at=(Get-Date -Format o);status=if($fail.Count){'FAIL'}else{'PASS'};checks=$checks.Count;failures=$fail.Count;prior_v10_checks=$v10.checks;adverse_states_asserted=@('EUROSTAT_OUTCOME_PENDING','UCII_V0_1_GATE_FAIL','NO_GLOBAL_WINNER');details=$checks}
[IO.File]::WriteAllText([IO.Path]::GetFullPath((Join-Path (Get-Location)$OutputPath)),($audit|ConvertTo-Json -Depth 12),[Text.UTF8Encoding]::new($false));$audit|ConvertTo-Json -Depth 3;if($fail.Count){exit 1}
