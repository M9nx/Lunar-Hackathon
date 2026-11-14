"""Centre-ray clearance classification (Master Reference §5–6)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

State = Literal["clear", "blocked", "unknown"]
Body = Literal["sun", "earth"]

VALID_SUN_ID = 10
VALID_EARTH_ID = 399
REJECT_BARY_ID = 3

JOINT_PRIORITY: tuple[State, ...] = ("blocked", "unknown", "clear")


@dataclass(frozen=True)
class ClassifiedSample:
    elevation_deg: float | None
    horizon_deg: float | None
    state: State
    margin_deg: float | None
    reason: str | None = None


def classify_margin(
    elevation_deg: float | None,
    horizon_deg: float | None,
    *,
    horizon_mode: str = "geometric_0deg",
) -> ClassifiedSample:
    if elevation_deg is None:
        return ClassifiedSample(None, horizon_deg, "unknown", None, "missing_ephemeris")
    if horizon_mode == "terrain" and horizon_deg is None:
        return ClassifiedSample(elevation_deg, None, "unknown", None, "terrain_gap")
    h = 0.0 if horizon_mode == "geometric_0deg" and horizon_deg is None else horizon_deg
    if h is None:
        return ClassifiedSample(elevation_deg, None, "unknown", None, "unsupported_horizon")
    margin = elevation_deg - h
    if margin > 0:
        state: State = "clear"
    else:
        state = "blocked"
    return ClassifiedSample(elevation_deg, h, state, margin, None)


def both_lane(sun: State, earth: State) -> State:
    if sun == "blocked" or earth == "blocked":
        return "blocked"
    if sun == "unknown" or earth == "unknown":
        return "unknown"
    return "clear"


def validate_body_id(body: str, command_id: int) -> bool:
    if command_id == REJECT_BARY_ID:
        return False
    if body == "sun":
        return command_id == VALID_SUN_ID
    if body == "earth":
        return command_id == VALID_EARTH_ID
    return False