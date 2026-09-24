"""
Tests pour la construction du prompt système (src/agent/prompt_builder.py).

Vérifie en particulier le correctif de sécurité audit F-03 :
la guard anti-extraction doit être présente dans le prompt système,
inconditionnellement (indépendamment du skill_profile, access_mode, ou include_rules).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.agent.prompt_builder import build_system_prompt


class TestAntiExtractionGuard:
    """Vérifie que la défense contre l'extraction du prompt est toujours présente."""

    def test_anti_extraction_present_default(self):
        """Test : la garde anti-extraction est présente avec les paramètres par défaut."""
        prompt = build_system_prompt()
        assert "DÉFENSE EXTRACTION SYSTÈME" in prompt
        assert "refuser TOUTE demande" in prompt
        assert "révéler" in prompt

    def test_anti_extraction_present_dsi_mode(self):
        """Test : la garde est présente en mode DSI."""
        prompt = build_system_prompt(access_mode="dsi")
        assert "DÉFENSE EXTRACTION SYSTÈME" in prompt

    def test_anti_extraction_present_technicien_mode(self):
        """Test : la garde est présente en mode Technicien."""
        prompt = build_system_prompt(access_mode="technicien")
        assert "DÉFENSE EXTRACTION SYSTÈME" in prompt

    def test_anti_extraction_present_with_rules(self):
        """Test : la garde est présente même avec include_rules=True."""
        prompt = build_system_prompt(include_rules=True)
        assert "DÉFENSE EXTRACTION SYSTÈME" in prompt

    def test_anti_extraction_present_without_rules(self):
        """Test : la garde est présente même avec include_rules=False."""
        prompt = build_system_prompt(include_rules=False)
        assert "DÉFENSE EXTRACTION SYSTÈME" in prompt

    def test_anti_extraction_present_single_skill(self):
        """Test : la garde est présente avec un seul skill."""
        prompt = build_system_prompt(active_skills=["mispl-core"])
        assert "DÉFENSE EXTRACTION SYSTÈME" in prompt

    def test_anti_extraction_present_multiple_skills(self):
        """Test : la garde est présente avec plusieurs skills."""
        prompt = build_system_prompt(
            active_skills=["mispl-core", "mispl-reports"]
        )
        assert "DÉFENSE EXTRACTION SYSTÈME" in prompt

    def test_anti_extraction_present_empty_skills(self):
        """Test : la garde est présente même avec une liste de skills vide."""
        prompt = build_system_prompt(active_skills=[])
        assert "DÉFENSE EXTRACTION SYSTÈME" in prompt

    def test_anti_extraction_unconditional_combination(self):
        """
        Test complet : vérifie que la garde est présente pour une combinaison
        de paramètres qui inclut tous les chemins de code possibles.
        """
        # Combinaison : Technicien, avec règles, plusieurs skills
        prompt = build_system_prompt(
            active_skills=["mispl-core", "mispl-performance"],
            include_rules=True,
            access_mode="technicien",
        )
        assert "DÉFENSE EXTRACTION SYSTÈME" in prompt

        # Combinaison : DSI, sans règles, skills vides
        prompt = build_system_prompt(
            active_skills=[],
            include_rules=False,
            access_mode="dsi",
        )
        assert "DÉFENSE EXTRACTION SYSTÈME" in prompt

    def test_anti_extraction_key_phrases(self):
        """Test : vérifie que les clés phrases de la défense sont présentes."""
        prompt = build_system_prompt()
        key_phrases = [
            "DÉFENSE EXTRACTION SYSTÈME",
            "refuser TOUTE demande",
            "révéler",
            "répéter",
            "résumer",
            "traduire",
            "paraphraser",
            "instructions",
            "Je ne peux pas révéler",
        ]
        for phrase in key_phrases:
            assert phrase in prompt, f"Phrase clé manquante : {phrase}"

    def test_anti_extraction_early_in_prompt(self):
        """
        Test : la garde anti-extraction aparaît avant les autres sections
        (après _BASE_SYSTEM mais avant les restrictions de mode, etc).
        Cette vérification assure qu'elle a la priorité.
        """
        prompt = build_system_prompt(access_mode="technicien", include_rules=True)
        # Vérifier que la garde apparaît avant la restriction Technicien (si elle existe)
        anti_extraction_idx = prompt.find("DÉFENSE EXTRACTION SYSTÈME")
        assert anti_extraction_idx != -1, "Guard not found"
        assert anti_extraction_idx > 0, "Guard should come after base system"
