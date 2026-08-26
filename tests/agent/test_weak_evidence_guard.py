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

    def test_one_high_score_among_weak_docs_prevents_warning(self):
        """La fonction ne lit que `score` (jamais `exact_match`) : un seul
        document à score élevé parmi des candidats faibles suffit à
        désactiver le garde-fou, simplement parce que le MAX des scores
        dépasse le seuil — pas de traitement spécial pour exact_match."""
        docs = [{"score": 1.0, "exact_match": True}, {"score": 0.05}]
        response = "✅ Certain."
        result = _enforce_weak_evidence_warning(response, docs)
        assert result == response

    def test_exact_match_flag_alone_without_high_score_is_ignored(self):
        """Confirme explicitement que `exact_match=True` seul, avec un score
        bas, N'empêche PAS le garde-fou — seul le score compte."""
        docs = [{"score": 0.1, "exact_match": True}]
        response = "✅ Certain."
        result = _enforce_weak_evidence_warning(response, docs)
        assert result.startswith("⚠️ **Documentation faible détectée**")

    def test_certain_phrase_mid_paragraph_is_not_downgraded(self):
        """Régression : '✅ Certain' apparaissant au milieu d'une phrase de
        prose (pas en tête de ligne) ne doit pas être touché par le garde-fou
        — seule la ligne de déclaration de certitude, en tête de ligne, doit
        l'être."""
        docs = [{"score": 0.1}]
        response = (
            "## Niveau de certitude\n"
            "✅ Certain — signature confirmée.\n\n"
            "## Notes techniques\n"
            "Le comportement est désormais fiable. ✅ Certain que la fonction "
            "Substr existe et fonctionne comme documenté, testée manuellement."
        )
        result = _enforce_weak_evidence_warning(response, docs)
        # La ligne de déclaration de certitude est bien rétrogradée...
        assert "## Niveau de certitude\n🔬 À vérifier" in result
        # ...mais la phrase de prose dans les notes techniques reste intacte.
        assert "Le comportement est désormais fiable. ✅ Certain que la fonction Substr existe" in result

    def test_threshold_constant_matches_prompt_documented_value(self):
        assert WEAK_EVIDENCE_SCORE_THRESHOLD == 0.50
