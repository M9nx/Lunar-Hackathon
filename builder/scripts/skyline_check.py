#!/usr/bin/env python3
"""Teaching comparator: ridge skyline vs centre-ray (§6 worked example)."""

from __future__ import annotations

import argparse
import math
import sys


def sight_angle_deg(e_m: float, n_m: float, u_m: float) -> float:
    q = math.hypot(e_m, n_m)
    return math.degrees(math.atan2(u_m, q)) if q > 0 else 90.0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sun-elev", type=float, default=0.8)
    parser.add_argument("--samples", type=str, default="1000,0,20.947|2000,0,24.436",
                        help="E,N,U metre tuples separated by |")
    args = parser.parse_args()

    max_alpha = -math.inf
    limit = None
    for chunk in args.samples.split("|"):
        e, n, u = (float(x) for x in chunk.split(","))
        alpha = sight_angle_deg(e, n, u)
        if alpha > max_alpha:
            max_alpha = alpha
            limit = (e, n, u, alpha)

    horizon = max_alpha
    margin = args.sun_elev - horizon
    state = "clear" if margin > 0 else "blocked"
    print(f"horizon_deg={horizon:.4f} margin_deg={margin:.4f} state={state}")
    if limit:
        print(f"limiting_sample ENU={limit[0]},{limit[1]},{limit[2]} alpha={limit[3]:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())