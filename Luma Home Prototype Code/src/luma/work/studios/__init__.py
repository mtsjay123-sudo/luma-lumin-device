"""Luma's creation studios. Each one: what the brain fills in, the code that builds the real files, and
the checks a file must pass before it counts as done."""
from __future__ import annotations

from luma.work.studios.base import Result, Studio  # noqa: F401


def registry():
    from luma.work.studios import cad, code, data, docs, game, media, package, research, website
    studios = [research.Research(), data.AnalyzeData(), data.FinancialModel(), docs.Document(), docs.Deck(), website.Website(),
               code.Code(), game.Game(), cad.Model3D(), media.Graphics(), package.Package()]
    return {s.name: s for s in studios}
