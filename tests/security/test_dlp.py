"""Tests DLP — détection de données patient dans le texte envoyé au LLM."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.security.dlp import dlp_check


class TestDLPBlocking:
    def test_nir_blocks(self):
        blocked, alerts = dlp_check("Mon NIR est 1850578006012 34")
        assert blocked is True
        assert any("NIR" in a for a in alerts)

    def test_ipp_blocks(self):
        blocked, alerts = dlp_check("le patient IPP:1234567 a un resultat anormal")
        assert blocked is True

    def test_clean_technical_question_not_blocked(self):
        blocked, alerts = dlp_check("Comment utiliser Substr pour extraire une sous-chaine ?")
        assert blocked is False

    def test_lab_context_with_ipp_blocks(self):
        # Reproduit le bug corrigé : le contexte labo doit être vérifié comme la question
        enriched = "[Contexte labo: patient IPP 1234567, analyseur Cobas]\n\nComment formater la date ?"
        blocked, alerts = dlp_check(enriched)
        assert blocked is True

    def test_bare_dossier_number_blocks(self):
        blocked, alerts = dlp_check("le dossier 4582910 a un resultat aberrant sur Cobas 8000")
        assert blocked is True

    def test_name_and_dob_combination_blocks(self):
        blocked, alerts = dlp_check("Mme DUPONT Marie, nee le 12/03/1980, resultat glycemie anormal")
        assert blocked is True


class TestDLPWarningsNonBlocking:
    def test_date_triggers_warning_not_block(self):
        blocked, alerts = dlp_check("livraison prevue le 12/03/2026")
        assert blocked is False
        assert len(alerts) >= 1

    def test_name_alone_still_warning_not_block(self):
        blocked, alerts = dlp_check("Dr Martin BERNARD a valide ce resultat")
        assert blocked is False
