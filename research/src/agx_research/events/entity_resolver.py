"""Resolves raw mentions (tickers, company names, macro series ids) to
canonical EntityRefs.

Real, mechanical matching against `universe.UniverseProvider` as the source
of truth for company identity: exact ticker, then case-insensitive
company-name containment, then known macro series ids, falling back to
`EntityKind.UNKNOWN` rather than guessing. This is not a general NLP
entity-linking system — resolving free-text mentions from unstructured
news bodies needs real unstructured data this scaffold doesn't have yet
(see `docs/EVENT_PLATFORM_DESIGN.md`).
"""

from __future__ import annotations

from datetime import date

from agx_research.events.entity import EntityKind, EntityRef
from agx_research.universe.provider import UniverseProvider
from agx_research.universe.sector import SectorProvider


class EntityResolver:
    def __init__(
        self,
        universe_provider: UniverseProvider,
        sector_provider: SectorProvider | None = None,
        *,
        as_of: date,
        known_macro_series_ids: list[str] | None = None,
    ):
        self._constituents = universe_provider.constituents(as_of)
        self._sector_provider = sector_provider
        self._as_of = as_of
        self._known_macro_series_ids = set(known_macro_series_ids or [])
        self._name_to_ticker = {name.lower(): ticker for ticker, name in self._constituents.items()}

    def resolve(self, mention: str) -> EntityRef:
        if mention in self._constituents:
            return EntityRef(
                kind=EntityKind.COMPANY,
                canonical_id=mention,
                display_name=self._constituents[mention],
                raw_mention=mention,
            )

        lowered = mention.lower()
        if lowered in self._name_to_ticker:
            ticker = self._name_to_ticker[lowered]
            return EntityRef(
                kind=EntityKind.COMPANY,
                canonical_id=ticker,
                display_name=self._constituents[ticker],
                raw_mention=mention,
            )
        for name_lower, ticker in self._name_to_ticker.items():
            if name_lower and (name_lower in lowered or lowered in name_lower):
                return EntityRef(
                    kind=EntityKind.COMPANY,
                    canonical_id=ticker,
                    display_name=self._constituents[ticker],
                    raw_mention=mention,
                )

        if mention in self._known_macro_series_ids:
            return EntityRef(kind=EntityKind.MACRO_SERIES, canonical_id=mention, raw_mention=mention)

        return EntityRef(kind=EntityKind.UNKNOWN, canonical_id=mention, raw_mention=mention)

    def resolve_many(self, mentions: list[str]) -> list[EntityRef]:
        return [self.resolve(mention) for mention in mentions]

    def sector_of(self, entity: EntityRef) -> str | None:
        if self._sector_provider is None or entity.kind != EntityKind.COMPANY:
            return None
        return self._sector_provider.sector_of(entity.canonical_id, self._as_of)
