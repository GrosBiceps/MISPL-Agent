# ADR-0012 — Suppression de l'en-tête `<TYPE> PROGRAM`

## Statut

Accepté.

## Date

2026-09-24 (commit `02b3225`, `feat(agent): supprime l'en-tête « <TYPE>
PROGRAM », fiches utilitaires pour scripts, rappel mode Technicien`), à la
suite du banc de test temps réel (`scripts/claude_harness/`, voir ADR-0011).

## Contexte

Les premières versions du prompt système demandaient au LLM de faire
commencer chaque bloc de code MISPL généré par une ligne d'en-tête de la
forme `<TYPE> PROGRAM` (par exemple `LOGICAL PROGRAM`), reprenant une
convention observée dans des scripts MISPL réels. Le banc de test temps réel
du 2026-09-24, en confrontant l'agent à des questions réalistes, a montré que
cette ligne était **inutile dans le contexte réel d'usage de GLIMS** (le code
généré par l'agent est un extrait destiné à être intégré dans un script GLIMS
existant, pas un programme autonome complet), et qu'elle ajoutait du bruit
systématique à chaque réponse.

## Décision

Retirer la consigne de génération de la ligne d'en-tête `<TYPE> PROGRAM` du
prompt utilisateur de `ask_mispl()` (« N'écris JAMAIS de ligne d'en-tête
'<TYPE> PROGRAM' (inutile dans GLIMS). »), et incrémenter `CACHE_VERSION`
(`v31`) pour que les réponses déjà en cache avec l'ancien format expirent
sans être reservies.

## Alternatives étudiées

- **Rendre l'en-tête optionnel, laissé au jugement du LLM** : écarté — un
  format non déterministe aurait rendu les réponses moins prévisibles et
  moins faciles à valider automatiquement par le banc de test.
- **Conserver l'en-tête pour rester proche d'un style de script complet** :
  écarté — le constat du banc de test est que l'en-tête n'apporte pas
  d'information utile au technicien, qui insère le code dans un contexte
  GLIMS déjà structuré (règle de calcul, validation...).

## Conséquences

- Les réponses générées après ce changement sont plus courtes et plus
  directement utilisables (le code commence directement par les
  instructions utiles).
- Toute documentation, exemple ou test antérieur qui vérifiait la présence
  de cette ligne d'en-tête devait être mis à jour en cohérence (couvert par
  le même commit, qui inclut aussi l'ajustement des fiches utilitaires et du
  rappel de consigne du mode Technicien).
