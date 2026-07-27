"""Resolve free text (a news headline) to the ticker(s) it actually refers
to, using only real, already-catalogued company data.

Reuses `discovery.engine.significant_tokens()`'s exact token-normalization
discipline (already shared between `discover_company_directory_links` and
`discovery.wikidata_lookup`) for company-name matching: a text mention
must contain every one of a company display name's significant tokens
(common corporate suffixes like "Company"/"Group"/"Holding"/"Egypt"
excluded), not merely overlap with one.

Ticker matching is a real word/token match against `text`, not a
substring check -- this closes the "VLMR matches inside VLMRA" false
positive that `RssNewsCollector`/`GdeltDocCollector`'s prior
`ticker.lower() in title.lower()` check was exposed to (named explicitly
in the project owner's own completion plan).

Deliberately English-only and ticker/company-name-only: no Arabic alias
list is included here because no verified Arabic-language source for
EGX30/EGX70 constituent names exists in this codebase yet
(`research/data/universe/EGX30.csv`/`EGX70.csv` are English/ISIN only,
each row's `source_url` pointing at EGX's own English listing page).
Inventing Arabic transliterations from training-data recall would be
exactly the kind of fabrication this program's rules forbid -- a wrong
alias risks a *wrong* ticker match, which is worse than a missed one. See
TD-36.
"""

from __future__ import annotations

import re

from agx_research.discovery.engine import significant_tokens

_WORD_PATTERN = re.compile(r"[a-z0-9]+")


def _raw_tokens(text: str) -> set[str]:
    return set(_WORD_PATTERN.findall(text.lower()))


def resolve_ticker_mentions(text: str, companies: dict[str, str]) -> list[str]:
    """Return every ticker in `companies` (ticker -> display name) that
    `text` genuinely mentions: either the ticker code appears as its own
    word/token (not merely a substring of a longer token), or every
    significant token of the company's display name appears in `text`.

    A company with an empty/unknown display name is only matched by its
    ticker code -- an empty name's "every token" requirement would
    otherwise vacuously match everything, which is exactly the kind of
    false positive this function exists to avoid.
    """
    raw_tokens = _raw_tokens(text)
    text_name_tokens = significant_tokens(text)
    matched: list[str] = []
    for ticker, name in companies.items():
        if ticker.lower() in raw_tokens:
            matched.append(ticker)
            continue
        tokens = significant_tokens(name)
        if tokens and tokens.issubset(text_name_tokens):
            matched.append(ticker)
    return matched
