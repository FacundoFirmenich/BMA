param(
    [string]$InputQueue = "evidence/probes/rmk-url-inventory-v1/rmk_ordered_payload_queue_with_head.csv",
    [string]$OutputDir = "evidence/probes/rmk-url-inventory-v1"
)

$ErrorActionPreference = "Stop"
$sourceRows = Import-Csv -LiteralPath $InputQueue
$canonical = foreach ($group in ($sourceRows | Group-Object payload_url)) {
    $url = $group.Name
    $probe = $url.ToLowerInvariant()
    $isReference = $probe -match "standard|tyyptingimused|hinnastatistika|veohind|veokaugus|sadamahinnad"
    $role = if ($isReference) { "NORMALIZATION_REFERENCE" }
        elseif ($group.Group.role -contains "RESULT") { "RESULT" }
        elseif ($group.Group.role -contains "OFFER_OR_FORM") { "OFFER_OR_FORM" }
        else { "UNRESOLVED" }
    $dates = if ($isReference) { @() } else { @($group.Group.event_date | Where-Object { $_ } | Sort-Object -Unique) }
    $phases = if ($isReference) { @() } else { @($group.Group.phase_hint | Where-Object { $_ } | Sort-Object -Unique) }
    if ($dates.Count -gt 1) { throw "Conflicting event dates for ${url}: $($dates -join ',')" }
    if ($phases.Count -gt 1) { throw "Conflicting phase hints for ${url}: $($phases -join ',')" }
    $metaGroups = @($group.Group | Group-Object head_status,content_type,content_length,etag,last_modified)
    if ($metaGroups.Count -gt 1) { throw "Conflicting HEAD metadata for $url" }
    $first = $group.Group[0]
    [pscustomobject]@{
        sequence=0; event_date=if($dates.Count){$dates[0]}else{""}; phase_hint=if($phases.Count){$phases[0]}else{""};
        within_date_order=switch($role){"NORMALIZATION_REFERENCE"{0};"OFFER_OR_FORM"{1};"RESULT"{2};default{9}};
        role=$role; acquisition_state="PENDING_RECOMPUTE";
        date_evidence=($group.Group.date_evidence|Where-Object{$_}|Sort-Object -Unique)-join ";";
        payload_url=$url; discovery_pages=($group.Group.discovery_page|Where-Object{$_}|Sort-Object -Unique)-join ";";
        head_status=$first.head_status; content_type=$first.content_type; content_length=$first.content_length;
        etag=$first.etag; last_modified=$first.last_modified; head_error=$first.head_error; body_opened=$false
    }
}

$dateRoles=@{}
foreach($g in ($canonical|Where-Object event_date|Group-Object event_date)){$dateRoles[$g.Name]=@($g.Group.role)}
$schemaProbeUrls=@(
    "https://rmk.ee/wp-content/uploads/2026/06/Myygiobjektid_30.06.2026.xlsx",
    "https://rmk.ee/wp-content/uploads/2026/07/Edukad_EP_30.06.2026.xlsx"
)
foreach($row in $canonical){
    $row.acquisition_state = if($schemaProbeUrls -contains $row.payload_url){"SCHEMA_PROBE_EXCLUDED_FROM_BLIND_EVALUATION"}
        elseif($row.role -eq "NORMALIZATION_REFERENCE") {"REFERENCE_VERSION_FREEZE_BODY_CLOSED"}
        elseif(-not $row.event_date -and $row.phase_hint){"QUARANTINE_PHASE_ONLY_DATE_UNRESOLVED"}
        elseif(-not $row.event_date){"UNRESOLVED_NOT_IN_REPLAY"}
        elseif($row.role -eq "RESULT" -and -not ($dateRoles[$row.event_date] -contains "OFFER_OR_FORM")){"RESULT_ONLY_ELIGIBILITY_AUDIT"}
        elseif(($dateRoles[$row.event_date] -contains "RESULT") -and ($dateRoles[$row.event_date] -contains "OFFER_OR_FORM")){"PAIR_DISCOVERED_NOT_YET_OPENED"}
        else{"UNPAIRED_NOT_IN_REPLAY"}
}
$canonical=@($canonical|Sort-Object @{Expression={if($_.event_date){$_.event_date}else{"9999-99-99"}}},within_date_order,payload_url)
for($i=0;$i -lt $canonical.Count;$i++){$canonical[$i].sequence=$i+1}

$resolvedOutput=[IO.Path]::GetFullPath((Join-Path (Get-Location) $OutputDir))
$queuePath=Join-Path $resolvedOutput "rmk_ordered_payload_queue_v2.csv"
$canonical|Export-Csv -NoTypeInformation -Encoding utf8 -LiteralPath $queuePath
$pairDates=@($canonical|Where-Object event_date|Group-Object event_date|Where-Object{($_.Group.role -contains "RESULT") -and ($_.Group.role -contains "OFFER_OR_FORM")})
$manifest=[ordered]@{
    schema="rmk-ordered-payload-queue/v2";generated_at=(Get-Date -Format o);
    source_queue_sha256=(Get-FileHash -Algorithm SHA256 -LiteralPath $InputQueue).Hash;
    rows=$canonical.Count;unique_urls=@($canonical.payload_url|Sort-Object -Unique).Count;
    date_role_conflicts=0;head_metadata_conflicts=0;bodies_opened=0;
    pair_dates=$pairDates.Count;result_only_rows=@($canonical|Where-Object acquisition_state -eq "RESULT_ONLY_ELIGIBILITY_AUDIT").Count;
    normalization_references=@($canonical|Where-Object role -eq "NORMALIZATION_REFERENCE").Count;
    schema_probe_excluded_rows=@($canonical|Where-Object acquisition_state -eq "SCHEMA_PROBE_EXCLUDED_FROM_BLIND_EVALUATION").Count;
    queue_sha256=(Get-FileHash -Algorithm SHA256 -LiteralPath $queuePath).Hash
}
$manifestPath=Join-Path $resolvedOutput "rmk_ordered_payload_queue_v2_manifest.json"
[IO.File]::WriteAllText($manifestPath,($manifest|ConvertTo-Json -Depth 6),[Text.UTF8Encoding]::new($false))
$manifest|ConvertTo-Json -Depth 6
