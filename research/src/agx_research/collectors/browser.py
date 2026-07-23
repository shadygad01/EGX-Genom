"""BrowserAutomationCollector: the honest stub for the one collector type
this platform cannot yet deliver for real.

Every other collector type in the charter's list (RSS, REST, HTML, PDF,
CSV, Excel, XML, JSON, Filesystem, Archive Replay) is either implemented or
a generic, tested framework piece waiting on a verified endpoint. Browser
automation is different: it requires a concrete target site whose structure
justifies scripted interaction (login walls, JS-rendered content, pagination
that no plain HTTP fetch can follow) *and* a documented case that the site's
ToS permits it -- inventing one now would mean guessing both a site and a
legal conclusion. Per this codebase's own rule (see `ExperimentFactory`,
`review.reviewers`, `AdversarialScientist`), an unimplemented capability
raises `NotImplementedError` rather than faking a plausible-looking result.

When a concrete, ToS-cleared browser-automation target exists, a subclass
implements `fetch()`/`parse()` the same as any other `Collector` -- this
base class only declares the contract and documents why it's empty.
"""

from __future__ import annotations

from agx_research.collectors.base import CollectionBatch, Collector
from agx_research.collectors.raw import RawDocument


class BrowserAutomationCollector(Collector):
    def fetch(self) -> list[RawDocument]:
        raise NotImplementedError(
            f"{self.spec.id}: no browser-automation target has been verified and "
            "ToS-cleared yet. See docs/DATA_ACQUISITION.md's TOS_REVIEW policy -- "
            "ambiguity blocks collection, it does not get bypassed with automation."
        )

    def parse(self, document: RawDocument) -> CollectionBatch:
        raise NotImplementedError(
            f"{self.spec.id}: no browser-automation collector is implemented."
        )
