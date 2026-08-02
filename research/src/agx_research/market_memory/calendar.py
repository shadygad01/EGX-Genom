"""The EGX trading calendar: weekends plus public holidays.

Two holiday classes, treated differently on purpose:

- Fixed-date national holidays (Coptic Christmas, Sinai Liberation Day,
  Labour Day, June 30 Revolution, July 23 Revolution Day, Armed Forces
  Day, Coptic Christmas, January 25) recur on the same Gregorian date and
  are encoded as rules.
- Lunar-calendar holidays (Eid al-Fitr, Eid al-Adha, Islamic New Year,
  Prophet's Birthday) and Sham El Nessim (Coptic-Easter-linked) move each
  year. Approximating them algorithmically would be fabricating calendar
  data — observed EGX closures also vary with official announcements — so
  they live in an explicit per-year table that must be maintained from an
  authoritative source, never guessed. `EGX_MOVABLE_HOLIDAYS_2026` holds
  real, cited 2026 dates (see its own comment for sources) — replace this
  module's approach entirely with a real collected feed once one exists;
  until then, a new year's dates must be added the same way: found and
  cited, never estimated.

`TradingCalendar` is an interface (like `UniverseProvider`) so a real
exchange-published calendar feed can replace the static one without
touching any caller.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

# EGX's trading week is Sunday-Thursday; Friday/Saturday are the weekend.
_EGX_WEEKEND_WEEKDAYS = {4, 5}  # date.weekday(): Friday=4, Saturday=5

# (month, day) -> holiday name. Recur every year.
EGX_FIXED_HOLIDAYS: dict[tuple[int, int], str] = {
    (1, 7): "Coptic Christmas",
    (1, 25): "January 25 Revolution Day / Police Day",
    (4, 25): "Sinai Liberation Day",
    (5, 1): "Labour Day",
    (6, 30): "June 30 Revolution Day",
    (7, 23): "July 23 Revolution Day",
    (10, 6): "Armed Forces Day",
}

# Movable (lunar / Coptic-Easter-linked) EGX holidays for 2026, replacing an
# earlier placeholder table (2026-08-02 review) with real, cited dates found
# via live web search -- not algorithmically estimated:
#
# - Eid al-Fitr: EGX suspended trading Thu 2026-03-19 through Mon 2026-03-23,
#   resuming Tue 2026-03-24 ("EGX declares five-day holiday for Eid Al-Fitr",
#   Arab Finance). Fri 2026-03-20/Sat 2026-03-21 are already the regular
#   weekend, so only the three genuinely-additional closed days are listed.
# - Eid al-Adha: EGX suspended trading Tue 2026-05-26 through Sun 2026-05-31,
#   resuming Mon 2026-06-01 ("EGX announces Eid Al Adha holiday from 26 May
#   until 31 May", Amwal Al Ghad -- itself one of this platform's own
#   IMPLEMENTED sources). Fri 2026-05-29/Sat 2026-05-30 are already the
#   regular weekend.
# - Islamic New Year (1448 AH): Thursday 2026-06-18, a government-declared
#   paid public holiday (Egyptian PM Mostafa Madbouly; EgyptToday, Egypt's
#   State Information Service sis.gov.eg).
# - Prophet's Birthday (Mawlid al-Nabi): Tuesday 2026-08-25 (multiple
#   corroborating sources: Wego, National Today, QPPStudio), one day earlier
#   than the prior placeholder's 2026-08-26 -- exactly the kind of drift this
#   table's own docstring warned an uncited guess could produce, and this
#   date sits only ~3 weeks after this correction, squarely inside the
#   platform's near-term MICRO/SWING decision window.
# - Sham El Nessim: Monday 2026-04-13, the day after Coptic Orthodox Easter
#   (2026-04-12) -- matches the prior placeholder's date exactly, now cited
#   (Time.now, The Middle East Insider).
#
# A future year's dates must be added the same way -- found and cited from a
# real announcement, never estimated -- and this whole mechanism should be
# replaced by a real collected feed the moment one exists (see this file's
# module docstring).
EGX_MOVABLE_HOLIDAYS_2026: dict[date, str] = {
    date(2026, 3, 19): "Eid al-Fitr",
    date(2026, 3, 22): "Eid al-Fitr",
    date(2026, 3, 23): "Eid al-Fitr",
    date(2026, 5, 26): "Eid al-Adha",
    date(2026, 5, 27): "Eid al-Adha",
    date(2026, 5, 28): "Eid al-Adha",
    date(2026, 5, 31): "Eid al-Adha",
    date(2026, 6, 18): "Islamic New Year",
    date(2026, 8, 25): "Prophet's Birthday (Mawlid al-Nabi)",
    date(2026, 4, 13): "Sham El Nessim",
}


class TradingCalendar(ABC):
    @abstractmethod
    def is_trading_day(self, as_of: date) -> bool: ...

    @abstractmethod
    def holiday_name(self, as_of: date) -> str | None:
        """The holiday observed on `as_of`, or None if it isn't a holiday."""


class StaticEGXCalendar(TradingCalendar):
    def __init__(self, movable_holidays: dict[date, str] | None = None):
        self._movable = dict(
            EGX_MOVABLE_HOLIDAYS_2026 if movable_holidays is None else movable_holidays
        )

    def holiday_name(self, as_of: date) -> str | None:
        fixed = EGX_FIXED_HOLIDAYS.get((as_of.month, as_of.day))
        if fixed is not None:
            return fixed
        return self._movable.get(as_of)

    def is_trading_day(self, as_of: date) -> bool:
        if as_of.weekday() in _EGX_WEEKEND_WEEKDAYS:
            return False
        return self.holiday_name(as_of) is None
