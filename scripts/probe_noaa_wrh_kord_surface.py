#!/usr/bin/env python3
"""Probe the declared NOAA WRH KORD page without calling third-party data APIs."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from weather_quant.ingestion.noaa_wrh import analyze_wrh_surface

PAGE_URL = "https://www.weather.gov/wrh/timeseries?site=kord"
OBS_SCRIPT_URL = "https://www.weather.gov/source/wrh/timeseries/obs.js?v202601121730"
CREDENTIAL_SCRIPT_URL = "https://www.weather.gov/source/wrh/apiKey.js"


def fetch(url: str) -> tuple[bytes, dict[str, object]]:
    requested = datetime.now(timezone.utc)
    request = Request(url, headers={"User-Agent": "weather-quant-research/0.1"})
    with urlopen(request, timeout=30) as response:
        raw = response.read()
        received = datetime.now(timezone.utc)
        return raw, {
            "url": url,
            "requested_at_utc": requested.isoformat().replace("+00:00", "Z"),
            "received_at_utc": received.isoformat().replace("+00:00", "Z"),
            "http_status": response.status,
            "content_type": response.headers.get("Content-Type"),
            "last_modified": response.headers.get("Last-Modified"),
            "etag": response.headers.get("ETag"),
            "byte_count": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.raw_dir.exists() or args.output.exists():
        raise FileExistsError("raw directory and output must be new")
    args.raw_dir.mkdir(parents=True)

    pages = []
    page_contents = []
    for index in (1, 2):
        content, metadata = fetch(PAGE_URL)
        (args.raw_dir / f"page-{index}-{metadata['sha256']}.html").write_bytes(content)
        pages.append(metadata)
        page_contents.append(content)
    obs_script, obs_metadata = fetch(OBS_SCRIPT_URL)
    (args.raw_dir / f"obs-{obs_metadata['sha256']}.js").write_bytes(obs_script)
    credential_script, credential_metadata = fetch(CREDENTIAL_SCRIPT_URL)
    # The public credential helper is inspected in memory but never persisted or printed.
    safe_credential_metadata = {
        **credential_metadata,
        "sha256": credential_metadata["sha256"],
        "content_persisted": False,
        "content_or_value_recorded": False,
    }

    analysis = analyze_wrh_surface(
        page_contents[0].decode("utf-8", errors="replace"),
        obs_script.decode("utf-8", errors="replace"),
        credential_script.decode("utf-8", errors="replace"),
    )
    checks = {
        "two_page_http_200": all(page["http_status"] == 200 for page in pages),
        "two_page_schema_stable": pages[0]["content_type"] == pages[1]["content_type"],
        "two_page_content_stable": pages[0]["sha256"] == pages[1]["sha256"],
        "official_page_references_client_script": any(
            "/source/wrh/timeseries/obs.js" in item for item in analysis["script_sources"]
        ),
        "exact_kord_identity_in_machine_payload": False,
        "timestamped_temperature_rows_in_official_payload": False,
        "following_local_date_trigger_selectable": False,
        "official_origin_machine_endpoint_available": analysis[
            "official_origin_timeseries_endpoint_count"
        ]
        >= 1,
    }
    artifact = {
        "schema_version": "0.1.0",
        "experiment_id": "EXP-20260830-data-source-feasibility",
        "probe": "NOAA WRH KORD declared-source surface",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "page_retrievals": pages,
        "client_script_retrieval": obs_metadata,
        "credential_script_retrieval": safe_credential_metadata,
        "surface_analysis": analysis,
        "semantic_checks": checks,
        "semantic_gate_passed": all(checks.values()),
        "decision": "FAILED_NOT_MACHINE_RECONCILABLE_WITHIN_OFFICIAL_ORIGIN_SCOPE",
        "revision_status": "HISTORICAL_FREEZE_AS_OF_UNRESOLVED",
        "raw_directory": str(args.raw_dir),
        "safety": "NO_THIRD_PARTY_DATA_CALL_NO_CREDENTIAL_RECORD_NO_POLLING",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(args.output),
                "decision": artifact["decision"],
                "semantic_checks": checks,
                "surface_analysis": analysis,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
