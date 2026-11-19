import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from backend.main import ChatRequest, gemini_answer


class GeminiIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_no_key_uses_demo_fallback(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}):
            answer = await gemini_answer(ChatRequest(message="What can you help me with?"))
        self.assertIn("Demo mode is active", answer)

    async def test_configured_key_returns_validated_gemini_text(self):
        client = MagicMock()
        client.models.generate_content.return_value = SimpleNamespace(text="  Gemini response  ")
        with patch.dict(os.environ, {"GEMINI_API_KEY": "configured"}), patch("google.genai.Client", return_value=client) as factory:
            answer = await gemini_answer(ChatRequest(message="Explain this service", language="English"))
        self.assertEqual(answer, "Gemini response")
        factory.assert_called_once_with(api_key="configured")
        client.models.generate_content.assert_called_once()

    async def test_provider_error_becomes_generic_gateway_error(self):
        client = MagicMock()
        client.models.generate_content.side_effect = RuntimeError("sensitive provider detail")
        with patch.dict(os.environ, {"GEMINI_API_KEY": "configured"}), patch("google.genai.Client", return_value=client):
            with self.assertRaises(HTTPException) as raised:
                await gemini_answer(ChatRequest(message="Explain this service"))
        self.assertEqual(raised.exception.status_code, 502)
        self.assertNotIn("sensitive provider detail", raised.exception.detail)

    async def test_empty_provider_response_is_rejected(self):
        client = MagicMock()
        client.models.generate_content.return_value = SimpleNamespace(text="  ")
        with patch.dict(os.environ, {"GEMINI_API_KEY": "configured"}), patch("google.genai.Client", return_value=client):
            with self.assertRaises(HTTPException) as raised:
                await gemini_answer(ChatRequest(message="Explain this service"))
        self.assertEqual(raised.exception.status_code, 502)
        self.assertIn("empty response", raised.exception.detail)


if __name__ == "__main__":
    unittest.main()
