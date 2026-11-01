"""Tests for the output filter — AGENTS.md constraint #3 guard."""


from app.mentor.output_filter import filter_hint_response


class TestOutputFilter:
    def test_clean_l1_hint_passes(self) -> None:
        hint = "Have you considered what happens when the array has duplicate values?"
        text, modified = filter_hint_response(hint, hint_level=1)
        assert not modified
        assert text == hint

    def test_l4_walkthroughs_pass_without_filter(self) -> None:
        code_heavy = "Here is the full solution:\n```python\ndef twoSum(nums, target):\n    seen = {}\n    for i, num in enumerate(nums):\n        if target - num in seen:\n            return [seen[target - num], i]\n        seen[num] = i\n```\nThis runs in O(n) time."
        text, modified = filter_hint_response(code_heavy, hint_level=4)
        assert not modified  # L4 is not filtered

    def test_direct_answer_phrasing_blocked_at_l1(self) -> None:
        hint = "The answer is: use a hash map to store complements."
        text, modified = filter_hint_response(hint, hint_level=1)
        assert modified
        assert "filtered" in text.lower()

    def test_direct_answer_phrasing_blocked_at_l2(self) -> None:
        hint = "The solution is: iterate and store each element's complement."
        text, modified = filter_hint_response(hint, hint_level=2)
        assert modified

    def test_l3_allows_pseudocode(self) -> None:
        pseudocode = "Use a hash map:\n```\ninitialize empty map\nfor each i, num in nums:\n    if target-num in map: return [map[target-num], i]\n    map[num] = i\n```"
        text, modified = filter_hint_response(pseudocode, hint_level=3)
        assert not modified  # L3 allows pseudocode

    def test_short_code_snippet_allowed_at_l2(self) -> None:
        hint = "Think about this step:\n```python\ncomplement = target - num\n```\nWhere would you store this?"
        text, modified = filter_hint_response(hint, hint_level=2)
        assert not modified  # short snippet is fine
