import pytest

from scripts.select_us_nbm_model_ready_pilot import evenly_spaced_indices


def test_evenly_spaced_indices_include_boundaries_and_are_unique():
    indices = evenly_spaced_indices(100, 20)
    assert indices[0] == 0
    assert indices[-1] == 99
    assert len(indices) == len(set(indices)) == 20


def test_evenly_spaced_indices_reject_insufficient_population():
    with pytest.raises(ValueError, match="not enough"):
        evenly_spaced_indices(19, 20)
