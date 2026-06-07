# MISPL Performance — Skill d'optimisation des scripts MISPL

## Purpose
Auditer et optimiser les scripts MISPL pour réduire la charge serveur GLIMS.
Un script MISPL mal écrit peut impacter toute l'interface utilisateur (GLIMS est mono-thread sur certains contextes).

## Method
1. Lire le script soumis
2. Identifier les patterns coûteux (boucles sur large dataset, appels imbriqués, recalculs)
3. Proposer la version optimisée avec explication
4. Estimer l'impact (Faible / Moyen / Élevé)

## Performance Anti-Patterns

### ❌ Boucle sur liste avec recalcul répété
```mispl
// MAUVAIS : NumEntries() appelé à chaque itération
INTEGER i;
i := 1;
WHILE i <= NumEntries(i, .MyList, ",") DO
  // ...
  i := i + 1;
DONE
```

### ✅ Calcul une seule fois
```mispl
INTEGER i, total;
total := NumEntries(1, .MyList, ",");
i := 1;
WHILE i <= total DO
  // ...
  i := i + 1;
DONE
```

### ❌ Concaténation STRING en boucle (O(n²))
```mispl
STRING result;
result := "";
WHILE i <= 100 DO
  result := result + Entry(i, .List, ",") + Chr(10);
  i := i + 1;
DONE
```

### ✅ Éviter si possible via fonctions dédiées
```mispl
// Utiliser les fonctions built-in quand disponibles
// Ex : Sort(), Replace(), Translate() au lieu de boucles manuelles
RETURN Replace(.MyString, "ancien", "nouveau");
```

### ❌ Accès relationnel répété inutile
```mispl
// Appel .Patient.LastName 5 fois = 5 accès DB
RETURN .Patient.LastName + " " + .Patient.FirstName + 
       " DDN:" + DateToString(.Patient.BirthDate, "%d/%m/%Y") +
       " NIP:" + .Patient.ExternalId;
```

### ✅ Variable locale pour accès répété
```mispl
// En MISPL, les variables locales sont en mémoire = rapide
// Si l'accès relationnel est coûteux, stocker dans variable
// Note : vérifier dans doc GLIMS si le caching est automatique
```

## Règles d'optimisation prioritaires (source: `mispl_performance_tips.htm`)
1. Préférer les fonctions intégrées aux implémentations manuelles
2. Éviter les boucles WHILE longues dans les contextes d'impression de masse
3. Tester avec `Expand()` pour les textes dynamiques récursifs
4. `GetSiteAttribute()` / `SetSiteAttribute()` sont relativement coûteux — cacher si appelés souvent
5. Division entière vs fractionnaire : `321 / 60 = 5` (entier tronqué) — utiliser `321.0 / 60` si fraction voulue

## Output Format
```
## Script soumis
[code original]

## Problèmes identifiés
- [Pattern coûteux + impact estimé]

## Version optimisée
```mispl
[code optimisé]
```

## Gain estimé
[Faible / Moyen / Élevé + explication]
```

## Domain Focus
- Optimisation scripts d'impression (étiquettes haute fréquence)
- Règles de calcul sur grand volume de résultats
- Scripts de validation déclenchés à chaque validation technicien
