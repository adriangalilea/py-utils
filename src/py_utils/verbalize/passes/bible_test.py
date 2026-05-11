from py_utils.verbalize.passes.bible import expand_bible_refs


def test_single_verse_spanish():
    out = expand_bible_refs("Génesis 1:1", "spanish")
    assert out == "Génesis, capítulo uno, versículo uno"


def test_verse_range_spanish():
    out = expand_bible_refs("Génesis 1:1-5", "spanish")
    assert "Génesis, capítulo uno, versículos uno al cinco" in out


def test_numbered_book_spanish():
    # "1 Corintios 13:4-7" — ordinal-prefixed book name.
    out = expand_bible_refs("1 Corintios 13:4-7", "spanish")
    assert "1 Corintios, capítulo trece, versículos cuatro al siete" in out


def test_single_verse_english():
    out = expand_bible_refs("Genesis 1:1", "english")
    assert out == "Genesis chapter one, verse one"


def test_verse_range_english():
    out = expand_bible_refs("John 3:16-17", "english")
    assert "John chapter three, verses sixteen through seventeen" in out


def test_psalm_with_long_chapter_num():
    # Psalms / Salmos go up to 150
    out = expand_bible_refs("Salmo 119:1", "spanish")
    assert "ciento diecinueve" in out


def test_unknown_book_passthrough():
    # Not in our list — leave alone
    out = expand_bible_refs("Atlantis 1:1", "spanish")
    assert out == "Atlantis 1:1"


def test_unsupported_lang_noop():
    out = expand_bible_refs("Génesis 1:1", "german")
    assert out == "Génesis 1:1"


def test_no_match_on_time():
    # 15:30 is a time, not a bible ref (no book name precedes)
    out = expand_bible_refs("a las 15:30 nos vemos", "spanish")
    assert "15:30" in out
