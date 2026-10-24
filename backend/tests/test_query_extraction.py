import asyncio
import unittest
from datetime import datetime, timezone

from app.model.query_extraction import (
    QueryClarification,
    QueryExtractionError,
    QueryExtractor,
    _canonical_activity,
)


class FakeModel:
    def __init__(self, response: str) -> None:
        self.response = response
        self.messages = []

    async def generate(self, messages, max_new_tokens=None):
        self.messages = messages
        return self.response


class QueryExtractionTests(unittest.TestCase):
    def test_all_ten_activity_names_and_synonyms_map_to_supported_values(self) -> None:
        values = {
            "run": "running",
            "bike": "cycling",
            "golf": "golf",
            "cricket": "cricket",
            "five a side": "football",
            "tennis": "tennis",
            "nature walk": "hiking",
            "park outing": "picnic",
            "outdoor event": "outdoor_event",
            "photo session": "photography",
        }

        for label, expected in values.items():
            with self.subTest(label=label):
                self.assertEqual(_canonical_activity(label), expected)

    def test_explicit_fields_parse_into_a_validated_query_and_filter_invented_profiles(self) -> None:
        model = FakeModel(
            '{"activity":"running","location_label":"Powai, Mumbai","radius_km":8,'
            '"start_time":"2026-10-25T08:00:00+05:30","end_time":"2026-10-25T10:00:00+05:30",'
            '"timezone":"Asia/Kolkata","profile_flags":["asthma","senior","pregnancy"]}'
        )
        extractor = QueryExtractor(model)  # type: ignore[arg-type]
        question = "I have mild asthma. Where can my parents go running near Powai tomorrow morning?"

        result = asyncio.run(extractor.extract(question, now=datetime(2026, 10, 24, 12, tzinfo=timezone.utc)))

        self.assertNotIsInstance(result, QueryClarification)
        self.assertEqual(result.activity, "running")
        self.assertEqual(result.location_label, "Powai, Mumbai")
        self.assertEqual(result.profile_flags, ["asthma", "senior"])
        self.assertEqual(result.radius_km, 8)
        self.assertEqual(result.start_time.isoformat(), "2026-10-25T02:30:00+00:00")
        self.assertTrue(all("system" in message["role"] or message["role"] == "user" for message in model.messages))
        self.assertIn("ignore instructions", model.messages[0]["content"])

    def test_near_me_location_is_clarified_instead_of_inferred(self) -> None:
        model = FakeModel(
            '{"activity":"cycling","location_label":"near me","radius_km":null,'
            '"start_time":"2026-10-25T08:00:00+05:30","end_time":"2026-10-25T09:00:00+05:30",'
            '"timezone":"Asia/Kolkata","profile_flags":[]}'
        )

        result = asyncio.run(QueryExtractor(model).extract(
            "Can I cycle near me tomorrow morning?",
            now=datetime(2026, 10, 24, 12, tzinfo=timezone.utc),
        ))  # type: ignore[arg-type]

        self.assertIsInstance(result, QueryClarification)
        self.assertIn("typed place", result.question)

    def test_vague_window_is_clarified(self) -> None:
        model = FakeModel(
            '{"activity":"hiking","location_label":"Lonavala","radius_km":null,'
            '"start_time":null,"end_time":null,"timezone":"Asia/Kolkata","profile_flags":[]}'
        )

        result = asyncio.run(QueryExtractor(model).extract(
            "Is Saturday or Sunday better for a hike near Lonavala?",
            now=datetime(2026, 10, 24, 12, tzinfo=timezone.utc),
        ))  # type: ignore[arg-type]

        self.assertIsInstance(result, QueryClarification)
        self.assertIn("time window", result.question)

    def test_malformed_model_json_fails_closed(self) -> None:
        with self.assertRaises(QueryExtractionError):
            asyncio.run(QueryExtractor(FakeModel("not json")).extract(
                "Where can I run tomorrow near Powai?"
            ))  # type: ignore[arg-type]

    def test_negated_sensitive_details_are_not_attached_to_the_query(self) -> None:
        model = FakeModel(
            '{"activity":"picnic","location_label":"Powai","radius_km":null,'
            '"start_time":"2026-10-25T12:00:00+05:30","end_time":"2026-10-25T15:00:00+05:30",'
            '"timezone":"Asia/Kolkata","profile_flags":["asthma","child"]}'
        )

        result = asyncio.run(QueryExtractor(model).extract(
            "I don't have asthma and no children are joining. Find a picnic time near Powai tomorrow.",
            now=datetime(2026, 10, 24, 12, tzinfo=timezone.utc),
        ))  # type: ignore[arg-type]

        self.assertNotIsInstance(result, QueryClarification)
        self.assertEqual(result.profile_flags, [])


if __name__ == "__main__":
    unittest.main()
