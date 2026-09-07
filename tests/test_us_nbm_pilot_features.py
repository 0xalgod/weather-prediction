from scripts.collect_us_nbm_pilot_features import run_date_for_target


def test_run_date_is_prior_calendar_date():
    assert run_date_for_target("2026-03-24") == "20260323"
