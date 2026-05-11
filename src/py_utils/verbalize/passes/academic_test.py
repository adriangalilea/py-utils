from py_utils.verbalize.passes.academic import (
    expand_citations,
    expand_doi,
    expand_footnotes,
    expand_isbn,
)


def test_doi_spanish():
    out = expand_doi("Ver 10.1234/abcd para detalles", "spanish")
    assert "D O I" in out
    assert "barra" in out
    assert "abcd" in out


def test_doi_english():
    out = expand_doi("See 10.1234/abcd", "english")
    assert "D O I" in out
    assert "slash" in out


def test_isbn_13():
    out = expand_isbn("978-3-16-148410-0", "spanish")
    assert "I S B N" in out
    assert "nueve siete ocho" in out


def test_isbn_with_prefix():
    out = expand_isbn("ISBN 978-3-16-148410-0", "spanish")
    assert "I S B N" in out


def test_citation_page():
    out = expand_citations("Smith 2024, p. 5", "spanish")
    assert "página 5" in out


def test_citation_pages():
    out = expand_citations("Smith 2024, pp. 5-10", "english")
    assert "pages 5-10" in out


def test_footnote_superscript():
    out = expand_footnotes("Esto es importante¹", "spanish")
    assert "nota uno" in out


def test_footnote_multi_digit():
    out = expand_footnotes("ver¹²", "spanish")
    # treated as 12 (not 1, 2 separately)
    assert "doce" in out


def test_doi_unsupported_lang_noop():
    assert expand_doi("10.1234/abcd", "german") == "10.1234/abcd"
