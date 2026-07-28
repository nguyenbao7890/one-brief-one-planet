import unittest

from prompt_rewriter import build_localization_instruction, build_rewrite_prompt
from rule_loader import RuleValidationError, _validate, list_available_markets, load_market_rules


class RuleLoaderTests(unittest.TestCase):
    def test_lists_and_loads_markets(self):
        self.assertEqual(list_available_markets(), ["japan", "middle_east_gulf"])
        self.assertEqual(load_market_rules("japan")["market_id"], "japan")

    def test_all_market_files_are_valid(self):
        for market_id in list_available_markets():
            with self.subTest(market_id=market_id):
                self.assertEqual(load_market_rules(market_id)["market_id"], market_id)

    def test_rejects_path_traversal(self):
        with self.assertRaises(ValueError):
            load_market_rules("../secret")

    def test_rejects_mismatched_market_id(self):
        with self.assertRaises(RuleValidationError):
            _validate({"market_id": "other", "market_name": "x", "avoid": {}, "embrace": {}, "sources": ["x"]}, "japan")


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


if __name__ == "__main__":
    unittest.main()
