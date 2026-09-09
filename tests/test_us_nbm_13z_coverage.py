from scripts.probe_us_nbm_13z_coverage import run_date


def test_13z_run_date_is_prior_day():
    assert run_date("2026-01-15") == "20260114"
