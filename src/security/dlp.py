"""
DLP — filet de sécurité contre les données patient envoyées par erreur au LLM.

Vérifie TOUT texte destiné au LLM, y compris le contexte labo optionnel
(question_enriched), pas seulement la question brute — un IPP ou NIR tapé
dans le champ « Contexte labo » doit être bloqué au même titre.
"""

from __future__ import annotations

import re

_DLP_PATTERNS: list[tuple[re.Pattern, str, bool]] = [
    (re.compile(r'\b[12]\s?\d{2}\s?\d{2}\s?\d{2}\s?\d{3}\s?\d{3}\s?\d{2}\b'), "NIR/Numéro Sécu", True),
    (re.compile(r'\b\d{2}[01]\d[0-3]\d[-\s]?\d{3}[-\s]?\d{2}\b'), "NISS belge", True),
    (re.compile(r'\b(?:IPP|NIP|ipp|nip)\s*[:\-=]?\s*\d{5,10}\b', re.IGNORECASE), "IPP/NIP patient", True),
    (re.compile(r'n.{0,2}e\s+le\s+\d{1,2}[/\-]\d{1,2}[/\-]\d{4}', re.IGNORECASE), "Date de naissance nominative", False),
    (re.compile(r'\b\d{2}[/\-]\d{2}[/\-]\d{4}\b'), "Date au format DD/MM/YYYY", False),
    (re.compile(r'\b(?:Mr?|Mme?|Dr?|patient|patiente)\s+[A-Z][a-z]+\s+[A-Z]{2,}', re.IGNORECASE), "Nom patient potentiel", False),
]


def dlp_check(text: str) -> tuple[bool, list[str]]:
    """Retourne (bloquant, alertes) — bloquant=True si un pattern à haut risque a matché."""
    blocked, alerts = False, []
    for pattern, label, is_blocking in _DLP_PATTERNS:
        if pattern.search(text):
            alerts.append(label)
            if is_blocking:
                blocked = True
    return blocked, alerts
