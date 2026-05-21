"""Quick verification of gauge tick spacing."""
import sys, math
sys.path.insert(0, '.')
from app.widgets.speed_gauge import _pick_major_step, _pick_minor_step, _label_fmt
from app.config import compute_speed_range

def show(label, target_ms, use_kmh):
    factor = 3.6 if use_kmh else 1.0
    unit = 'km/h' if use_kmh else 'm/s'
    target_d = target_ms * factor
    d_min_d, d_max_d = compute_speed_range(target_d)
    span_d   = d_max_d - d_min_d
    major    = _pick_major_step(span_d, floor_step=1.0 if use_kmh else 0.0)
    minor    = _pick_minor_step(major)
    fmt      = _label_fmt(major, use_kmh)
    first    = math.ceil(round(d_min_d / minor, 8)) * minor
    majors   = []
    t = first
    while t <= d_max_d + minor * 1e-6:
        if abs(t / major - round(t / major)) < 1e-6:
            majors.append(round(t, 10))
        t = round(t + minor, 10)
    n_sub = round(major / minor)
    print(f"{label:<28} [{d_min_d:{fmt}}, {d_max_d:{fmt}}] {unit}  "
          f"major={major}  minor={minor}  ({n_sub}/major)  "
          f"labels={[f'{v:{fmt}}' for v in majors]}")

show('1.5 m/s (bug)', 1.5, False)
show('3 km/h',        3/3.6, True)
show('1 m/s',         1.0, False)
show('5 m/s',         5.0, False)
show('10 m/s',       10.0, False)
show('10 km/h',      10/3.6, True)
show('20 km/h',      20/3.6, True)
show('30 km/h',      30/3.6, True)
