"""Tests du module d'accès DSI/Technicien — mot de passe, prompt, barrière dure."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.security.access_mode import (
    MODE_DSI,
    MODE_TECHNICIEN,
    REFUSAL_MESSAGE,
    access_mode_for_user,
    build_restrictions_prompt,
    enforce_access_mode,
    generate_salt,
    hash_password,
    verify_dsi_password,
)


class TestPasswordHashing:
    def test_correct_password_verifies(self, monkeypatch):
        salt = generate_salt()
        digest = hash_password("un-bon-mdp-dsi", salt)
        monkeypatch.setenv("MISPL_DSI_PASSWORD_SALT", salt)
        monkeypatch.setenv("MISPL_DSI_PASSWORD_HASH", digest)
        assert verify_dsi_password("un-bon-mdp-dsi") is True

    def test_wrong_password_rejected(self, monkeypatch):
        salt = generate_salt()
        digest = hash_password("un-bon-mdp-dsi", salt)
        monkeypatch.setenv("MISPL_DSI_PASSWORD_SALT", salt)
        monkeypatch.setenv("MISPL_DSI_PASSWORD_HASH", digest)
        assert verify_dsi_password("mauvais-mdp") is False

    def test_empty_password_rejected(self, monkeypatch):
        salt = generate_salt()
        digest = hash_password("un-bon-mdp-dsi", salt)
        monkeypatch.setenv("MISPL_DSI_PASSWORD_SALT", salt)
        monkeypatch.setenv("MISPL_DSI_PASSWORD_HASH", digest)
        assert verify_dsi_password("") is False

    def test_missing_env_fails_safe_to_technicien(self, monkeypatch):
        # Fail-safe : si le hash n'est pas configuré, aucun mot de passe ne marche
        monkeypatch.delenv("MISPL_DSI_PASSWORD_SALT", raising=False)
        monkeypatch.delenv("MISPL_DSI_PASSWORD_HASH", raising=False)
        assert verify_dsi_password("nimporte-quoi") is False

    def test_different_salts_give_different_hashes(self):
        h1 = hash_password("same-password", generate_salt())
        h2 = hash_password("same-password", generate_salt())
        assert h1 != h2


class TestRestrictionsPrompt:
    def test_technicien_gets_restrictions(self):
        prompt = build_restrictions_prompt(MODE_TECHNICIEN)
        assert "WHILE" in prompt or "boucle" in prompt.lower()

    def test_dsi_gets_no_restrictions(self):
        assert build_restrictions_prompt(MODE_DSI) == ""


class TestEnforceAccessMode:
    def test_dsi_mode_never_blocks(self):
        response = "```mispl\nWHILE i < 10 DO\n  i := i + 1;\nDONE\n```"
        assert enforce_access_mode(response, MODE_DSI) == response

    def test_technicien_blocks_while_loop(self):
        response = "## Code MISPL\n```mispl\nWHILE i < 10 DO\n  i := i + 1;\nDONE\n```"
        result = enforce_access_mode(response, MODE_TECHNICIEN)
        assert result == REFUSAL_MESSAGE

    def test_technicien_blocks_repeat_loop(self):
        response = "```mispl\nREPEAT\n  i := i + 1;\nUNTIL i >= 10\n```"
        result = enforce_access_mode(response, MODE_TECHNICIEN)
        assert result == REFUSAL_MESSAGE

    def test_technicien_allows_loop_free_code(self):
        response = "## Code MISPL\n```mispl\nSTRING PROGRAM\n  RETURN Substr(\"abc\", 1, 2);\n```"
        assert enforce_access_mode(response, MODE_TECHNICIEN) == response

    def test_technicien_ignores_loop_keyword_outside_code_block(self):
        # Le mot "boucle"/"while" dans le texte explicatif ne doit pas déclencher
        # le refus — seul le code MISPL exécutable compte.
        response = "Cette fonction ne nécessite pas de boucle while.\n```mispl\nRETURN Today();\n```"
        assert enforce_access_mode(response, MODE_TECHNICIEN) == response

    def test_technicien_blocks_unfenced_while_loop(self):
        # F-01 : une boucle WHILE en pseudo-code MISPL sans aucun fencing
        # ``` doit être bloquée — le contournement historique de la barrière
        # dure consistait justement à demander une réponse non fenêtrée.
        response = (
            "Voici le code sans fence :\n"
            "STRING PROGRAM\n"
            "  WHILE i < 10 DO\n"
            "    i := i + 1;\n"
            "  DONE\n"
            "RETURN i;"
        )
        result = enforce_access_mode(response, MODE_TECHNICIEN)
        assert result == REFUSAL_MESSAGE

    def test_technicien_blocks_unfenced_repeat_loop(self):
        response = (
            "STRING PROGRAM\n"
            "  REPEAT\n"
            "    i := i + 1;\n"
            "  UNTIL i >= 10\n"
            "RETURN i;"
        )
        result = enforce_access_mode(response, MODE_TECHNICIEN)
        assert result == REFUSAL_MESSAGE

    def test_dsi_mode_unfenced_loop_not_blocked(self):
        # Mode DSI : la barrière dure ne s'applique pas, fenced ou non.
        response = (
            "STRING PROGRAM\n"
            "  WHILE i < 10 DO\n"
            "    i := i + 1;\n"
            "  DONE\n"
            "RETURN i;"
        )
        assert enforce_access_mode(response, MODE_DSI) == response

    def test_technicien_blocks_plain_fence_loop_without_program_keyword(self):
        # Régression (revue Critical) : une fence ``` générique, sans tag
        # `mispl` et sans le mot PROGRAM, n'est PAS extraite par
        # extract_mispl_blocks — elle ne doit donc pas non plus être retirée
        # aveuglément de l'analyse texte-brut, sinon la boucle qu'elle
        # contient devient invisible aux deux couches de vérification.
        response = (
            "Voici un extrait :\n"
            "```\n"
            "WHILE i < 10 DO\n"
            "  i := i + 1;\n"
            "DONE\n"
            "```"
        )
        result = enforce_access_mode(response, MODE_TECHNICIEN)
        assert result == REFUSAL_MESSAGE

    def test_technicien_allows_ordinary_prose_with_english_while(self):
        # "while" au sens anglais courant, dans une explication sans aucune
        # saveur MISPL à proximité, ne doit pas déclencher le refus.
        response = (
            "Cette approche reste valable while this works correctly on your "
            "current dataset, mais nécessite une revue si le volume augmente."
        )
        assert enforce_access_mode(response, MODE_TECHNICIEN) == response


class TestAccessModeForUser:
    def test_dsi_flag_true_gives_dsi_mode(self):
        assert access_mode_for_user(True) == MODE_DSI

    def test_dsi_flag_false_gives_technicien_mode(self):
        assert access_mode_for_user(False) == MODE_TECHNICIEN
