# ÉTAPE 4 — Plan de Remédiation et Recommandations

## 4.1 Solutions d'hébergement viables

### Option A — Déploiement cloud certifié HDS (recommandé pour la production)

| Hébergeur | Certification | Notes |
|---|---|---|
| **OVHcloud** | HDS + ISO 27001 + SecNumCloud | Français, souverain, GPU disponible |
| **Outscale (Dassault)** | HDS + SecNumCloud | Souverain, conformité ANSSI |
| **Scaleway** | HDS + ISO 27001 | Français, offre GPU (A100) |
| **Azure France Central** | HDS (via Microsoft MCA-FR) | Acceptable avec DPA signé |
| **AWS Paris** | HDS via Business Associate Agreement | Acceptable avec DPA signé |

> ⚠️ **OpenRouter (actuel)** : hébergement US, aucune certification HDS → **interdit pour données de santé**. Acceptable uniquement en développement sans données réelles.

### Option B — Déploiement on-premise (recommandé pour LBM à contraintes fortes)

Architecture cible :
```
[Poste utilisateur] ──LAN chiffré──> [Serveur on-premise LBM]
                                            │
                                    [LLM local: Ollama]
                                    [Vectorstore: ChromaDB]
                                    [App: Streamlit]
                                            │
                                    [Logs chiffrés]
                                    [Pas d'accès internet]
```

Prérequis serveur on-premise :
- Intégré au périmètre HDS de l'établissement (si LBM hospitalier)
- Ou certifié HDS indépendamment (si LBM privé)
- Chiffrement disque (LUKS/BitLocker) obligatoire
- Authentification forte (SSO établissement ou MFA local)

### Option C — Mode dev isolé (acceptable uniquement en développement)

- Poste développeur isolé du réseau de production
- **Aucune donnée patient réelle** dans les prompts ou les logs
- LLM local (Ollama + llama3/mistral) — aucun appel réseau externe
- Acceptable pour développement et démonstration sans données réelles

---

## 4.2 Mécanismes DLP (Data Loss Prevention) avant le LLM

### Objectif : détecter et bloquer les DCPS avant qu'elles atteignent le LLM

#### Architecture DLP recommandée

```python
# Couche DLP à insérer dans mispl_agent.py avant l'appel LLM
# Positionnement : entre la question utilisateur et la construction du prompt

def _dlp_scan(text: str) -> tuple[bool, str]:
    """
    Retourne (is_clean, sanitized_text).
    Si DCPS détectée : bloque OU anonymise selon la politique.
    """
    ...
```

#### Patterns à détecter (expressions régulières)

```python
DLP_PATTERNS = [
    # IPP / NIP belge (format standard)
    (r'\b\d{2}[01]\d[0-3]\d[-\s]?\d{3}[-\s]?\d{2}\b', "NISS/IPP"),
    # NIR français (sécurité sociale)
    (r'\b[12]\s?\d{2}\s?\d{2}\s?\d{2}\s?\d{3}\s?\d{3}\s?\d{2}\b', "NIR"),
    # Numéro IPP générique (7-10 chiffres isolés)
    (r'\b(?:IPP|NIP|ipp|nip)\s*[:\-]?\s*\d{6,10}\b', "IPP"),
    # Date de naissance avec nom (pattern "né(e) le")
    (r'n[ée]\s+le\s+\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}', "DateNaissance"),
    # Résultat nominatif ("patient X, résultat Y")
    (r'(?:patient|mr|mme|m\.)\s+[A-Z][a-z]+\s+[A-Z][a-z]+', "NomPatient"),
    # Valeurs biologiques nominatives
    (r'(?:HB|GB|PLT|CRP|créatinine|sodium)\s*[=:]\s*\d+[.,]?\d*\s*(?:g/dL|mmol/L|g/L|UI/L)', "ResultatNominatif"),
]
```

#### Politique recommandée

| Niveau de risque | Action | Exemple |
|---|---|---|
| **CRITIQUE** (NIR, IPP explicite) | **Bloquer + alerter** | Afficher message d'erreur, ne pas envoyer au LLM |
| **ÉLEVÉ** (nom + date naissance) | **Anonymiser + avertir** | Remplacer par [PATIENT_ANONYME] |
| **MODÉRÉ** (résultat isolé sans nom) | **Avertir** | Warning visible, laisser passer |

#### Implémentation dans app.py

```python
# Dans app.py, avant l'appel à _ask_mispl()
def _apply_dlp(question: str) -> tuple[str, list[str]]:
    """
    Retourne (question_nettoyée, liste_alertes).
    Bloque si DCPS critique détectée.
    """
    alerts = []
    for pattern, label in DLP_PATTERNS:
        if re.search(pattern, question, re.IGNORECASE):
            if label in ("NIR", "IPP"):
                raise DLPBlockedError(f"Donnée sensible détectée ({label}). Ne pas inclure de données patient.")
            else:
                question = re.sub(pattern, f"[{label}_ANONYMISÉ]", question, flags=re.IGNORECASE)
                alerts.append(f"⚠️ Donnée potentiellement sensible ({label}) anonymisée.")
    return question, alerts
```

---

## 4.3 Mentions légales et Disclaimers obligatoires

### Disclaimer à afficher en permanence dans l'interface Streamlit

```
⚠️ AVERTISSEMENT RÉGLEMENTAIRE

Cet outil génère des scripts MISPL à partir d'une base documentaire technique.
Il ne constitue PAS un dispositif médical et ne pose PAS de diagnostic.

AVANT toute mise en production d'un script généré :
• Validation obligatoire par un biologiste médical responsable
• Tests en environnement de recette GLIMS
• Enregistrement dans le registre des modifications du SIL

NE PAS inclure de données patient dans vos questions :
• Pas de numéro IPP/NIP
• Pas de résultats nominatifs  
• Pas de données identifiantes

Conformément au RGPD et au Code de la Santé Publique (Art. L.1111-8),
toute question contenant des données de santé engage votre responsabilité.
```

### Conditions d'utilisation (à faire accepter à la 1ère connexion)

```markdown
CONDITIONS D'UTILISATION — MISPL Agent

1. CET OUTIL EST RÉSERVÉ À UN USAGE DE PARAMÉTRAGE TECHNIQUE
   L'utilisateur reconnaît utiliser cet outil uniquement pour 
   générer des scripts de paramétrage GLIMS, sans finalité diagnostique.

2. RESPONSABILITÉ DE VALIDATION
   Tout script généré par cet outil doit être validé par un biologiste
   médical habilité avant déploiement en production (ISO 15189 §6.6).

3. INTERDICTION DE SAISIE DE DONNÉES PATIENT
   L'utilisateur s'engage à ne pas inclure de données à caractère 
   personnel de santé dans ses questions (RGPD Art. 9).

4. ABSENCE DE GARANTIE MÉDICALE
   Les scripts générés sont fournis à titre indicatif. L'établissement
   reste seul responsable de leur conformité clinique et réglementaire.

5. TRAÇABILITÉ
   Les questions posées peuvent être enregistrées à des fins d'audit
   interne conformément à la politique RSSI de l'établissement.

[ J'accepte ces conditions ] [ Refuser ]
```

---

## 4.4 Feuille de route de mise en conformité

### Priorité 1 — Actions immédiates (avant tout usage avec données réelles)

```
☐ Implémenter le filtre DLP dans app.py
☐ Ajouter le disclaimer permanent dans l'interface
☐ Créer la procédure de validation des scripts (document qualité)
☐ Informer le DPO de l'établissement de l'existence de l'outil
```

### Priorité 2 — Avant déploiement en production (J+30)

```
☐ Migrer l'hébergement vers une solution HDS si LLM cloud utilisé
   OU configurer LLM on-premise (Ollama) sans accès internet
☐ Rédiger la fiche AIPD (Analyse d'Impact Protection des Données)
   si traitement à grande échelle prévu
☐ Signer un DPA avec chaque fournisseur de service impliqué
☐ Former les utilisateurs aux bonnes pratiques (1 heure minimum)
☐ Mettre en place le registre des scripts générés (traçabilité)
```

### Priorité 3 — Conformité durable (J+90)

```
☐ Intégrer l'outil dans le système de management qualité du LBM
☐ Réaliser une première revue annuelle de l'outil (mise à jour doc)
☐ Évaluer l'impact sur la portée d'accréditation COFRAC
   (informer le COFRAC si modification substantielle du SIL)
☐ Auditer les logs d'utilisation (vérifier absence de DCPS)
```

---

## 4.5 Matrice des risques résiduels après remédiation

| Risque | Probabilité avant | Probabilité après DLP | Impact |
|---|---|---|---|
| DCPS transmise au LLM cloud | Élevée | Très faible (DLP actif) | CRITIQUE |
| Script erroné mis en prod sans validation | Élevée | Faible (procédure VAB/VAF) | ÉLEVÉ |
| Violation HDS en mode local | Modérée | Très faible (pas de stockage DCPS) | ÉLEVÉ |
| Qualification DM inattendue | Très faible | Très faible | MODÉRÉ |
| Non-conformité COFRAC | Modérée | Faible (procédures en place) | MODÉRÉ |
