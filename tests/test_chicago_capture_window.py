from datetime import datetime, timezone

import pytest

from scripts.run_chicago_vertical_slice import validate_capture_window


def config() -> dict:
    return {
        "capture_window": {
            "not_before_utc": "2026-09-06T10:45:00Z",
            "not_after_utc": "2026-09-06T11:15:00Z",
        }
    }


def test_capture_window_accepts_registered_time() -> None:
    validate_capture_window(config(), datetime(2026, 9, 6, 11, tzinfo=timezone.utc))


def test_capture_window_rejects_early_run() -> None:
    with pytest.raises(RuntimeError, match="outside preregistered"):
        validate_capture_window(config(), datetime(2026, 9, 6, 10, tzinfo=timezone.utc))
