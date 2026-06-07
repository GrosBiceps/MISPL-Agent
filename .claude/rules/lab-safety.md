# Règle : Sécurité Laboratoire Clinique

## Règle
Tout code MISPL généré qui touche à des résultats patients, des validations, ou des identifiants doit inclure un avertissement de test obligatoire.

## Pourquoi
GLIMS est un SIL (Système d'Information de Laboratoire) utilisé en production clinique. Un script MISPL défectueux peut :
- Générer des résultats incorrects transmis aux cliniciens
- Modifier des identifiants patients (risque de confusion entre patients)
- Bloquer la validation d'examens urgents
- Créer des boucles infinies bloquant le serveur GLIMS

## Comment appliquer
1. Tout script modifiant `.Result.*` ou `.Sample.*` → ajouter : "⚠️ Tester impérativement en environnement de recette GLIMS avant déploiement en production"
2. Toute écriture via `SetSiteAttribute()` → avertir sur les effets globaux
3. Scripts d'impression haute fréquence (étiquettes) → signaler l'impact performance
4. Toujours recommander l'usage de `AddLogEntry()` pour les modifications de données

## Avertissement standard à inclure
```
⚠️ AVERTISSEMENT CLINIQUE
Ce script modifie des données dans GLIMS.
Tester obligatoirement dans l'environnement de développement/recette GLIMS
avant tout déploiement en production.
Faire valider par un biologiste médical responsable.
```
