"""Synthesize ACTIVE inpatients — the four hero patients ARE the demo cohort.

The imported cohort is entirely historical (every encounter ``status=finished``),
so a disposition agent would have nothing live to act on. These four synthesized
patients are admitted right now (``encounter.status='in-progress'``,
``period_end=NULL``) with charts primed so disposition planning is a *retrieval*
problem: the signal lives both in typed columns (living_situation, active
conditions, pending labs, dispo assessments) and in realistic longitudinal
documentation (H&Ps with dispo-rich social histories, daily progress notes,
prior-admission discharge summaries, family-communication notes) for
ambient-style agents. Each hero also carries a per-patient Placer chat thread.

The cast, one storyline each:

- **hero-a-stroke** (Rosa Alvarez, 78F) — ischemic stroke, lives alone in a
  walk-up, daughter out of state: the SNF-placement path, gated on a pending
  COVID PCR.
- **hero-b-chf** (Daniel Okafor, 66M) — CHF exacerbation, suitable home and
  spouse who works days: home with home-health services.
- **hero-c-hospice** (Giulia Bianchi, 84F) — metastatic pancreatic cancer,
  DNR, comfort-focused: home hospice vs facility, hinging on caregiver nights.
- **hero-d-ambiguous** (Tom Nguyen, 71M) — pneumonia + COPD with an
  undocumented baseline: the disposition is unknowable until someone fills the
  social-history gap.

IDs and MRNs are fixed (``hero-a-stroke``, ``MRN90001``, ``enc-hero-a``, ...)
so demo/agent scripts can hardcode them.
"""

from __future__ import annotations

from sqlmodel import Session

from . import hero_a, hero_b, hero_c, hero_d


def seed_hero_patients(session: Session) -> int:
    """Create all hero patients. Returns the number of hero patients created."""
    builders = [hero_a.build, hero_b.build, hero_c.build, hero_d.build]
    for build in builders:
        build(session)
    return len(builders)
