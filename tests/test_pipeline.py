import unittest
from unittest.mock import patch

from prompt_rewriter import (
    build_localization_instruction,
    build_localization_result,
    build_rewrite_prompt,
    rewrite_brief_for_market,
)
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


if __name__ == "__main__":
    unittest.main()
