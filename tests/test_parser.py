import pytest
from tinyblabla.parser import parse_suggestions, clean_segment


class TestParseSuggestions:
    def test_basic_dot_format(self):
        raw = "1. Hello world\n2. Hi there\n3. Greetings"
        assert parse_suggestions(raw) == ["Hello world", "Hi there", "Greetings"]

    def test_parenthesis_format(self):
        raw = "1) Hello world\n2) Hi there"
        assert parse_suggestions(raw) == ["Hello world", "Hi there"]

    def test_preamble_is_ignored(self):
        raw = "Here are some suggestions:\n1. Hello world\n2. Hi there"
        assert parse_suggestions(raw) == ["Hello world", "Hi there"]

    def test_trailing_commentary_after_blank_is_ignored(self):
        raw = "1. Hello world\n\nSome commentary\n2. Hi there"
        assert parse_suggestions(raw) == ["Hello world", "Hi there"]

    def test_soft_wrapped_line_is_joined(self):
        raw = "1. This is a long sentence\nthat wraps to the next line\n2. Short one"
        assert parse_suggestions(raw) == [
            "This is a long sentence that wraps to the next line",
            "Short one",
        ]

    def test_caps_at_five(self):
        raw = "\n".join(f"{i}. suggestion {i}" for i in range(1, 9))
        result = parse_suggestions(raw)
        assert len(result) == 5
        assert result[0] == "suggestion 1"
        assert result[4] == "suggestion 5"

    def test_empty_string(self):
        assert parse_suggestions("") == []

    def test_no_numbers(self):
        assert parse_suggestions("just some plain text") == []

    def test_last_item_without_trailing_newline(self):
        raw = "1. First\n2. Second"
        assert parse_suggestions(raw) == ["First", "Second"]

    def test_french_suggestions(self):
        raw = (
            "1. Je voudrais que tu viennes avec moi demain.\n"
            "2. J'aimerais que tu m'accompagnes demain.\n"
            "3. Pourrais-tu venir avec moi demain ?\n"
        )
        result = parse_suggestions(raw)
        assert len(result) == 3
        assert result[0] == "Je voudrais que tu viennes avec moi demain."

    def test_two_digit_numbers(self):
        raw = "\n".join(f"{i}. item {i}" for i in range(1, 11))
        result = parse_suggestions(raw)
        assert len(result) == 5


class TestCleanSegment:
    def test_strips_dot_prefix(self):
        assert clean_segment("1. Hello world") == "Hello world"

    def test_strips_parenthesis_prefix(self):
        assert clean_segment("2) Hi there") == "Hi there"

    def test_joins_multiline(self):
        assert clean_segment("1. Hello\nworld") == "Hello world"

    def test_stops_at_blank_line(self):
        assert clean_segment("1. Hello\n\nsome commentary") == "Hello"

    def test_strips_whitespace(self):
        assert clean_segment("1.  Hello  ") == "Hello"

    def test_empty_segment(self):
        assert clean_segment("") == ""

    def test_number_only_segment(self):
        assert clean_segment("1. ") == ""

    def test_french_text_preserved(self):
        seg = "1. Je voudrais que tu viennes avec moi demain."
        assert clean_segment(seg) == "Je voudrais que tu viennes avec moi demain."
