"""
DLP — filet de sécurité contre les données patient envoyées par erreur au LLM.

Vérifie TOUT texte destiné au LLM, y compris le contexte labo optionnel
(question_enriched), pas seulement la question brute — un IPP ou NIR tapé
dans le champ « Contexte labo » doit être bloqué au même titre.
"""

from __future__ import annotations

import re

_DLP_PATTERNS: list[tuple[re.Pattern, str, bool, bool]] = [
    # (pattern, label, is_blocking, is_identifying)
    # is_identifying: True if this pattern alone strongly suggests a specific patient
    # is targeted. When 2+ distinct identifying patterns match the same text, the
    # combination is escalated to blocking even if individually non-blocking —
    # e.g. a name plus a birth date together are highly re-identifying even though
    # a bare date or a bare name alone is common in legitimate technical questions.
    (re.compile(r'\b[12]\s?\d{2}\s?\d{2}\s?\d{2}\s?\d{3}\s?\d{3}\s?\d{2}\b'), "NIR/Numéro Sécu", True, True),
    (re.compile(r'\b\d{2}[01]\d[0-3]\d[-\s]?\d{3}[-\s]?\d{2}\b'), "NISS belge", True, True),
    (re.compile(r'\b(?:IPP|NIP|ipp|nip)\s*[:\-=]?\s*\d{5,10}\b', re.IGNORECASE), "IPP/NIP patient", True, True),
    (re.compile(r'\b(?:dossier|n°|num[ée]ro)\s*(?:patient|labo)?\s*[:\-#]?\s*\d{6,10}\b', re.IGNORECASE), "Identifiant dossier/patient potentiel", True, True),
    (re.compile(r'n.{0,2}e\s+le\s+\d{1,2}[/\-]\d{1,2}[/\-]\d{4}', re.IGNORECASE), "Date de naissance nominative", False, True),
    (re.compile(r'\b\d{2}[/\-]\d{2}[/\-]\d{4}\b'), "Date au format DD/MM/YYYY", False, False),
    (re.compile(r'\b(?:Mr?|Mme?|Dr?|patient|patiente)\s+[A-Z][a-z]+\s+[A-Z]{2,}', re.IGNORECASE), "Nom patient potentiel", False, True),
]


def dlp_check(text: str) -> tuple[bool, list[str]]:
    """Retourne (bloquant, alertes) — bloquant=True si un pattern à haut risque a matché,
    ou si 2+ patterns identifiants distincts matchent simultanément (ex: nom + date
    de naissance), même si chacun est individuellement non-bloquant."""
    blocked, alerts = False, []
    identifying_matches = 0
    for pattern, label, is_blocking, is_identifying in _DLP_PATTERNS:
        if pattern.search(text):
            alerts.append(label)
            if is_blocking:
                blocked = True
            if is_identifying:
                identifying_matches += 1
    if identifying_matches >= 2:
        blocked = True
    return blocked, alerts
