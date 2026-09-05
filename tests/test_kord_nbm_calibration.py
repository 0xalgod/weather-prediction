from scripts.run_kord_nbm_calibration import inclusive_grid, select_candidate


def test_inclusive_grid_contains_both_endpoints() -> None:
    assert inclusive_grid(-0.5, 0.5, 0.25) == [-0.5, -0.25, 0.0, 0.25, 0.5]


def test_candidate_tie_break_prefers_no_adjustment() -> None:
    candidates = [
        {"shift_f": -1.0, "spread_scale": 1.0},
        {"shift_f": 0.0, "spread_scale": 1.0},
        {"shift_f": 0.0, "spread_scale": 1.5},
    ]
    assert select_candidate(candidates, [3.0, 3.0, 3.0], 3) == 1
