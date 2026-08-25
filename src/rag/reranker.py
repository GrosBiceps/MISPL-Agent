"""
Reranker cross-encoder — score de pertinence sémantique réel entre la question
et chaque chunk candidat, en remplacement des anciens boosts heuristiques
arbitraires post-RRF (×1.12/×1.08/×1.04, cf. src/rag/retriever.py).

Modèle multilingue (corpus et questions MISPL Agent majoritairement en
français) : cross-encoder/mmarco-mMiniLMv2-L12-H384-v1, chargé via
sentence-transformers (déjà une dépendance du projet — aucun ajout requis).

Repli automatique sur l'ordre d'entrée en cas d'échec (modèle non chargeable,
erreur d'inférence, désactivation via variable d'env) — ne doit jamais faire
échouer une requête de chat.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)

RERANKER_MODEL_NAME = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"

_cross_encoder = None
_load_failed = False


def _rerank_enabled() -> bool:
    return os.environ.get("MISPL_RERANK_ENABLED", "true").strip().lower() not in ("false", "0", "no")


def _get_cross_encoder():
    """Singleton lazy — charge le modèle une seule fois par process. Retourne
    None si le chargement échoue (mémorisé pour ne pas retenter à chaque appel)."""
    global _cross_encoder, _load_failed
    if _cross_encoder is not None or _load_failed:
        return _cross_encoder
    try:
        from sentence_transformers import CrossEncoder

        _cross_encoder = CrossEncoder(RERANKER_MODEL_NAME)
    except Exception as e:
        logger.warning(f"Reranker : échec de chargement du modèle ({e}), repli sur l'ordre RRF")
        _load_failed = True
        _cross_encoder = None
    return _cross_encoder


def rerank(query: str, docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Trie `docs` par pertinence sémantique réelle (cross-encoder) au lieu du
    score RRF/heuristique. Retourne une NOUVELLE liste de nouveaux dicts (ne
    mute jamais `docs` ni ses éléments). En cas d'échec à n'importe quelle
    étape (désactivé, modèle non chargeable, erreur d'inférence), retourne
    `docs` inchangé (mêmes objets, même ordre) — jamais d'exception propagée.
    """
    if not docs or not _rerank_enabled():
        return docs

    model = _get_cross_encoder()
    if model is None:
        return docs

    try:
        start = time.monotonic()
        pairs = [(query, d.get("text", "")) for d in docs]
        scores = model.predict(pairs)
        elapsed_ms = (time.monotonic() - start) * 1000
        logger.info(f"Reranker : {len(docs)} candidats en {elapsed_ms:.0f}ms")
        reranked = []
        for doc, score in zip(docs, scores):
            new_doc = dict(doc)
            new_doc["score"] = float(score)
            reranked.append(new_doc)
        reranked.sort(key=lambda d: d["score"], reverse=True)
        return reranked
    except Exception as e:
        logger.warning(f"Reranker : échec à l'inférence ({e}), repli sur l'ordre d'entrée")
        return docs
