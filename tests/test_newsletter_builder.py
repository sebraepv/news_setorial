import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from newsletter.builder import NewsletterBuilder


class NewsletterBuilderTests(unittest.TestCase):
    def test_loads_config_without_whitespace(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            env_path = Path(tmp_dir) / "variaveis.env"
            env_path.write_text(
                "ENDPOINT_KIMI= https://example.test/openai/v1\n"
                "KIMI_API_KEY_FOUNDRY= abc123\n",
                encoding="utf-8",
            )

            builder = NewsletterBuilder(env_path=env_path, deployment_name="demo")

            self.assertEqual(builder.endpoint, "https://example.test/openai/v1")
            self.assertEqual(builder.api_key, "abc123")
            self.assertEqual(builder.deployment_name, "demo")


if __name__ == "__main__":
    unittest.main()
