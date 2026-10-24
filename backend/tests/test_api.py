import unittest

from fastapi.testclient import TestClient

from app.main import app


class ApiFoundationTests(unittest.TestCase):
    def setUp(self) -> None:
        app.state.model_ready = False
        app.state.recommendation_service = None
        self.client = TestClient(app)

    def test_health_reports_model_not_ready_without_exposing_configuration(self) -> None:
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"status": "not_ready", "model_ready": False, "version": "0.1.0"},
        )

    def test_recommendations_never_return_a_fabricated_result_when_unconfigured(self) -> None:
        response = self.client.post(
            "/api/recommendations",
            json={"question": "Where should I go running tomorrow near Powai?"},
        )

        self.assertEqual(response.status_code, 503)
        self.assertIn("not ready", response.json()["detail"])

    def test_request_rejects_blank_and_oversized_questions(self) -> None:
        blank = self.client.post("/api/recommendations", json={"question": "   "})
        oversized = self.client.post("/api/recommendations", json={"question": "x" * 501})

        self.assertEqual(blank.status_code, 422)
        self.assertEqual(oversized.status_code, 422)

    def test_request_rejects_unknown_fields(self) -> None:
        response = self.client.post(
            "/api/recommendations",
            json={"question": "Suggest a hike near Lonavala tomorrow", "debug": True},
        )

        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
