"""Tests du garde-fou mécanique de certitude — src/agent/mispl_agent.py::_enforce_weak_evidence_warning."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.agent.mispl_agent import _enforce_weak_evidence_warning, WEAK_EVIDENCE_SCORE_THRESHOLD


class TestWeakEvidenceGuard:
    def test_response_unchanged_when_score_above_threshold(self):
        docs = [{"score": 0.95}, {"score": 0.3}]
        response = "## Niveau de certitude\n✅ Certain — tout va bien."
        result = _enforce_weak_evidence_warning(response, docs)
        assert result == response

    def test_warning_prepended_when_all_scores_below_threshold(self):
        docs = [{"score": 0.17}, {"score": 0.05}]
        response = "## Niveau de certitude\n✅ Certain — tout va bien."
        result = _enforce_weak_evidence_warning(response, docs)
        assert result.startswith("⚠️ **Documentation faible détectée**")

    def test_certain_claim_downgraded_when_evidence_weak(self):
        docs = [{"score": 0.1}]
        response = "## Niveau de certitude\n✅ Certain — signature confirmée."
        result = _enforce_weak_evidence_warning(response, docs)
        assert "✅ Certain" not in result
        assert "🔬 À vérifier" in result

    def test_bold_certain_variant_also_downgraded(self):
        docs = [{"score": 0.1}]
        response = "## Niveau de certitude\n✅ **Certain** — signature confirmée."
        result = _enforce_weak_evidence_warning(response, docs)
        assert "Certain" not in result
        assert "🔬 À vérifier" in result

    def test_empty_docs_list_triggers_warning(self):
        response = "✅ Certain — réponse générée sans aucun document."
        result = _enforce_weak_evidence_warning(response, [])
        assert result.startswith("⚠️ **Documentation faible détectée**")
        assert "0.00" in result

    def test_exact_match_score_of_one_prevents_warning(self):
        """Un seul document exact-match (score=1.0) parmi des candidats faibles
        suffit à désactiver le garde-fou — cohérent avec le fait qu'un exact-
        match est une preuve forte à lui seul."""
        docs = [{"score": 1.0, "exact_match": True}, {"score": 0.05}]
        response = "✅ Certain."
        result = _enforce_weak_evidence_warning(response, docs)
        assert result == response

    def test_threshold_constant_matches_prompt_documented_value(self):
        assert WEAK_EVIDENCE_SCORE_THRESHOLD == 0.50
