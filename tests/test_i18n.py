from cuselect.i18n import LANGUAGES, translate

def test_four_languages():
    assert set(LANGUAGES) == {"en", "de", "es", "fr"}

def test_german_translation():
    assert translate("catalyst.title", "de") == "Katalysator-Explorer"

def test_english_fallback():
    assert translate("missing.key", "de") == "missing.key"

def test_unknown_language():
    assert translate("catalyst.title", "xx") == "Catalyst Explorer"
