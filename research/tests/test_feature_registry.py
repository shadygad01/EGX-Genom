import pytest

from agx_research.features.correlation import PAIRWISE_RETURN_CORRELATION, default_feature_registry
from agx_research.features.definition import FeatureDefinition
from agx_research.features.registry import FeatureRegistry


def test_default_registry_has_correlation_feature():
    registry = default_feature_registry()
    fetched = registry.get(PAIRWISE_RETURN_CORRELATION.id, PAIRWISE_RETURN_CORRELATION.version)
    assert fetched == PAIRWISE_RETURN_CORRELATION


def test_register_rejects_duplicate_id_and_version():
    registry = FeatureRegistry()
    definition = FeatureDefinition(id="foo", version=1, name="Foo", description="test")
    registry.register(definition)
    with pytest.raises(ValueError):
        registry.register(definition)


def test_get_unknown_feature_raises():
    registry = FeatureRegistry()
    with pytest.raises(KeyError):
        registry.get("does-not-exist", 1)


def test_latest_version_picks_highest():
    registry = FeatureRegistry()
    registry.register(FeatureDefinition(id="foo", version=1, name="Foo v1", description="test"))
    registry.register(FeatureDefinition(id="foo", version=2, name="Foo v2", description="test"))

    assert registry.latest_version("foo").version == 2
