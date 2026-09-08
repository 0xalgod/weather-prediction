from scripts.diagnose_us_nbm_failure import signed_interval_distance


def test_signed_interval_distance_handles_finite_and_open_tails():
    assert signed_interval_distance(5, 6, 7) == -1
    assert signed_interval_distance(8, 6, 7) == 1
    assert signed_interval_distance(6.5, 6, 7) == 0
    assert signed_interval_distance(5, None, 7) == 0
    assert signed_interval_distance(8, 6, None) == 0
