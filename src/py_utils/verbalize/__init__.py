"""Public API for ``py_utils.verbalize``.

See ``CLAUDE.md`` in this directory for design rationale, the NeMo
comparison, and the per-class coverage table.

Quick start::

    from py_utils.verbalize import normalize

    normalize("Visita www.example.com el 25/6/2026", lang="es")
    # → "Visita uve doble uve doble uve doble punto example punto com el
    #    veinticinco de junio de dos mil veintiséis"
"""

from .pipeline import normalize

__all__ = ["normalize"]
