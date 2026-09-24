# ADR-0008 — DLP contre les données patient envoyées au LLM

## Statut

Accepté.

## Date

Introduit le 2026-08-14 avec le mode d'accès (commit `a0050d6`, `feat(security):
mode d'accès DSI/Technicien + corrections d'audit`). Renforcé le 2026-08-17
(commit `b049b58`, `fix(security): escalate DLP to blocking on identifying-pattern
combinations`, et `1153353`, `fix(security): re-check DLP against conversation
history on every turn in Streamlit app`) et le 2026-08-25/27 (correction de
plusieurs contournements et faux positifs — noms au format worklist, dates de
naissance en toutes lettres, paires d'acronymes techniques).

## Contexte

Le LLM est un service tiers externe (OpenRouter). Une question ou un
contexte labo saisi par un technicien pourrait, par erreur ou par habitude
(copier-coller depuis une liste de travail GLIMS), contenir une information
permettant d'identifier un patient (nom, date de naissance, numéro de
sécurité sociale, identifiant de dossier). Le périmètre du projet exclut le
traitement de données patient (voir le cahier des charges), mais un filet de
sécurité applicatif est nécessaire.

## Décision

Filtrer, en code, **avant tout appel au LLM**, la question, le contexte labo
optionnel et l'historique de conversation, avec `src/security/dlp.py`. Les
motifs à haut risque individuellement bloquants (NIR/NISS, IPP/NIP) bloquent
toujours la requête. D'autres motifs, individuellement ambigus (une date
seule, un nom seul), ne bloquent pas isolément — pour ne pas produire trop de
faux positifs sur des questions techniques légitimes — mais une
**combinaison d'au moins deux motifs identifiants distincts** (par exemple un
nom et une date) est escaladée en blocage, car la combinaison est fortement
réidentifiante même si chaque élément pris seul ne l'est pas.

Le filtrage couvre explicitement le format « liste de travail » GLIMS (« NOM
Prénom, DATE » copié-collé sans titre), identifié comme le vecteur de fuite
le plus réaliste, et re-scanne l'historique de conversation à chaque tour
dans Streamlit (pas seulement le message courant).

## Alternatives étudiées

- **Blocage sur un seul motif, sans escalade combinatoire** : plus simple,
  mais laisse passer un nom et une date associés dans la même question si
  chacun, pris isolément, est jugé trop ambigu pour bloquer seul.
- **Blocage de tout nom capitalisé ou de toute date** : écarté — génère trop
  de faux positifs sur des questions techniques légitimes (un nom
  d'acronyme technique en majuscules, une date dans un exemple de code).
- **Aucun filtrage automatique, formation des utilisateurs uniquement** :
  écarté — un filet de sécurité applicatif reste nécessaire en complément
  de la formation, en particulier pour l'habitude de copier-coller depuis
  une liste de travail GLIMS.

## Conséquences

- Le DLP est un ensemble de règles par expression régulière, pas un modèle
  de détection d'entités nommées ; il nécessite un entretien régulier face
  aux contournements découverts (plusieurs correctifs successifs en
  août 2026).
- Un faux positif bloque une question technique légitime sans donnée
  patient réelle ; un faux négatif laisse passer une donnée potentiellement
  identifiante. Les deux types d'erreur ont fait l'objet de corrections
  documentées dans le `CHANGELOG.md`.
- Ce filtrage ne constitue pas, à lui seul, une garantie de conformité
  réglementaire complète ; il réduit le risque de fuite accidentelle vers un
  tiers. Le périmètre normal d'usage du produit reste des questions
  génériques sur la syntaxe MISPL, jamais des données patient réelles.
