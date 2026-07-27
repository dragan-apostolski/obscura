"""Fixes for PyMuPDF extraction artifacts on PDFs with ligature-heavy embedded fonts.

Root cause: ligature glyphs (fi/ff/fl) have unusual advance widths that trip
PyMuPDF's word-boundary heuristic, inserting a stray space right after them
("flash" -> "fl ash"). The ligature itself decodes correctly — only the
following space is spurious. Dictionary-gated so real word pairs (e.g. "off
the") are never merged.
"""
import re
import unicodedata

from spellchecker import SpellChecker

_spell = SpellChecker()
_LIGATURE_BREAK = re.compile(r"(\S*(?:fi|ff|fl)) (\S+)")
_LIGATURE_FREQ_THRESHOLD = 1e-6   # below this, treat the left token as a bare fragment, not a word

_HYPHEN_LINEBREAK = re.compile(r"(?<=[a-z])-\n(?=[a-z])")


def _rejoin_ligature_break(m: re.Match) -> str:
    left, right = m.group(1), m.group(2)
    core_l = re.sub(r"[^a-zA-Z]", "", left)
    core_r = re.sub(r"[^a-zA-Z]", "", right)
    if not core_l or not core_r:
        return m.group(0)
    left_is_real_word = _spell.word_usage_frequency(core_l.lower()) >= _LIGATURE_FREQ_THRESHOLD
    merged_is_real_word = (core_l + core_r).lower() in _spell
    if not left_is_real_word and merged_is_real_word:
        return left + right
    return m.group(0)


def clean_extracted_text(text: str) -> str:
    """Rejoin hyphenated line-break words and ligature-broken words."""
    text = unicodedata.normalize("NFKC", text)   # raw ligature glyphs (e.g. "ﬁ") -> "fi"
    text = _HYPHEN_LINEBREAK.sub("", text)
    return _LIGATURE_BREAK.sub(_rejoin_ligature_break, text)
