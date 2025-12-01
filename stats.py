import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Optional, Tuple


@dataclass
class DifficultyStats:
    runs: int = 0
    wins: int = 0
    defeats: int = 0
    quits: int = 0
    best_turns: Optional[int] = None
    win_streak: int = 0
    best_streak: int = 0


@dataclass
class StatsResult:
    new_best: bool
    streak: int
    best_streak: int


class StatsManager:
    def __init__(self, path: Path, difficulty_keys: Tuple[str, ...]) -> None:
        self.path = path
        self._difficulty_keys = difficulty_keys
        self.stats: Dict[str, DifficultyStats] = {
            key: DifficultyStats() for key in difficulty_keys
        }
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            payload = json.loads(self.path.read_text())
        except Exception:
            return
        for key, raw in payload.items():
            if key not in self.stats or not isinstance(raw, dict):
                continue
            defaults = asdict(DifficultyStats())
            defaults.update({k: raw.get(k, v) for k, v in defaults.items()})
            self.stats[key] = DifficultyStats(**defaults)

    def save(self) -> None:
        payload = {key: asdict(stats) for key, stats in self.stats.items()}
        try:
            self.path.write_text(json.dumps(payload, indent=2))
        except Exception:
            pass

    def summary_line(self, difficulty_key: str) -> str:
        stats = self.stats.get(difficulty_key)
        if not stats:
            return "No data yet."
        win_rate = (stats.wins / stats.runs * 100) if stats.runs else 0.0
        best_turns = stats.best_turns if stats.best_turns is not None else "—"
        return (
            f"runs {stats.runs}, wins {stats.wins} ({win_rate:.0f}% rate), "
            f"best {best_turns} turns, streak {stats.win_streak} (best {stats.best_streak})"
        )

    def record_run(self, difficulty_key: str, turns: int, result: str) -> StatsResult:
        stats = self.stats.setdefault(difficulty_key, DifficultyStats())
        stats.runs += 1
        new_best = False

        if result == "victory":
            stats.wins += 1
            stats.win_streak += 1
            stats.best_streak = max(stats.best_streak, stats.win_streak)
            if stats.best_turns is None or turns < stats.best_turns:
                stats.best_turns = turns
                new_best = True
        else:
            if result == "defeat":
                stats.defeats += 1
            elif result == "quit":
                stats.quits += 1
            stats.win_streak = 0

        self.save()
        return StatsResult(new_best=new_best, streak=stats.win_streak, best_streak=stats.best_streak)
