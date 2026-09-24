# ADR-0010 — Garde-fou mécanique de faible évidence

## Statut

Accepté.

## Date

2026-08-26 (commit `b71ef02`, `feat(agent): add mechanical certainty guard
independent of LLM self-assessment`), corrigé le même jour (commit `c909848`,
ancrage de la regex en début de ligne pour ne pas rétrograder une mention en
prose) et le 2026-08-27 (commit `61c7989`, restauration du retrait des scores
à l'intérieur du garde-fou après une régression).

## Contexte

Le prompt système demande au LLM de qualifier sa réponse par un niveau de
certitude (✅ Certain, ⚠️ Probable, 🔬 À vérifier) en fonction de la qualité de
la documentation retrouvée. Un audit du 2026-08-27 a mis en évidence un cas
réel où **tous les scores de retrieval retournés étaient inférieurs à
0,17**, et où le LLM a malgré tout répondu « ✅ Certain » — l'auto-évaluation
demandée par consigne de prompt n'est pas fiable à 100 %.

## Décision

Appliquer, **en code, après génération**, un seuil mécanique indépendant du
jugement du LLM : si le meilleur score parmi les documents récupérés est
inférieur à `WEAK_EVIDENCE_SCORE_THRESHOLD = 0.50` (seuil aligné sur le seuil
« 🔬 À vérifier » déjà documenté dans le prompt système), la réponse est
systématiquement :
1. rétrogradée — toute occurrence de « ✅ Certain » en début de ligne est
   remplacée par « 🔬 À vérifier — documentation insuffisante pour
   confirmer » ;
2. précédée d'un bandeau « ⚠️ Documentation faible détectée », sauf pour les
   réponses où ce bandeau serait un bruit inutile (refus sans code du mode
   Technicien, refus d'extraction du prompt système, cas impossible, ou
   réponse qui annonce déjà elle-même l'absence de documentation via « ⚠️
   Fonction non trouvée »).

Ce garde-fou s'applique avant la mise en cache, pour que l'avertissement soit
systématiquement présent, que la réponse soit fraîchement générée ou servie
depuis le cache.

## Alternatives étudiées

- **Faire confiance uniquement à la consigne de prompt** : rejeté après
  l'audit du 2026-08-27, qui a montré un cas concret d'échec de
  l'auto-évaluation du LLM.
- **Bloquer entièrement la réponse en cas de score faible, plutôt que la
  rétrograder** : écarté — une documentation partielle n'est pas forcément
  inutilisable (elle peut orienter vers du pseudo-code exploitable), et le
  prompt système prévoit déjà ce cas via le niveau « 🔬 À vérifier ».
- **Bandeau systématique sans exemption** : écarté après le banc de test
  temps réel du 2026-09-24, qui a montré que le bandeau devenait un bruit
  sur des refus sans code (8 réponses concernées, cas IMP-003, PIJ-001,
  TEC-001).

## Conséquences

- La qualité perçue de l'agent dépend directement du calibrage du seuil
  (0,50) et de l'échelle de score produite par le pipeline de retrieval
  (RRF + reranking, voir ADR-0001) : un changement du pipeline de retrieval
  qui modifierait l'échelle des scores devrait revalider ce seuil.
- Le garde-fou agit indépendamment de la qualité réelle du code généré :
  une réponse peut être correcte mais tout de même rétrogradée si le score
  de retrieval est faible (biais volontairement prudent, cohérent avec
  l'objectif « zéro hallucination »).
- Un couplage étroit existe avec le retrait des scores de retrieval qui
  auraient fuité dans le texte (`_strip_leaked_retrieval_scores`) : la
  régression du 2026-08-27 a montré que ces deux traitements doivent rester
  appliqués ensemble sur toute réponse, y compris celle dégradée par ce
  garde-fou.
