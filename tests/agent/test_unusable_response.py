"""Réponses inexploitables (raisonnement à voix haute, fuite des consignes).

Incident 2026-10-23 (dots-3-note-preview via le routeur) : le modèle a recopié
la consigne « repondre UNIQUEMENT '## Contexte GLIMS' puis… » dans son
raisonnement, tronqué par max_tokens. _strip_chain_of_thought coupait sur ce
marqueur cité et la consigne interne était affichée au technicien.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import src.agent.mispl_agent as agent_mod

INCIDENT_RESPONSE = (
    "We need to answer. The instruction says: if impossible, repondre UNIQUEMENT "
    "'## Contexte GLIMS' puis, a la ligne, 'impossible via MISPL — se fait via la "
    "configuration GLIMS.' (une phrase d'explication au plus), SANS bloc de code, "
    "SANS pseudo-code, SANS inventer CreatePatient/CreatePerson/CreateObject. Une "
    "fonction nommee dans la question mais absente des extraits ne doit JAMAIS etre "
    "appelee, meme en pseudo-code.\"\n\nThis is about functions named in the question "
    "but absent from extracts.\n\nSo I"
)

GOOD_RESPONSE = (
    "## Contexte GLIMS\nFormatage de la date du jour.\n\n"
    "## Code MISPL\n```\nDateTimeToString(Today(), \"DD/MM/YYYY\")\n```"
)


def _completion(content, finish_reason="stop"):
    c = MagicMock()
    c.choices = [MagicMock()]
    c.choices[0].message.content = content
    c.choices[0].finish_reason = finish_reason
    return c


class TestUnusableResponse:
    def test_incident_response_is_rejected(self):
        assert agent_mod._is_unusable_response(INCIDENT_RESPONSE, "length")
        assert agent_mod._is_unusable_response(INCIDENT_RESPONSE, "stop")

    def test_quoted_marker_is_not_answer_start(self):
        assert agent_mod._first_answer_marker(INCIDENT_RESPONSE) is None

    def test_good_answer_kept(self):
        assert not agent_mod._is_unusable_response(GOOD_RESPONSE, "stop")

    def test_cot_preamble_then_real_answer_is_kept_and_stripped(self):
        text = "Okay, let me check the docs for Today.\n" + GOOD_RESPONSE
        assert not agent_mod._is_unusable_response(text, "stop")
        assert agent_mod._strip_chain_of_thought(text).startswith("## Contexte GLIMS")

    def test_refusals_without_marker_are_kept(self):
        assert not agent_mod._is_unusable_response("🔒 Génération réservée au mode DSI", "stop")

    def test_truncated_reasoning_rejected(self):
        assert agent_mod._is_unusable_response("The user wants to format today's date. I", "length")
        assert agent_mod._is_unusable_response("", "stop")

    def test_fallback_skips_unusable_model(self, monkeypatch):
        monkeypatch.setattr(agent_mod, "FALLBACK_ORDER", ["bad/model", "good/model"])
        client = MagicMock()
        client.chat.completions.create.side_effect = lambda **kw: (
            _completion(INCIDENT_RESPONSE, "length") if kw["model"] == "bad/model" else _completion(GOOD_RESPONSE)
        )
        used, completion = agent_mod._call_with_fallback(client, "bad/model", messages=[])
        assert used == "good/model"
        assert completion.choices[0].message.content == GOOD_RESPONSE
