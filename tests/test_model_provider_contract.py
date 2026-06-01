import json
import unittest

from backend.app.model_providers import (
    LocalDemoModelProvider,
    ModelProviderError,
    OllamaModelProvider,
    parse_model_json,
)


class ModelProviderContractTest(unittest.TestCase):
    def test_ollama_model_provider_calls_generate_endpoint(self):
        posts = []

        def http_post(url, payload, timeout):
            posts.append((url, payload, timeout))
            return 200, json.dumps({"response": '{"queries":["raspberry pi 5 buy"]}'})

        provider = OllamaModelProvider(
            base_url="http://ollama:11434",
            model_name="mistral-nemo:12b",
            timeout_seconds=60,
            http_post=http_post,
        )

        result = provider.complete_json("Return JSON")

        self.assertEqual({"queries": ["raspberry pi 5 buy"]}, result)
        self.assertEqual("http://ollama:11434/api/generate", posts[0][0])
        self.assertEqual("mistral-nemo:12b", posts[0][1]["model"])
        self.assertFalse(posts[0][1]["stream"])
        self.assertEqual("json", posts[0][1]["format"])

    def test_ollama_internal_assistant_uses_plain_text_completion(self):
        posts = []

        def http_post(url, payload, timeout):
            posts.append((url, payload, timeout))
            return 200, json.dumps({"response": "Поставщик выглядит проверяемым, но нужно уточнить цену и сроки."})

        provider = OllamaModelProvider(
            base_url="http://ollama:11434",
            model_name="qwen2.5:14b",
            http_post=http_post,
        )

        result = provider.complete("You are an internal AI assistant. Return only the internal assistant answer.")

        self.assertIn("Поставщик", result)
        self.assertNotIn("format", posts[0][1])

    def test_ollama_model_provider_rejects_invalid_json(self):
        def http_post(url, payload, timeout):
            return 200, json.dumps({"response": "not json"})

        provider = OllamaModelProvider(
            base_url="http://ollama:11434",
            model_name="mistral-nemo:12b",
            http_post=http_post,
        )

        with self.assertRaises(ModelProviderError):
            provider.complete_json("Return JSON")

    def test_parse_model_json_accepts_fenced_json(self):
        payload = parse_model_json('```json\n{"selected":[{"url":"https://example.com"}]}\n```')

        self.assertEqual({"selected": [{"url": "https://example.com"}]}, payload)

    def test_local_demo_provider_returns_deterministic_json(self):
        provider = LocalDemoModelProvider()

        self.assertEqual({"queries": ["Raspberry Pi 5"]}, provider.complete_json("Raspberry Pi 5"))

    def test_local_demo_provider_rejects_internal_assistant_prompt(self):
        provider = LocalDemoModelProvider()

        with self.assertRaises(ModelProviderError):
            provider.complete("You are an internal AI assistant. Return only the internal assistant answer.")


if __name__ == "__main__":
    unittest.main()
