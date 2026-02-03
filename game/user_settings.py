from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict


@dataclass
class UserSettings:
    # Audio (future-proof): keep even if not used yet
    master_volume: float = 0.8

    # Visual / UX
    reduce_motion: bool = False
    high_contrast: bool = False
    show_fps: bool = False

    # Retro display effects
    crt_enabled: bool = True
    crt_intensity: float = 0.65

    # Display (apply-on-restart unless app loop supports live switching)
    fullscreen: bool = False


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def load_user_settings(path: str | Path = "user_settings.json") -> UserSettings:
    settings_path = Path(path)
    if not settings_path.exists():
        return UserSettings()

    try:
        raw: Dict[str, Any]
        with settings_path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception:
        return UserSettings()

    return UserSettings(
        master_volume=_clamp01(raw.get("master_volume", 0.8)),
        reduce_motion=bool(raw.get("reduce_motion", False)),
        high_contrast=bool(raw.get("high_contrast", False)),
        show_fps=bool(raw.get("show_fps", False)),
        crt_enabled=bool(raw.get("crt_enabled", True)),
        crt_intensity=_clamp01(raw.get("crt_intensity", 0.65)),
        fullscreen=bool(raw.get("fullscreen", False)),
    )


def save_user_settings(settings: UserSettings, path: str | Path = "user_settings.json") -> None:
    settings_path = Path(path)
    tmp_path = settings_path.with_suffix(settings_path.suffix + ".tmp")

    payload = asdict(settings)
    payload["master_volume"] = _clamp01(payload.get("master_volume", 0.8))
    payload["crt_intensity"] = _clamp01(payload.get("crt_intensity", 0.65))

    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=4)

    tmp_path.replace(settings_path)
