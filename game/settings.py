import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple


Color = Tuple[int, int, int]


@dataclass(frozen=True)
class GameConfig:
    background_color: Color
    player_color: Color
    platform_color: Color
    obstacle_color: Color
    player_width: int
    player_height: int
    jump_strength: float
    platform_width: int
    platform_height: int


def load_config(path: str | Path = "config.json") -> GameConfig:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as f:
        raw: Dict[str, Any] = json.load(f)

    def _as_color(value: List[int]) -> Color:
        return (int(value[0]), int(value[1]), int(value[2]))

    return GameConfig(
        background_color=_as_color(raw["background"]["color"]),
        player_color=_as_color(raw["player"]["color"]),
        platform_color=_as_color(raw["platforms"]["color"]),
        obstacle_color=_as_color(raw["obstacles"]["color"]),
        player_width=int(raw["player"]["width"]),
        player_height=int(raw["player"]["height"]),
        jump_strength=float(raw["player"]["jump_strength"]),
        platform_width=int(raw["platforms"]["width"]),
        platform_height=int(raw["platforms"]["height"]),
    )
