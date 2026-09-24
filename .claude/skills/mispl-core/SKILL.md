# MISPL Core — Skill de génération de code MISPL

## Purpose
Générer, expliquer et déboguer du code MISPL pour GLIMS/Clinisys.
Contrainte absolue : zéro hallucination, toujours sourcer depuis la documentation RAG.

## Method
1. Analyser la demande : type de programme (texte / expression / règle métier)
2. Interroger le RAG : récupérer les fonctions MISPL pertinentes avec leur syntaxe exacte
3. Vérifier le type de retour attendu (INTEGER / STRING / LOGICAL / DATE / FRACTIONAL)
4. Construire le programme avec déclarations de variables en tête
5. Gérer les valeurs inconnues (`?`) — ne jamais les ignorer
6. Citer la source documentaire pour chaque fonction utilisée
7. Qualifier le niveau de certitude global

## Syntax Rules
```
  [DECLARATIONS]
  [STATEMENTS]
RETURN expression;
```

Déclarations obligatoires avant usage :
```mispl
STRING result, temp;
INTEGER counter;
LOGICAL flag;
DATE birthdate;
```

## Anti-Hallucination Protocol
- Chercher la fonction dans RAG AVANT de l'utiliser
- Si absente → pseudo-code avec commentaire `/* À VÉRIFIER dans GLIMS */`, sans jamais appeler la fonction absente
- Ne jamais inventer de paramètres non documentés
- Si plusieurs surcharges existent → lister toutes les signatures

## Common Patterns

### Formatage d'identifiant échantillon
```mispl
  STRING prefix, num;
  prefix := DateToString(Today(), "%Y%m%d");
  num := IntegerToString(NextValue("SampleCounter"), "%05d");
RETURN prefix + "-" + num;
```
Source : `rag_knowledge_base/02_functions/datetime/datetime_functions.md`, `rag_knowledge_base/02_functions/conversion/conversion_functions.md`, `rag_knowledge_base/02_functions/misc/misc_functions.md`

### Gestion valeur inconnue
```mispl
  STRING val;
  val := .SomeField;
  IF val = ? THEN
    RETURN FALSE;
  ENDIF;
RETURN val <> "";
```

### Log d'audit obligatoire
```mispl
  LOGICAL ok;
  ok := AddLogEntry("Sample", .Id, "RESULT_CHANGE", Info, FALSE,
    "Résultat modifié par " + CurrentUser());
RETURN ok;
```
Source : `rag_knowledge_base/02_functions/misc/misc_functions.md` — AddLogEntry

## Output Format
```
## Contexte GLIMS
[contexte métier 1-2 phrases]

## Code MISPL
```mispl
[code]
```

## Sources documentaires
[chemin rag_knowledge_base/... exact — section]

## Niveau de certitude
[✅ Certain | ⚠️ Probable | 🔬 À vérifier]

## Notes techniques
[optimisations, risques, alternatives]
```

## Domain Focus
- Règles de calcul de résultats (valeurs dérivées)
- Formatage d'identifiants et numérotation automatique
- Validation de saisie et contrôles qualité
- Déclencheurs sur événements GLIMS (à la validation, à l'impression)
- Manipulation de chaînes pour rapports et étiquettes
