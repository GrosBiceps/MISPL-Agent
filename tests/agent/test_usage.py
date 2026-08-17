"""Tests de l'extraction des compteurs de tokens depuis une réponse OpenRouter."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.agent.mispl_agent import _extract_usage


class FakeUsage:
    def __init__(self, prompt_tokens, completion_tokens, total_tokens):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens


class FakeCompletion:
    def __init__(self, usage):
        self.usage = usage


class TestExtractUsage:
    def test_reads_token_counts_from_completion(self):
        completion = FakeCompletion(FakeUsage(120, 340, 460))
        assert _extract_usage(completion) == {
            "prompt_tokens": 120,
            "completion_tokens": 340,
            "total_tokens": 460,
        }

    def test_defaults_to_zero_when_usage_missing(self):
        class NoUsage:
            pass

        assert _extract_usage(NoUsage()) == {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }

    def test_defaults_to_zero_when_usage_is_none(self):
        completion = FakeCompletion(None)
        assert _extract_usage(completion) == {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }
