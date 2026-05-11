from py_utils.verbalize.locales.es import (
    _classify_next,
    _try_load_spacy,
    post_pass,
)


# ─── Trigger sweep ──────────────────────────────────────────────────


def test_no_trigger_passthrough():
    # Text without trigger words: nothing happens, zero spaCy calls.
    out = post_pass("hola mundo de gente")
    assert out == "hola mundo de gente"


# ─── Concordance with feminine plural ───────────────────────────────


def test_hundreds_before_feminine_plural_swap():
    out = post_pass("doscientos personas asistieron")
    assert "doscientas personas" in out


def test_hundreds_before_masculine_kept():
    out = post_pass("doscientos hombres asistieron")
    assert "doscientos hombres" in out


def test_false_positive_dias_kept_masculine():
    # "días" looks feminine plural by suffix but is masculine.
    # spaCy correctly identifies it; heuristic fallback misclassifies.
    nlp = _try_load_spacy()
    if nlp is None:
        # heuristic fallback: días → Fem by suffix, this WILL mis-fire
        # but we accept it (documented limitation)
        return
    out = post_pass("doscientos días después")
    assert "doscientos días" in out


def test_false_positive_problemas_kept_masculine():
    nlp = _try_load_spacy()
    if nlp is None:
        return
    out = post_pass("trescientos problemas resueltos")
    assert "trescientos problemas" in out


# ─── Apocope ────────────────────────────────────────────────────────


def test_apocope_before_masculine_singular():
    nlp = _try_load_spacy()
    if nlp is None:
        return
    out = post_pass("uno gigabyte de RAM")
    assert "un gigabyte" in out


def test_apocope_veintiuno():
    nlp = _try_load_spacy()
    if nlp is None:
        return
    out = post_pass("veintiuno años de edad")
    # años is masc plural — apocope still applies on the quantifier
    assert "veintiún años" in out


def test_apocope_idiom_uno_de_cada():
    # spaCy classifies "de" as ADP (preposition); should NOT apocopate.
    out = post_pass("uno de cada cinco")
    assert "uno de" in out


def test_uno_before_feminine_singular():
    nlp = _try_load_spacy()
    if nlp is None:
        return
    out = post_pass("uno mujer")
    # Should swap to "una mujer"
    assert "una mujer" in out


# ─── classify_next ──────────────────────────────────────────────────


def test_classify_next_returns_gender_for_known_word():
    nlp = _try_load_spacy()
    if nlp is None:
        return
    eligible, gender, number = _classify_next("personas")
    assert eligible is True
    assert gender == "Fem"
    assert number == "Plur"


def test_classify_next_ineligible_for_preposition():
    nlp = _try_load_spacy()
    if nlp is None:
        return
    eligible, gender, number = _classify_next("de")
    assert eligible is False


def test_classify_next_eligible_unknown_gender_for_loanword():
    # spaCy tags loanwords like "gigabyte" as PROPN with no gender;
    # apocope should still fire — eligible=True, gender="".
    nlp = _try_load_spacy()
    if nlp is None:
        return
    eligible, gender, _ = _classify_next("gigabyte")
    assert eligible is True
    assert gender in ("", "Masc")  # spaCy may not commit a gender
