import unittest
import json
import threading
from http.client import HTTPConnection
from unittest.mock import patch

from prompt_rewriter import (
    build_localization_instruction,
    build_localization_result,
    build_rewrite_prompt,
    rewrite_brief_for_market,
)
from api_server import create_server
from rule_loader import RuleValidationError, _validate, list_available_markets, load_market_rules


class RuleLoaderTests(unittest.TestCase):
    def test_lists_and_loads_markets(self):
        self.assertEqual(list_available_markets(), ["japan", "middle_east_gulf"])
        self.assertEqual(load_market_rules("japan")["market_id"], "japan")

    def test_all_market_files_are_valid(self):
        for market_id in list_available_markets():
            with self.subTest(market_id=market_id):
                rules = load_market_rules(market_id)
                self.assertEqual(rules["market_id"], market_id)
                self.assertEqual(rules["schema_version"], "1.0")
                self.assertEqual(rules["review_status"], "draft")

    def test_rejects_path_traversal(self):
        with self.assertRaises(ValueError):
            load_market_rules("../secret")

    def test_rejects_mismatched_market_id(self):
        with self.assertRaises(RuleValidationError):
            _validate({"market_id": "other", "market_name": "x", "avoid": {}, "embrace": {}, "sources": ["x"]}, "japan")

    def test_rejects_unknown_review_status(self):
        rules = load_market_rules("japan")
        rules["review_status"] = "published"
        with self.assertRaises(RuleValidationError):
            _validate(rules, "japan")


class PromptTests(unittest.TestCase):
    def test_instruction_contains_avoid_and_embrace_rules(self):
        text = build_localization_instruction(load_market_rules("japan"))
        self.assertIn("NÊN TRÁNH", text)
        self.assertIn("NÊN ÁP DỤNG", text)
        self.assertIn("Hoa anh đào", text)

    def test_preview_prompt_has_brief_and_market(self):
        text = build_rewrite_prompt("Chai trà xanh", "japan")
        self.assertIn("Chai trà xanh", text)
        self.assertIn("Nhật Bản", text)

    def test_structured_result_contains_prompt_rules_and_sources(self):
        rules = load_market_rules("japan")
        result = build_localization_result(
            "Chai trà xanh", rules, "A quiet seasonal green tea bottle"
        )

        self.assertEqual(result["market_id"], "japan")
        self.assertEqual(result["rule_schema_version"], "1.0")
        self.assertEqual(result["rule_review_status"], "draft")
        self.assertEqual(result["localized_prompt"], "A quiet seasonal green tea bottle")
        self.assertTrue(any("Hoa anh đào" in rule["description"] for rule in result["applied_rules"]))
        self.assertTrue(any("màu trắng" in rule["description"] for rule in result["avoid_rules"]))
        self.assertGreater(len(result["sources"]), 0)

    @patch("prompt_rewriter.call_llm", return_value="Localized prompt")
    def test_rewrite_calls_llm_and_returns_structured_result(self, mock_call_llm):
        result = rewrite_brief_for_market("Chai trà xanh", "japan")

        self.assertEqual(result["localized_prompt"], "Localized prompt")
        mock_call_llm.assert_called_once()


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = create_server("127.0.0.1", 0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.host, cls.port = cls.server.server_address

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def request(self, method, path, body=None):
        connection = HTTPConnection(self.host, self.port, timeout=2)
        encoded = None if body is None else json.dumps(body).encode("utf-8")
        headers = {"Content-Type": "application/json"} if encoded else {}
        connection.request(method, path, body=encoded, headers=headers)
        response = connection.getresponse()
        payload = json.loads(response.read())
        connection.close()
        return response.status, payload

    def test_health_endpoint(self):
        status, payload = self.request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "ok")

    def test_localize_rejects_invalid_payload(self):
        status, payload = self.request("POST", "/localize", {"market_id": "japan"})
        self.assertEqual(status, 400)
        self.assertIn("brief", payload["error"])

    @patch("api_server.rewrite_brief_for_market")
    def test_localize_returns_domain_result(self, mock_rewrite):
        mock_rewrite.return_value = {
            "market_id": "japan",
            "localized_prompt": "Localized prompt",
        }
        status, payload = self.request(
            "POST", "/localize", {"brief": "Tea", "market_id": "japan"}
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["localized_prompt"], "Localized prompt")
        mock_rewrite.assert_called_once_with("Tea", "japan")


if __name__ == "__main__":
    unittest.main()
