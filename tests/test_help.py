"""The manual: both languages have the same sections, links resolve, findings are covered."""

import re

from advastro import help as manual
from advastro.rate import judge


def ids(lang):
    return [s.id for ch in manual.chapters(lang) for s in ch.sections]


def test_languages_have_the_same_sections():
    assert set(manual.languages()) >= {"en", "sv"}
    assert ids("en") == ids("sv")
    assert len(ids("en")) == len(set(ids("en")))           # ids are unique


def test_every_help_link_resolves():
    known = set(ids("en"))
    for lang in manual.languages():
        for ch in manual.chapters(lang):
            for link in re.findall(r"\(help:([\w.]+)\)", ch.markdown):
                assert link in known, (lang, ch.title, link)


def test_every_finding_has_an_entry():
    import inspect

    source = inspect.getsource(judge) + inspect.getsource(
        __import__("advastro.rate.sky", fromlist=["x"]))
    found = set(re.findall(r'(?:add|Finding)\("([a-z_]+)"', source))
    assert len(found) > 40
    known = set(ids("en"))
    missing = {f for f in found if manual.finding_topic(f) not in known}
    assert not missing, missing


def test_locate_falls_back_to_parents_and_english():
    ch, sec = manual.locate("settings.compare.something")
    assert sec.id == "settings.compare"
    assert manual.locate("rate.verdict", "xx")[1].id == "rate.verdict"


def test_search_finds_sections():
    hits = [s.id for _, s in manual.search("walking noise")]
    assert "finding.walking_noise" in hits
    assert manual.search("   ") == []
