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
  authoritative source. `EGX_MOVABLE_HOLIDAYS_PLACEHOLDER` follows the
  same convention as `EGX30_UNIVERSE_PLACEHOLDER`: real structure,
  placeholder content, replace before real research depends on it.

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

# Placeholder per-year table for movable (lunar / Coptic-Easter) holidays.
# NOT authoritative — populate from official EGX announcements before any
# research conclusion depends on these dates.
EGX_MOVABLE_HOLIDAYS_PLACEHOLDER: dict[date, str] = {
    date(2026, 3, 20): "Eid al-Fitr (placeholder date)",
    date(2026, 5, 27): "Eid al-Adha (placeholder date)",
    date(2026, 6, 17): "Islamic New Year (placeholder date)",
    date(2026, 8, 26): "Prophet's Birthday (placeholder date)",
    date(2026, 4, 13): "Sham El Nessim (placeholder date)",
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
            EGX_MOVABLE_HOLIDAYS_PLACEHOLDER if movable_holidays is None else movable_holidays
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
