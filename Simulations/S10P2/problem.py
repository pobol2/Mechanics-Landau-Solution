# SPDX-License-Identifier: MIT
# Copyright (c) 2026 P.O. Bolduc. See LICENSE-CODE.
"""Section 10 P2: compare U and 4U, x_4U(t/2)=x_U(t)."""
from similarity import verify_similarity


def verify(exe, work):
    return verify_similarity("S10P2", exe, work)
