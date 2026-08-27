"""Tests du garde-fou mécanique de certitude — src/agent/mispl_agent.py::_enforce_weak_evidence_warning."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.agent.mispl_agent import (
    _enforce_weak_evidence_warning,
    _strip_leaked_retrieval_scores,
    WEAK_EVIDENCE_SCORE_THRESHOLD,
)


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
        # Le score numérique interne ne doit jamais apparaître dans le texte
        # visible par l'utilisateur (cf. _strip_leaked_retrieval_scores).
        assert "score" not in result.lower()

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


class TestScoreLeakGuard:
    def test_strips_score_from_certainty_justification(self):
        response = (
            "✅ Certain — la signature de `Substr` est présente avec un score "
            "de 1,00 dans le RAG et un exemple d'utilisation est fourni dans "
            "la documentation."
        )
        result = _strip_leaked_retrieval_scores(response)
        assert "score" not in result.lower()
        assert "1,00" not in result
        assert "✅ Certain" in result

    def test_strips_score_colon_notation(self):
        response = "Justification : score : 0.952, confirmé dans la doc."
        result = _strip_leaked_retrieval_scores(response)
        assert "score" not in result.lower()
        assert "0.952" not in result

    def test_strips_parenthetical_score(self):
        response = "Fonction confirmée (score=1.000, exact=True) dans la doc."
        result = _strip_leaked_retrieval_scores(response)
        assert "score" not in result.lower()

    def test_leaves_unrelated_text_untouched(self):
        response = "## Contexte GLIMS\nExtraction des 3 premiers caractères d'une chaîne."
        result = _strip_leaked_retrieval_scores(response)
        assert result == response

    def test_wired_into_weak_evidence_guard_output(self):
        """La suppression de fuite de score s'applique aussi sur le chemin
        'documentation faible' (_enforce_weak_evidence_warning), y compris
        dans du texte qui survit à la rétrogradation de la ligne ✅ Certain
        (donc pas uniquement parce que toute la ligne a été remplacée)."""
        docs = [{"score": 0.05}]
        response = (
            "## Niveau de certitude\n"
            "✅ Certain — tout va bien.\n\n"
            "## Notes techniques\n"
            "Cette fonction a été retrouvée avec un score de 0,95 dans le RAG."
        )
        result = _enforce_weak_evidence_warning(response, docs)
        assert "score" not in result.lower()
        assert "0,95" not in result

    def test_code_block_never_altered(self):
        """Régression critique (revue du 2026-08-27) : le nettoyage ne doit
        jamais toucher l'intérieur d'un bloc ``` ``` ``` — une première
        version cassait la syntaxe MISPL à point initial (".Sample.Id" →
        "IF.Sample.Id") et écrasait l'indentation, car le nettoyage
        s'appliquait à la réponse entière au lieu de la seule prose."""
        response = (
            "## Code MISPL\n"
            "```mispl\n"
            "STRING PROGRAM\n"
            "  IF .Sample.Id NE ? THEN\n"
            "    code := Substr(.Sample.Id, 1, 3);\n"
            "  ENDIF;\n"
            "RETURN code;\n"
            "```\n\n"
            "## Sources documentaires\n"
            "Source : function_string.htm\n\n"
            "## Niveau de certitude\n"
            "✅ Certain — la signature de `Substr` est présente avec un score "
            "de 1,00 dans le RAG.\n"
        )
        result = _strip_leaked_retrieval_scores(response)
        assert "IF .Sample.Id NE ? THEN" in result
        assert "code := Substr(.Sample.Id, 1, 3);" in result
        assert "Source : function_string.htm" in result  # typographie française préservée
        assert "1,00" not in result

    def test_clinical_score_variable_and_prose_untouched(self):
        """Régression critique : un score métier (variable MISPL nommée
        "score", score de Glasgow, z-score) n'est pas une fuite de retrieval
        et ne doit jamais être effacé — seul un nombre au format 0.xxx/1.xxx
        (plage des scores de retrieval de ce RAG) est concerné."""
        response = (
            "```mispl\n"
            "FRACTIONAL PROGRAM\n"
            "  FRACTIONAL score;\n"
            "  score := 0.95;\n"
            "RETURN score;\n"
            "```\n"
            "Le score de Glasgow est de 8. Calcul du z-score : 2.58.\n"
        )
        result = _strip_leaked_retrieval_scores(response)
        assert "FRACTIONAL score;" in result
        assert "score := 0.95;" in result
        assert "Glasgow" in result
        assert "z-score : 2.58" in result
