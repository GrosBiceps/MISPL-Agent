"""Tests du hachage Argon2id et de la génération de mot de passe temporaire."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.security import generate_temp_password, hash_password, verify_password


class TestPasswordHashing:
    def test_verify_correct_password(self):
        h = hash_password("MotDePasseRobuste1!")
        assert verify_password("MotDePasseRobuste1!", h) is True

    def test_verify_wrong_password(self):
        h = hash_password("MotDePasseRobuste1!")
        assert verify_password("AutreChose", h) is False

    def test_same_password_different_hash_each_time(self):
        h1 = hash_password("MotDePasseRobuste1!")
        h2 = hash_password("MotDePasseRobuste1!")
        assert h1 != h2  # sel aléatoire à chaque hash

    def test_verify_against_garbage_hash_does_not_raise(self):
        assert verify_password("quoiquecesoit", "pas-un-hash-valide") is False


class TestTempPasswordGeneration:
    def test_default_length(self):
        assert len(generate_temp_password()) == 14

    def test_custom_length(self):
        assert len(generate_temp_password(length=20)) == 20

    def test_two_calls_differ(self):
        assert generate_temp_password() != generate_temp_password()
