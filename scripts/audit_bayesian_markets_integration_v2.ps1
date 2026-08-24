param(
    [string]$OutputPath = "governance/KCH_BAYESIAN_MARKETS_V2_AUDIT.json"
)

$ErrorActionPreference = "Stop"
$checks = [Collections.Generic.List[object]]::new()
function Add-Check([string]$Name, [bool]$Pass, [object]$Observed, [object]$Expected) {
    $checks.Add([pscustomobject]@{name=$Name;pass=$Pass;observed=$Observed;expected=$Expected})
}
function File-Hash([string]$Path) { return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash }
function Audit-HashSet([object[]]$Items, [string]$Prefix) {
    foreach($item in $Items){
        $exists=Test-Path -LiteralPath $item.path
        Add-Check "$Prefix.exists.$($item.path)" $exists $exists $true
        if($exists){$actual=File-Hash $item.path;Add-Check "$Prefix.hash.$($item.path)" ($actual -eq $item.sha256) $actual $item.sha256}
    }
}

$contract=Get-Content -Raw -LiteralPath "governance/KCH_BAYESIAN_MARKETS_EVIDENCE_CONTRACT_V2.json"|ConvertFrom-Json
$receipt=Get-Content -Raw -LiteralPath "governance/KCH_BAYESIAN_MARKETS_INTEGRATION_RECEIPT_V2.json"|ConvertFrom-Json
$rmk=Get-Content -Raw -LiteralPath "governance/KCH_BAYESIAN_MARKETS_RMK_INVENTORY_ADDENDUM_V1.json"|ConvertFrom-Json
Audit-HashSet @($contract.frozen_evidence) "contract"
Audit-HashSet @($rmk.frozen_evidence) "rmk"
$missionHash=File-Hash $contract.mission_register.path
Add-Check "contract.mission_hash" ($missionHash -eq $contract.mission_register.sha256) $missionHash $contract.mission_register.sha256
$contractHash=File-Hash $receipt.evidence_contract.path
Add-Check "receipt.contract_hash" ($contractHash -eq $receipt.evidence_contract.sha256) $contractHash $receipt.evidence_contract.sha256
Add-Check "rmk.parent_contract_hash" ($contractHash -eq $rmk.parent_evidence_contract.sha256) $contractHash $rmk.parent_evidence_contract.sha256

$index=Import-Csv -LiteralPath "canonical/CLASSIFICATION_INDEX_V6.csv"
Add-Check "index.rows" ($index.Count -eq 26) $index.Count 26
Add-Check "index.bpm" (@($index|Where-Object canonical_family -eq "BPM").Count -eq 9) @($index|Where-Object canonical_family -eq "BPM").Count 9
Add-Check "index.bum" (@($index|Where-Object canonical_family -eq "BUM").Count -eq 1) @($index|Where-Object canonical_family -eq "BUM").Count 1
Add-Check "index.hbp" (@($index|Where-Object canonical_family -eq "HBP").Count -eq 12) @($index|Where-Object canonical_family -eq "HBP").Count 12
Add-Check "index.unclassified" (@($index|Where-Object canonical_family -eq "UNCLASSIFIED_PENDING_CONTENT_REVIEW").Count -eq 4) @($index|Where-Object canonical_family -eq "UNCLASSIFIED_PENDING_CONTENT_REVIEW").Count 4

$ledger=Import-Csv -LiteralPath "governance/HBP_ARGENTINA_EUROSTAT_CAMPAIGN_LEDGER_V1.csv"
Add-Check "hbp.ledger_rows" ($ledger.Count -eq 6) $ledger.Count 6
Add-Check "hbp.ucii_legacy_invalid" (@($ledger|Where-Object scientific_state -match "LEGACY").Count -eq 1) @($ledger|Where-Object scientific_state -match "LEGACY").Count 1
Add-Check "hbp.eurostat_not_estimable" (@($ledger|Where-Object scientific_state -match "NOT_ESTIMABLE").Count -eq 1) @($ledger|Where-Object scientific_state -match "NOT_ESTIMABLE").Count 1

$queue=Import-Csv -LiteralPath "evidence/probes/rmk-url-inventory-v1/rmk_ordered_payload_queue_v3.csv"
$unique=@($queue.payload_url|Sort-Object -Unique).Count
$pairDates=@($queue|Where-Object event_date|Group-Object event_date|Where-Object{($_.Group.role -contains "RESULT") -and ($_.Group.role -contains "OFFER_OR_FORM")}).Count
Add-Check "rmk.queue_rows" ($queue.Count -eq 63) $queue.Count 63
Add-Check "rmk.queue_unique_urls" ($unique -eq 63) $unique 63
Add-Check "rmk.head_200" (@($queue|Where-Object head_status -eq "200").Count -eq 63) @($queue|Where-Object head_status -eq "200").Count 63
Add-Check "rmk.bodies_closed" (@($queue|Where-Object body_opened -ne "False").Count -eq 0) @($queue|Where-Object body_opened -ne "False").Count 0
Add-Check "rmk.pair_dates" ($pairDates -eq 15) $pairDates 15
Add-Check "rmk.schema_exclusions" (@($queue|Where-Object acquisition_state -eq "SCHEMA_PROBE_EXCLUDED_FROM_BLIND_EVALUATION").Count -eq 2) @($queue|Where-Object acquisition_state -eq "SCHEMA_PROBE_EXCLUDED_FROM_BLIND_EVALUATION").Count 2
Add-Check "rmk.invalid_v1_marker" (Test-Path "evidence/probes/rmk-url-inventory-v1/INVALID_DO_NOT_EXECUTE_QUEUE_V1.md") (Test-Path "evidence/probes/rmk-url-inventory-v1/INVALID_DO_NOT_EXECUTE_QUEUE_V1.md") $true
Add-Check "rmk.invalid_v2_marker" (Test-Path "evidence/probes/rmk-url-inventory-v1/INVALID_DO_NOT_EXECUTE_QUEUE_V2.md") (Test-Path "evidence/probes/rmk-url-inventory-v1/INVALID_DO_NOT_EXECUTE_QUEUE_V2.md") $true

$rmkPre=Get-Content -Raw -LiteralPath "preregistrations/BPM_RMK_TIMBER_CAUSAL_CAMPAIGN_V0.1.json"|ConvertFrom-Json
$coralPre=Get-Content -Raw -LiteralPath "preregistrations/HBP_SPAIN_INDUSTRIAL_CORAL_CAUSAL_CAMPAIGN_V0.1.json"|ConvertFrom-Json
Add-Check "prereg.rmk.no_global_winner" ($null -eq $rmkPre.authority.global_winner) $rmkPre.authority.global_winner $null
Add-Check "prereg.coral.no_global_winner" ($null -eq $coralPre.authority.aggregate_winner) $coralPre.authority.aggregate_winner $null
Add-Check "contract.no_automatic_promotion" (-not $contract.experimental_invariants.automatic_promotion) $contract.experimental_invariants.automatic_promotion $false

$failures=@($checks|Where-Object{-not $_.pass})
$audit=[ordered]@{
    schema="kch-bayesian-markets-v2-audit/v1";generated_at=(Get-Date -Format o);
    status=if($failures.Count -eq 0){"PASS"}else{"FAIL"};checks=$checks.Count;failures=$failures.Count;
    adverse_states_asserted=@("AEAT_LOCAL_LOSS","DECEMBER_ABSTENTION","UCII_LEGACY_INVALID","EUROSTAT_NOT_ESTIMABLE","COMTRADE_QUARANTINE","RMK_QUEUE_V1_V2_INVALID");
    details=$checks
}
[IO.File]::WriteAllText([IO.Path]::GetFullPath((Join-Path (Get-Location) $OutputPath)),($audit|ConvertTo-Json -Depth 12),[Text.UTF8Encoding]::new($false))
$audit|ConvertTo-Json -Depth 4
if($failures.Count){exit 1}
