"""
Tests de la clé de cache et de la robustesse du cache disque de mispl_agent.

Vérifie en particulier le correctif de l'audit : la clé de cache doit varier
avec skill_profile / access_mode / historique, sinon une réponse DSI mise en
cache pourrait être resservie telle quelle à une session Technicien (ou une
réponse générée avec un historique donné resservie hors contexte).
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import src.agent.mispl_agent as agent_mod
from src.agent.mispl_agent import _cache_get, _cache_key


class TestCacheKeyIsolation:
    def _key(self, **overrides):
        base = dict(
            question="Comment utiliser Substr ?",
            model="nvidia/nemotron-3-super-120b-a12b:free",
            top_k=6,
            skill_profile=None,
            access_mode="dsi",
            conversation_history=None,
        )
        base.update(overrides)
        return _cache_key(**base)

    def test_same_inputs_same_key(self):
        assert self._key() == self._key()

    def test_different_access_mode_different_key(self):
        assert self._key(access_mode="dsi") != self._key(access_mode="technicien")

    def test_different_skill_profile_different_key(self):
        assert self._key(skill_profile=["mispl-core"]) != self._key(skill_profile=["mispl-reports"])

    def test_different_history_different_key(self):
        hist_a = [{"role": "user", "content": "question précédente A"}]
        hist_b = [{"role": "user", "content": "question précédente B"}]
        assert self._key(conversation_history=hist_a) != self._key(conversation_history=hist_b)

    def test_different_question_different_key(self):
        assert self._key(question="A") != self._key(question="B")


class TestCacheGetRobustness:
    def test_missing_file_returns_none(self, tmp_path, monkeypatch):
        import src.agent.mispl_agent as agent_mod
        monkeypatch.setattr(agent_mod, "CACHE_DIR", tmp_path)
        assert _cache_get("does-not-exist") is None

    def test_corrupted_json_does_not_raise(self, tmp_path, monkeypatch):
        import src.agent.mispl_agent as agent_mod
        monkeypatch.setattr(agent_mod, "CACHE_DIR", tmp_path)
        bad_file = tmp_path / "corrupted.json"
        bad_file.write_text("{not valid json", encoding="utf-8")
        # Ne doit jamais lever d'exception — juste ignorer le cache corrompu
        assert _cache_get("corrupted") is None
        # Le fichier corrompu doit être supprimé pour ne pas re-planter au tick suivant
        assert not bad_file.exists()

    def test_valid_fresh_cache_returns_data(self, tmp_path, monkeypatch):
        import src.agent.mispl_agent as agent_mod
        import datetime
        monkeypatch.setattr(agent_mod, "CACHE_DIR", tmp_path)
        entry = tmp_path / "fresh.json"
        entry.write_text(json.dumps({
            "ts": datetime.datetime.now().timestamp(),
            "response": "reponse test",
            "docs": [{"function_name": "Substr"}],
        }), encoding="utf-8")
        result = _cache_get("fresh")
        assert result == ("reponse test", [{"function_name": "Substr"}])


class TestCachePurge:
    def test_purges_files_older_than_retention(self, tmp_path, monkeypatch):
        monkeypatch.setattr(agent_mod, "CACHE_DIR", tmp_path)
        old_file = tmp_path / "old.json"
        old_file.write_text("{}", encoding="utf-8")
        import os as _os
        import time as _time
        old_time = _time.time() - 2 * 3600  # 2h dans le passé
        _os.utime(old_file, (old_time, old_time))

        removed = agent_mod.purge_old_cache(max_age_hours=1)
        assert removed == 1
        assert not old_file.exists()

    def test_keeps_recent_files(self, tmp_path, monkeypatch):
        monkeypatch.setattr(agent_mod, "CACHE_DIR", tmp_path)
        recent_file = tmp_path / "recent.json"
        recent_file.write_text("{}", encoding="utf-8")

        removed = agent_mod.purge_old_cache(max_age_hours=24)
        assert removed == 0
        assert recent_file.exists()

    def test_missing_cache_dir_returns_zero(self, tmp_path, monkeypatch):
        missing = tmp_path / "does-not-exist"
        monkeypatch.setattr(agent_mod, "CACHE_DIR", missing)
        assert agent_mod.purge_old_cache() == 0
