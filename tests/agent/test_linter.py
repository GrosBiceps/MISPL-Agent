"""Tests du linter de sécurité MISPL — règles critiques pour la production GLIMS."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.agent.linter import (
    Severity,
    autofix_mispl,
    extract_mispl_blocks,
    lint_mispl_code,
    lint_response,
)


class TestInfiniteLoopDetection:
    def test_while_true_is_error(self):
        result = lint_mispl_code("WHILE TRUE DO\n  x := 1;\nDONE")
        assert result.has_errors
        assert any("infinie" in i.message.lower() for i in result.issues)

    def test_repeat_without_until_is_error(self):
        result = lint_mispl_code("REPEAT\n  x := x + 1;\n")
        assert result.has_errors

    def test_repeat_with_until_is_clean_of_that_rule(self):
        result = lint_mispl_code("REPEAT\n  x := x + 1;\nUNTIL x >= 10")
        assert not any("REPEAT sans UNTIL" in i.message for i in result.issues)

    def test_while_done_mismatch_is_error(self):
        result = lint_mispl_code("WHILE x < 10 DO\n  x := x + 1;")
        assert result.has_errors


class TestReadOnlyFieldProtection:
    def test_id_assignment_is_error(self):
        result = lint_mispl_code('.Id := "X";')
        assert result.has_errors

    def test_validation_status_assignment_is_error(self):
        result = lint_mispl_code(".ValidationStatus := 1;")
        assert result.has_errors


class TestFakeFunctionDetection:
    def test_stringtoreal_flagged(self):
        result = lint_mispl_code('x := StringToReal("1.5");')
        assert result.has_errors
        assert any("StringToReal" in i.message for i in result.issues)

    def test_createpatient_flagged(self):
        result = lint_mispl_code('CreatePatient("Doe", "John");')
        assert result.has_errors

    def test_real_function_not_flagged(self):
        result = lint_mispl_code('x := StringToFractional("1.5");')
        assert not any("StringToFractional" in i.message and "inexistante" in i.message for i in result.issues)


class TestBalanceChecks:
    def test_if_endif_mismatch_is_error(self):
        result = lint_mispl_code("IF x = 1 THEN\n  y := 1;")
        assert result.has_errors

    def test_balanced_if_endif_no_balance_error(self):
        result = lint_mispl_code("IF x = 1 THEN\n  y := 1;\nENDIF")
        assert not any("IF/ENDIF" in i.message for i in result.issues)


class TestCleanCode:
    def test_valid_program_is_clean(self):
        code = (
            'STRING PROGRAM\n'
            '  RETURN Substr("abcdef", 1, 3);\n'
        )
        result = lint_mispl_code(code)
        assert result.is_clean

    def test_empty_code_is_clean(self):
        assert lint_mispl_code("").is_clean


class TestExtractAndAutofix:
    def test_extract_mispl_blocks_finds_tagged_block(self):
        text = "Voici le code:\n```mispl\nRETURN Today();\n```\nFin."
        blocks = extract_mispl_blocks(text)
        assert blocks == ["RETURN Today();"]

    def test_extract_returns_empty_for_no_code(self):
        assert extract_mispl_blocks("Pas de code ici.") == []

    def test_autofix_converts_double_slash_comments(self):
        text = "```mispl\n// commentaire\nRETURN Today();\n```"
        fixed, corrections = autofix_mispl(text)
        assert "/*" in fixed and "//" not in fixed
        assert corrections

    def test_autofix_converts_cascade_request(self):
        text = '```mispl\nCascadeRequest("GLYC");\n```'
        fixed, corrections = autofix_mispl(text)
        assert "AddRequest" in fixed
        assert corrections

    def test_lint_response_combines_all_blocks(self):
        text = "```mispl\nWHILE TRUE DO\nDONE\n```\n\n```mispl\n.Id := 1;\n```"
        result = lint_response(text)
        assert len(result.issues) >= 2
