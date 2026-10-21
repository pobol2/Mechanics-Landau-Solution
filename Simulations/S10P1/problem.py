# SPDX-License-Identifier: MIT
# Copyright (c) 2026 P.O. Bolduc. See LICENSE-CODE.
"""Section 10 P1: compare m and 4m, x_4m(2t)=x_m(t)."""
from similarity import verify_similarity


def verify(exe, work):
    return verify_similarity("S10P1", exe, work)
