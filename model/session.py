# model/session.py
import json
from pathlib import Path
from typing import Tuple

from .report import TestReport


class SessionManager:
    """Handles saving and loading user sessions to a JSON file."""
    def __init__(self, path: Path):
        self.path = path

    def save(self, report: TestReport, metadata: dict) -> None:
        data = {
            'df': report.df.to_dict(orient='records'),
            'metadata': metadata
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, 'w') as f:
            json.dump(data, f, indent=2)

    def load(self) -> Tuple[TestReport, dict]:
        with open(self.path) as f:
            data = json.load(f)
        report = TestReport(data.get('df', []))
        metadata = data.get('metadata', {})
        return report, metadata