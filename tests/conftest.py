"""Shared test configuration.

Hypothesis profiles are mandatory, not decorative (RULES §3.2): without them the fast
suite is flaky and nobody trusts it. Pick one with `HYPOTHESIS_PROFILE`:

    dev      25 examples   gate B, the per-batch hook.  Default.
    gate    100 examples   gate C, end of turn.
    nightly 1000 examples  the nightly run.
"""

from __future__ import annotations

import os

from hypothesis import HealthCheck, settings

settings.register_profile("dev", max_examples=25, deadline=None)
settings.register_profile("gate", max_examples=100, deadline=None)
settings.register_profile(
    "nightly",
    max_examples=1000,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "dev"))
