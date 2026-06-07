---
id: "functions_datetime"
type: "fonction_core"
domaine: "date_heure"
langage_proxy: "Progress ABL / OpenEdge"
context: ["all"]
table_abbrev: null
return_type: "Date | DateTime | Time | String | Fractional"
priority: "high"
keywords_fr: ["date", "heure", "aujourd'hui", "maintenant", "âge", "jour de la semaine", "formater date", "convertir date", "différence en années", "horodatage", "garde", "week-end"]
anti_hallucination: []
tags: [date, datetime, Today, Now, DateDiffInYears, DateTimeToString, DateTimeToDate, DateTimeToTime, StringToDate, DateToString, TimeToString, AgeInYears, DateAndTimeToDateTime]
---

# Fonctions Date et Heure

Équivalent ABL : `TODAY`, `NOW`, `DATE()`, `DATETIME()` et fonctions de manipulation temporelle.

---

## Today
**Signature** : `Date Today()`  
Retourne la date système courante (sans composante heure).  
**Équivalent ABL** : `TODAY`

```mispl
IF Action.Object.AgeInYears(Today()) <= 19 THEN ...
```

---

## Now
**Signature** : `Time Now()`  
Retourne l'heure système courante.  
**Équivalent ABL** : `TIME`

---

## DateAndTimeToDateTime
**Signature** :
```
Datetime DateAndTimeToDateTime(Date Date, Time Time)
Fractional DateAndTimeToDateTime(Date Date, Integer Time)
```
Combine une date et une heure en un DateTime.

```mispl
DateAndTimeToDateTime(Today(), Now())   /* datetime courant */
```

---

## DateDiffInYears
**Signature** : `Fractional DateDiffInYears(Date Date1, Date Date2)`  
Retourne `Date1 - Date2` exprimé en années (tient compte des années bissextiles).  
Résultat décimal — utiliser `FractionalToInteger()` pour obtenir un entier.

---

## DateTimeToDate
**Signature** : `Date DateTimeToDate(DateTime dt)`  
Extrait la composante date d'un DateTime.

```mispl
DATE Jour;
Jour := DateTimeToDate(Action.Order().ReceiptTime);
```

---

## DateTimeToTime
**Signature** : `Time DateTimeToTime(DateTime dt)`  
Extrait la composante heure d'un DateTime.

---

## DateTimeToString
**Signature** : `String DateTimeToString(DateTime dt, String Format)`  
Formate un DateTime en chaîne. Format style `strftime` :

| Code | Valeur |
|------|--------|
| `%Y` | Année 4 chiffres |
| `%m` | Mois 01–12 |
| `%d` | Jour 01–31 |
| `%H` | Heure 00–23 |
| `%M` | Minutes 00–59 |
| `%a` | Jour semaine abrégé (lun, mar…) |

```mispl
/* Obtenir le jour de la semaine */
STRING jourSemaine;
jourSemaine := DateTimeToString(Action.Order().ReceiptTime, "%a");
/* retourne "lun", "mar", "mer", "jeu", "ven", "sam", "dim" */
```

---

## DateToString
**Signature** : `String DateToString(Date Date, String Format)`  
Formate une Date en chaîne.

---

## StringToDate
**Signature** : `Date StringToDate(String DateString)`  
Convertit une chaîne au format `DD/MM/YYYY` en Date.

```mispl
IF DateTimeToDate(Action.Order().CreationTime) >= StringToDate("13/02/2017") THEN ...
```

---

## StringToTime
**Signature** : `Time StringToTime(String TimeString)`  
Convertit une chaîne heure en Time.

---

## TimeToString
**Signature** : `String TimeToString(Time Time, String Format)`  
Formate un Time en chaîne.

---

## Cas d'usage CHU — Calcul délai et test jour de semaine

```mispl
/* B_non_conf_en_garde : tester si réception hors heures ouvrées */
LOGICAL PROGRAM
  DATE Jour;
  INTEGER WeekDay;
  STRING Reception;

  Jour := DateTimeToDate(Action.Order().ReceiptTime);
  WeekDay := LookUp(DateTimeToString(Action.Order().ReceiptTime, "%a"),
                    "lun,mar,mer,jeu,ven,sam,dim", ",");
  Reception := DateTimeToString(Action.Order().ReceiptTime, "%H:%M");

  /* WeekDay 1-5 = lun-ven, 6-7 = week-end */
  IF WeekDay >= 6 THEN
    /* traitement garde week-end */
  ENDIF;
RETURN YES;
```
