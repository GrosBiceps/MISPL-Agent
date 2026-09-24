"""Tests du module d'accès DSI/Technicien — mot de passe, prompt, barrière dure."""

import hashlib
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.security.access_mode import (
    MODE_DSI,
    MODE_TECHNICIEN,
    REFUSAL_MESSAGE,
    access_mode_for_user,
    build_restrictions_prompt,
    dsi_password_format,
    dsi_password_needs_upgrade,
    enforce_access_mode,
    hash_dsi_password,
    verify_dsi_password,
)


class TestPasswordHashing:
    """Mot de passe DSI : Argon2id depuis le 2026-09-24, ancien PBKDF2 encore
    vérifié (compatibilité) avec invitation à regénérer."""

    def _set_argon2(self, monkeypatch, password="un-bon-mdp-dsi"):
        monkeypatch.delenv("MISPL_DSI_PASSWORD_SALT", raising=False)
        monkeypatch.setenv("MISPL_DSI_PASSWORD_HASH", hash_dsi_password(password))

    def _set_legacy(self, monkeypatch, password="un-bon-mdp-dsi"):
        salt = os.urandom(16).hex()
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), 200_000).hex()
        monkeypatch.setenv("MISPL_DSI_PASSWORD_SALT", salt)
        monkeypatch.setenv("MISPL_DSI_PASSWORD_HASH", digest)

    def test_new_hash_is_argon2id_with_shared_parameters(self):
        h = hash_dsi_password("un-bon-mdp-dsi")
        assert h.startswith("$argon2id$v=19$m=65536,t=3,p=4$")
        assert "un-bon-mdp-dsi" not in h

    def test_correct_password_verifies(self, monkeypatch):
        self._set_argon2(monkeypatch)
        assert verify_dsi_password("un-bon-mdp-dsi") is True
        assert dsi_password_format() == "argon2id"
        assert dsi_password_needs_upgrade() is False

    def test_wrong_password_rejected(self, monkeypatch):
        self._set_argon2(monkeypatch)
        assert verify_dsi_password("mauvais-mdp") is False

    def test_empty_password_rejected(self, monkeypatch):
        self._set_argon2(monkeypatch)
        assert verify_dsi_password("") is False

    def test_missing_env_fails_safe_to_technicien(self, monkeypatch):
        # Fail-safe : si le hash n'est pas configuré, aucun mot de passe ne marche
        monkeypatch.delenv("MISPL_DSI_PASSWORD_SALT", raising=False)
        monkeypatch.delenv("MISPL_DSI_PASSWORD_HASH", raising=False)
        assert verify_dsi_password("nimporte-quoi") is False
        assert dsi_password_format() == "absent"

    def test_corrupted_argon2_hash_fails_safe(self, monkeypatch):
        monkeypatch.setenv("MISPL_DSI_PASSWORD_HASH", "$argon2id$v=19$m=65536,t=3,p=4$abc$def")
        assert verify_dsi_password("un-bon-mdp-dsi") is False

    def test_same_password_gives_different_hashes(self):
        assert hash_dsi_password("same-password") != hash_dsi_password("same-password")

    def test_legacy_pbkdf2_still_verifies_with_upgrade_warning(self, monkeypatch, caplog):
        self._set_legacy(monkeypatch)
        with caplog.at_level(logging.WARNING):
            assert verify_dsi_password("un-bon-mdp-dsi") is True
        assert dsi_password_format() == "pbkdf2-legacy"
        assert dsi_password_needs_upgrade() is True
        assert "set_dsi_password.py" in caplog.text
        assert "un-bon-mdp-dsi" not in caplog.text

    def test_legacy_pbkdf2_wrong_password_rejected(self, monkeypatch):
        self._set_legacy(monkeypatch)
        assert verify_dsi_password("mauvais-mdp") is False

    def test_legacy_without_salt_fails_safe(self, monkeypatch):
        self._set_legacy(monkeypatch)
        monkeypatch.delenv("MISPL_DSI_PASSWORD_SALT")
        assert verify_dsi_password("un-bon-mdp-dsi") is False

    def test_weak_argon2_hash_flagged_for_upgrade(self, monkeypatch):
        from argon2 import PasswordHasher
        monkeypatch.delenv("MISPL_DSI_PASSWORD_SALT", raising=False)
        monkeypatch.setenv(
            "MISPL_DSI_PASSWORD_HASH",
            PasswordHasher(time_cost=1, memory_cost=8192, parallelism=1).hash("un-bon-mdp-dsi"),
        )
        assert verify_dsi_password("un-bon-mdp-dsi") is True
        assert dsi_password_needs_upgrade() is True


class TestSetDsiPasswordScript:
    def _load(self):
        import importlib.util
        path = Path(__file__).parent.parent.parent / "scripts" / "set_dsi_password.py"
        spec = importlib.util.spec_from_file_location("set_dsi_password", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_replaces_legacy_lines_and_keeps_others(self):
        script = self._load()
        lines = [
            "OPENROUTER_API_KEY=cle-factice\n",
            "MISPL_DSI_PASSWORD_SALT=00ff\n",
            "MISPL_DSI_PASSWORD_HASH=abcdef\n",
            "PYTHONUTF8=1",
        ]
        h = hash_dsi_password("un-bon-mdp-dsi")
        text = "".join(script.update_env_lines(lines, h))
        assert "MISPL_DSI_PASSWORD_SALT" not in text
        assert f"MISPL_DSI_PASSWORD_HASH='{h}'" in text
        assert "OPENROUTER_API_KEY=cle-factice" in text and "PYTHONUTF8=1" in text
        assert "un-bon-mdp-dsi" not in text

    def test_written_value_roundtrips_through_dotenv(self, tmp_path, monkeypatch):
        """Le hash contient des « $ » : entre apostrophes, python-dotenv ne
        doit pas les interpréter, et la vérification doit réussir après relecture."""
        from dotenv import dotenv_values
        script = self._load()
        h = hash_dsi_password("un-bon-mdp-dsi")
        env_file = tmp_path / ".env"
        env_file.write_text("".join(script.update_env_lines([], h)), encoding="utf-8")
        values = dotenv_values(env_file)
        assert values["MISPL_DSI_PASSWORD_HASH"] == h
        monkeypatch.delenv("MISPL_DSI_PASSWORD_SALT", raising=False)
        monkeypatch.setenv("MISPL_DSI_PASSWORD_HASH", values["MISPL_DSI_PASSWORD_HASH"])
        assert verify_dsi_password("un-bon-mdp-dsi") is True


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

    def test_technicien_allows_prose_refusal_citing_htm_source(self):
        # Régression (revue finale) : un refus légitime en mode Technicien,
        # rédigé en prose et citant sa source au format `## Source` obligatoire
        # (CLAUDE.md, ex: "function_string.htm"), ne doit PAS être écrasé par
        # REFUSAL_MESSAGE. Avant le correctif, le bras `.Champ` du pattern de
        # saveur MISPL matchait n'importe quel point suivi d'un mot (donc
        # ".htm" dans la citation) sous IGNORECASE, et RETURN comptait comme
        # marqueur de saveur — la combinaison avec WHILE dans la même fenêtre
        # de proximité déclenchait à tort le remplacement.
        response = (
            "Une boucle WHILE serait nécessaire, mais elle est interdite en "
            "mode Technicien.\n"
            'Source : function_string.htm — section "Substr"'
        )
        assert enforce_access_mode(response, MODE_TECHNICIEN) == response


class TestAccessModeForUser:
    def test_dsi_flag_true_gives_dsi_mode(self):
        assert access_mode_for_user(True) == MODE_DSI

    def test_dsi_flag_false_gives_technicien_mode(self):
        assert access_mode_for_user(False) == MODE_TECHNICIEN


class TestUnfencedLoopMentions:
    """Banc temps réel 2026-09-24 (ORD-001) : une mention en prose des
    mots-clés de boucle ne doit pas remplacer une réponse valide sans boucle,
    tandis que toute boucle structurée hors bloc reste bloquée."""

    ORD_001 = (
        "## Code MISPL\n```mispl\nLOGICAL PROGRAM\n"
        "  RETURN Action.Order().IsRequested(\"TSH\", NO);\n```\n\n"
        "## Notes techniques\n"
        "- Alternative : `Action.Order().Result(\"TSH\", ?, ?).Id <> ?`.\n"
        "- Aucune boucle WHILE/REPEAT requise — pattern conforme au mode technicien.\n"
    )

    def test_prose_mention_next_to_accessor_is_not_blocked(self):
        assert enforce_access_mode(self.ORD_001, MODE_TECHNICIEN) == self.ORD_001

    def test_unfenced_while_do_mid_sentence_still_blocked(self):
        response = "Il suffit d'écrire WHILE i < 10 DO i := i + 1; DONE dans le script."
        assert enforce_access_mode(response, MODE_TECHNICIEN) == REFUSAL_MESSAGE

    def test_unfenced_repeat_with_long_body_still_blocked(self):
        body = "".join(f"  x{n} := {n};\n" for n in range(8))
        response = f"Voici :\nREPEAT\n{body}UNTIL x7 > 0\n"
        assert enforce_access_mode(response, MODE_TECHNICIEN) == REFUSAL_MESSAGE

    def test_statement_position_loop_without_done_still_blocked(self):
        response = "STRING PROGRAM\n  WHILE i < 10\n    i := i + 1;\nRETURN i;"
        assert enforce_access_mode(response, MODE_TECHNICIEN) == REFUSAL_MESSAGE

    def test_bulleted_statement_loop_still_blocked(self):
        response = "- WHILE .Next <> ?\n  x := .Next;"
        assert enforce_access_mode(response, MODE_TECHNICIEN) == REFUSAL_MESSAGE
