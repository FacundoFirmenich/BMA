"""Execute the sealed 2022 M0 bootstrap in one uninterrupted local process."""

from pathlib import Path

from bma.experiments import aeat_monthly_sequential_v0_6_3 as base
from bma.experiments import aeat_monthly_sequential_v0_6_4 as runner


base.YEAR = 2022
result = runner.run(Path("evidence/runs/aeat-ch72-monthly-sequential-v0.6.5-2022-bootstrap-r2"))
print(f"status={result['status']} transitions={result['transition_count']}")
