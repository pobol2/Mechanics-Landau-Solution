# SPDX-License-Identifier: MIT
# Copyright (c) 2026 P.O. Bolduc. See LICENSE-CODE.
"""Helpers for analytical comparisons; no engine trajectory is generated here."""
import numpy as np
from study import ROOT, run_engine


class Verification:
    def __init__(self, name, exe, work):
        self.name, self.exe, self.work = name, exe, work
        self.passed = True

    def check(self, condition, message):
        if not condition:
            print("FAIL:", message)
            self.passed = False

    def run(self, label, case, duration, dt, step):
        data = run_engine(self.exe, {**case, "fixed_step": step}, duration, dt, 1e-11,
                          self.work / f"{self.name}-{label}.csv", 1)
        if not all(np.isfinite(v).all() for v in data.values()):
            raise RuntimeError(f"{label}: non-finite engine output")
        self.check(len(data["t"]) == round(duration / dt) + 1 and
                   np.allclose(data["t"], np.linspace(0, duration, len(data["t"])), atol=1e-12, rtol=0),
                   f"{label}: output times")
        return data

    def save(self, suffix, columns):
        path = ROOT / "Figures/Data" / f"{self.name}-{suffix}.csv"
        np.savetxt(path, np.column_stack(list(columns.values())), delimiter=",",
                   header=",".join(columns), comments="", fmt="%.12g")
        print("Wrote", path.relative_to(ROOT))

    def finish(self):
        print(f"{self.name}: {'PASS' if self.passed else 'FAIL'}")
        return 0 if self.passed else 1


def maximum(values):
    return float(np.max(np.abs(values)))


def converges(errors, floor=1e-12):
    # Halving RK4 steps should reduce global error by about 16. Require only
    # a factor two, allowing higher terms and a floating-point error floor.
    return all(b <= max(a / 2, floor) for a, b in zip(errors, errors[1:]))
