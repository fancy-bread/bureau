from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class Memory:
    """Shared scratchpad for a bureau run. Backed by a JSON file."""

    def __init__(self, run_id: str) -> None:
        self._path = Path.home() / ".bureau" / "runs" / run_id / "memory.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text("{}")

    def write(self, key: str, value: Any) -> None:
        data = self._load()
        data[key] = value
        self._path.write_text(json.dumps(data, indent=2, default=str))

    def read(self, key: str) -> Any:
        data = self._load()
        if key not in data:
            raise KeyError(key)
        return data[key]

    def summary(self) -> str:
        """Rolling summary — stub in foundation release."""
        return ""

    def _load(self) -> dict[str, Any]:
        return json.loads(self._path.read_text())
