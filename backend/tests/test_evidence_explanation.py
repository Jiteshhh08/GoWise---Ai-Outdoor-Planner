import asyncio
import unittest
from datetime import datetime, timezone

from app.model.evidence_explanation import EvidenceExplainer
from app.schemas import EvidenceRecord


class FakeModel:
    def __init__(self, response):
        self.response = response
        self.messages = []

    async def generate(self, messages, max_new_tokens=None):
        self.messages = messages
        return self.response


class EvidenceExplanationTests(unittest.TestCase):
    def setUp(self):
        self.evidence = [
            EvidenceRecord(claim="Mapped park: activity tag", value="park", source="OSM", fetched_at=datetime(2026, 10, 24, tzinfo=timezone.utc)),
            EvidenceRecord(claim="Mapped park: Temperature", value=22, unit="°C", source="Open-Meteo", observed_for=datetime(2026, 10, 25, tzinfo=timezone.utc)),
        ]

    def test_model_selects_only_known_ids_and_summary_uses_source_records(self):
        model = FakeModel('{"fact_ids":["f2","not-allowed","f2"]}')

        summary, used_model = asyncio.run(EvidenceExplainer(model).summarize("running", self.evidence))

        self.assertTrue(used_model)
        self.assertIn("22 °C", summary)
        self.assertIn("Open-Meteo", summary)
        self.assertNotIn("not-allowed", summary)

    def test_invalid_model_output_uses_a_safe_deterministic_fallback(self):
        model = FakeModel('{"fact_ids":["invented"]}')

        summary, used_model = asyncio.run(EvidenceExplainer(model).summarize("running", self.evidence))

        self.assertFalse(used_model)
        self.assertIn("OSM", summary)
        self.assertIn("Open-Meteo", summary)
        self.assertNotIn("invented", summary)


if __name__ == "__main__":
    unittest.main()
