"""Semiotic class passes.

Each module owns one class of textual artefact (currency, percent,
date, time, …) and exports a single ``apply(text, lang)`` function.
``pipeline.py`` is the orchestrator that sequences them.
"""
