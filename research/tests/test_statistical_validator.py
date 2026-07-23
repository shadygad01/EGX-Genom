from agx_research.hypotheses.experiment import ExperimentResult
from agx_research.validation.statistical import SignificanceThresholdValidator


def test_passes_below_alpha():
    validator = SignificanceThresholdValidator(alpha=0.05)
    result = validator.validate(ExperimentResult(statistic=2.5, p_value=0.01, sample_size=100))
    assert result.passed


def test_fails_above_alpha():
    validator = SignificanceThresholdValidator(alpha=0.05)
    result = validator.validate(ExperimentResult(statistic=0.5, p_value=0.3, sample_size=100))
    assert not result.passed
