import unittest

from weather_quant.ingestion.closed_market_audit import (
    build_closed_audit,
    classify_closed_event,
    select_stratified_sample,
)


def event(event_id, *, source="https://example/KAAA", automatic=True, closed="2026-01-02T00:00:00Z", uma="resolved", condition="c"):
    return {
        "id": str(event_id),
        "title": f"Highest temperature in Test on January {event_id}?",
        "slug": f"test-{event_id}",
        "endDate": "2026-01-01T12:00:00Z",
        "closedTime": closed,
        "resolutionSource": source,
        "automaticallyResolved": automatic,
        "markets": [{
            "id": f"m-{event_id}", "conditionId": condition,
            "outcomes": '["Yes","No"]', "clobTokenIds": '["1","2"]',
            "outcomePrices": '["1","0"]', "groupItemTitle": "10 or below",
            "umaResolutionStatus": uma,
        }],
    }


class ClosedMarketAuditTests(unittest.TestCase):
    def test_classifies_overlapping_event_and_market_anomalies(self):
        record = classify_closed_event(
            event(1, source=None, automatic=False, closed=None, uma=None, condition=None), "abc"
        )
        self.assertEqual(
            record["cohorts"],
            [
                "EVENT_MISSING_CLOSED_TIME",
                "EVENT_NOT_AUTOMATICALLY_RESOLVED",
                "MARKET_IDENTIFIER_INCOMPLETE",
                "MARKET_NOT_UMA_RESOLVED",
                "NO_EVENT_RESOLUTION_SOURCE",
            ],
        )

    def test_audit_reports_overlap_without_double_counting_events(self):
        records = [
            classify_closed_event(event(1), "a"),
            classify_closed_event(event(2, source=None, automatic=False), "b"),
        ]
        audit = build_closed_audit(records)
        self.assertEqual(audit["event_count"], 2)
        self.assertEqual(audit["anomalous_event_count"], 1)
        self.assertEqual(audit["cohort_event_counts"]["NO_EVENT_RESOLUTION_SOURCE"], 1)
        self.assertEqual(audit["cohort_market_counts"]["MARKET_NOT_UMA_RESOLVED"], 0)

    def test_sample_is_deterministic_unique_and_exact_size(self):
        records = [classify_closed_event(event(i, source=None if i < 5 else "x"), str(i)) for i in range(1, 30)]
        first, metadata = select_stratified_sample(records, sample_size=10, anomaly_per_cohort=3, clean_target=5)
        second, _ = select_stratified_sample(list(reversed(records)), sample_size=10, anomaly_per_cohort=3, clean_target=5)
        self.assertEqual([x["event_id"] for x in first], [x["event_id"] for x in second])
        self.assertEqual(len({x["event_id"] for x in first}), 10)
        self.assertEqual(metadata["sample_size"], 10)


if __name__ == "__main__":
    unittest.main()
