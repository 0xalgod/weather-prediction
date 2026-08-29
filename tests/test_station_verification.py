import unittest

from weather_quant.normalization.station_verification import point_in_polygon, timezone_at_point


class StationVerificationTests(unittest.TestCase):
    def test_polygon_hole_is_excluded(self):
        polygon = [
            [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]],
            [[4, 4], [6, 4], [6, 6], [4, 6], [4, 4]],
        ]
        self.assertTrue(point_in_polygon(2, 2, polygon))
        self.assertFalse(point_in_polygon(5, 5, polygon))

    def test_timezone_lookup_requires_one_match(self):
        features = [{"properties": {"tzid": "Etc/Test"}, "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]]}}]
        self.assertEqual(timezone_at_point(2, 2, features), "Etc/Test")
        with self.assertRaisesRegex(ValueError, "expected one"):
            timezone_at_point(20, 20, features)


if __name__ == "__main__":
    unittest.main()
