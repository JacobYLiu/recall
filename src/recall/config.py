"""Runtime settings, loaded from environment / .env."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Settings:
    model: str = "claude-sonnet-4-5"
    max_iterations: int = 5  # hard critic-loop cap (spec Section 3)
    max_cost_usd: float = 2.00  # per-run cost ceiling (spec Section 3)
    data_dir: Path = Path("./data")

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            model=os.environ.get("RECALL_MODEL", cls.model),
            max_iterations=int(os.environ.get("RECALL_MAX_ITERATIONS", cls.max_iterations)),
            max_cost_usd=float(os.environ.get("RECALL_MAX_COST_USD", cls.max_cost_usd)),
            data_dir=Path(os.environ.get("RECALL_DATA_DIR", str(cls.data_dir))),
        )

    @property
    def facts_db(self) -> Path:
        return self.data_dir / "facts.sqlite3"

    @property
    def checkpoints_db(self) -> Path:
        return self.data_dir / "checkpoints.sqlite3"

    @property
    def chroma_dir(self) -> Path:
        return self.data_dir / "chroma"


def load_settings() -> Settings:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass
    settings = Settings.from_env()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    return settings
