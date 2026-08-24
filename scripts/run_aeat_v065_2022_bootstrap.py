"""Execute the sealed 2022 M0 bootstrap in one uninterrupted local process."""

from pathlib import Path

from bma.experiments import aeat_monthly_sequential_v0_6_4_resume as runner


result = runner.resume(
    Path("evidence/runs/aeat-ch72-monthly-sequential-v0.6.5-2022-bootstrap-r2"), year=2022
)
print(f"status={result['status']} transitions={result['transition_count']}")
