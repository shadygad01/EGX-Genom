"""Shared HTML-to-visible-text helper for bespoke per-company IR collectors.

Strips script/style content and tags, leaving plain text for a narrow,
explicit-label regex to search -- never used to guess a value from
unlabelled prose.
"""

from __future__ import annotations

import re
from html import unescape

_TAG = re.compile(r"<[^>]+>")
_SPACE = re.compile(r"\s+")
_SCRIPT = re.compile(r"<script[\s\S]*?</script>", re.IGNORECASE)
_STYLE = re.compile(r"<style[\s\S]*?</style>", re.IGNORECASE)


def visible_text(html: str) -> str:
    without_scripts = _SCRIPT.sub(" ", html)
    without_styles = _STYLE.sub(" ", without_scripts)
    return _SPACE.sub(" ", unescape(_TAG.sub(" ", without_styles))).strip()
