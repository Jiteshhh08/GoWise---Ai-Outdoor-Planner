import unittest
from datetime import datetime, timezone

from app.engine.activities import ACTIVITY_RULES, classify_venue
from app.engine.scoring import (
    GeoFeature,
    angular_difference_degrees,
    bearing_degrees,
    score_candidate_time,
)


def feature(tags: dict[str, str], latitude: float = 19.1, longitude: float = 72.9) -> GeoFeature:
    return GeoFeature("way/1", tags, latitude, longitude, "https://www.openstreetmap.org/way/1")


class ActivityMatchingTests(unittest.TestCase):
    def test_all_ten_activities_have_tag_based_venue_match_rules(self) -> None:
        self.assertEqual(len(ACTIVITY_RULES), 10)
        for activity, rule in ACTIVITY_RULES.items():
            tags = {key: sorted(values)[0] for key, values in rule.tag_alternatives[0].items()}
            with self.subTest(activity=activity):
                self.assertTrue(classify_venue(activity, tags))

    def test_place_name_never_classifies_a_venue_without_matching_tags(self) -> None:
        self.assertFalse(classify_venue("golf", {"name": "Example Golf Course"}))
        self.assertFalse(classify_venue("tennis", {"name": "Outdoor Tennis Courts"}))


class ScoringTests(unittest.TestCase):
    def setUp(self) -> None:
        self.venue = feature({"leisure": "park", "name": "Mapped Park"})
        self.when = datetime(2026, 10, 25, 3, tzinfo=timezone.utc)

    def test_suitable_weather_scores_above_unsuitable_weather(self) -> None:
        comfortable = score_candidate_time(
            "running", self.venue, self.when,
            {"values": {"temperature_2m": 20, "precipitation_probability": 5, "wind_speed_10m": 8}},
            {"values": {"european_aqi": 15}}, [],
        )
        poor = score_candidate_time(
            "running", self.venue, self.when,
            {"values": {"temperature_2m": 44, "precipitation_probability": 85, "wind_speed_10m": 50}},
            {"values": {"european_aqi": 130}}, [],
        )

        self.assertGreater(comfortable.suitability_score, poor.suitability_score)
        self.assertLessEqual(comfortable.suitability_score, 100)
        self.assertGreaterEqual(poor.suitability_score, 0)

    def test_missing_data_reduces_coverage_and_stays_unavailable(self) -> None:
        result = score_candidate_time("running", self.venue, self.when, None, None, [])

        self.assertEqual(result.coverage, 0.25)
        self.assertIsNone(next(item for item in result.score_factors if item.name == "weather").score)
        self.assertIsNone(next(item for item in result.score_factors if item.name == "air_quality").score)
        self.assertTrue(any("Weather data is unavailable" in warning for warning in result.warnings))

    def test_context_distinguishes_road_proximity_proxy_and_mapped_green(self) -> None:
        context = [
            feature({"highway": "primary"}, 19.101, 72.9),
            feature({"landuse": "forest"}, 19.105, 72.9),
        ]
        result = score_candidate_time("running", self.venue, self.when, {"values": {"temperature_2m": 20}}, None, context)
        context_factor = next(item for item in result.score_factors if item.name == "geospatial_context")

        self.assertIsNotNone(context_factor.score)
        self.assertIn("proximity proxy", context_factor.value)
        self.assertIn("nearest_major_road_km", result.context_flags[0])

    def test_wind_from_sector_flags_nearby_mapped_industry_without_pollution_claim(self) -> None:
        source = feature({"landuse": "industrial"}, 19.11, 72.9)
        result = score_candidate_time(
            "running", self.venue, self.when,
            {"values": {"temperature_2m": 20, "wind_direction_10m": 359}},
            None, [source],
        )

        self.assertTrue(any("forecast wind-from sector" in warning and "not a pollution measurement" in warning for warning in result.warnings))

    def test_bearing_and_angular_difference_wrap_at_north(self) -> None:
        north_bearing = bearing_degrees(0, 0, 1, 0)

        self.assertAlmostEqual(north_bearing, 0, places=5)
        self.assertEqual(angular_difference_degrees(359, 1), 2)

    def test_mismatched_venue_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "does not match"):
            score_candidate_time("golf", self.venue, self.when, None, None, [])


if __name__ == "__main__":
    unittest.main()
