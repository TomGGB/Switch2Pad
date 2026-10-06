import re

from switch2pad.i18n import LANGUAGES, STRINGS


def test_all_languages_have_the_same_keys():
    keys = set(STRINGS["en"])
    for lang in LANGUAGES:
        assert set(STRINGS[lang]) == keys, lang


def test_placeholders_match():
    for key, text in STRINGS["en"].items():
        ph = set(re.findall(r"{(\w+)}", text))
        for lang in LANGUAGES:
            assert set(re.findall(r"{(\w+)}", STRINGS[lang][key])) == ph, (lang, key)
