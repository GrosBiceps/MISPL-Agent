"""
Linter de sécurité MISPL — analyse le code généré avant affichage.
Détecte patterns dangereux : boucles infinies, division par zéro, assignation
de champs read-only, division entière silencieuse sur résultats biologiques.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class Severity(Enum):
    ERROR = "[ERREUR]"
    WARNING = "[AVERTISSEMENT]"
    INFO = "[CONSEIL]"


@dataclass
class LintIssue:
    severity: Severity
    message: str
    line: int | None = None
    pattern_matched: str = ""

    def __str__(self) -> str:
        loc = f" (ligne {self.line})" if self.line else ""
        return f"{self.severity.value}{loc} : {self.message}"


@dataclass
class LintResult:
    issues: list[LintIssue] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(i.severity == Severity.ERROR for i in self.issues)

    @property
    def has_warnings(self) -> bool:
        return any(i.severity == Severity.WARNING for i in self.issues)

    @property
    def is_clean(self) -> bool:
        return len(self.issues) == 0

    def summary(self) -> str:
        if self.is_clean:
            return "[OK] Code MISPL valide — aucun probleme detecte"
        errors = sum(1 for i in self.issues if i.severity == Severity.ERROR)
        warnings = sum(1 for i in self.issues if i.severity == Severity.WARNING)
        infos = sum(1 for i in self.issues if i.severity == Severity.INFO)
        parts = []
        if errors:
            parts.append(f"{errors} erreur(s)")
        if warnings:
            parts.append(f"{warnings} avertissement(s)")
        if infos:
            parts.append(f"{infos} conseil(s)")
        return "[ATTENTION] " + ", ".join(parts) + " detecte(s) dans le code MISPL"

    def format_report(self, use_emoji: bool = False) -> str:
        if self.is_clean:
            return self.summary()
        lines = [self.summary(), ""]
        for issue in self.issues:
            lines.append(str(issue))
        return "\n".join(lines)

    def format_report_md(self) -> str:
        """Version Markdown avec emojis pour Streamlit (UTF-8 garanti)."""
        emoji_map = {
            Severity.ERROR: "❌ ERREUR",
            Severity.WARNING: "⚠️ AVERTISSEMENT",
            Severity.INFO: "💡 CONSEIL",
        }
        if self.is_clean:
            return "✅ Code MISPL valide — aucun problème détecté"
        errors = sum(1 for i in self.issues if i.severity == Severity.ERROR)
        warnings = sum(1 for i in self.issues if i.severity == Severity.WARNING)
        parts = []
        if errors:
            parts.append(f"{errors} erreur(s)")
        if warnings:
            parts.append(f"{warnings} avertissement(s)")
        header = "⚠️ " + ", ".join(parts) + " détecté(s)"
        lines = [header, ""]
        for issue in self.issues:
            label = emoji_map.get(issue.severity, str(issue.severity.value))
            loc = f" *(ligne {issue.line})*" if issue.line else ""
            lines.append(f"**{label}**{loc} : {issue.message}")
        return "\n".join(lines)


# ── Règles de lint ─────────────────────────────────────────────────────────────

# (pattern_regex, severity, message)
_RULES: list[tuple[str, Severity, str]] = [
    # ── ERREURS BLOQUANTES ─────────────────────────────────────────────────────
    (
        r"\bWHILE\s+(TRUE|YES|1)\s+DO\b",
        Severity.ERROR,
        "Boucle infinie : WHILE TRUE/YES/1 sans condition de sortie -> freeze serveur GLIMS",
    ),
    (
        r"\bWHILE\s+\w+\s+DO\b(?!.*\w+\s*:=)",
        Severity.WARNING,  # avertissement — peut être faux positif
        "Boucle WHILE : vérifier que la variable de condition est modifiée dans le corps",
    ),
    (
        r"\.Id\s*:=\s*",
        Severity.ERROR,
        "Assignation de clé primaire (.Id) — champ READ-ONLY dans GLIMS, risque de corruption",
    ),
    (
        r"\.ValidationStatus\s*:=\s*",
        Severity.ERROR,
        "Assignation directe de .ValidationStatus — utiliser le workflow de validation GLIMS",
    ),
    (
        r"\.OrderStatus\s*:=\s*",
        Severity.ERROR,
        "Assignation directe de .OrderStatus — utiliser les actions GLIMS prévues",
    ),
    (
        r"\bREPEAT\b(?![\s\S]*?\bUNTIL\b)",
        Severity.ERROR,
        "Bloc REPEAT sans UNTIL — boucle infinie potentielle",
    ),
    # ── AVERTISSEMENTS CLINIQUES ───────────────────────────────────────────────
    (
        r"\b\d+\s*/\s*\d+\b",
        Severity.WARNING,
        "Division entière silencieuse : ex. 5/2=2 en MISPL. "
        "Utiliser 5.0/2 si résultat décimal attendu (critique pour calculs biologiques)",
    ),
    (
        r"/\s*0[^.]",
        Severity.ERROR,
        "Division par zéro entier — erreur d'exécution GLIMS garantie",
    ),
    (
        r"/\s*0\.0",
        Severity.ERROR,
        "Division par zéro fractionnaire — erreur d'exécution GLIMS garantie",
    ),
    (
        r"\.Result\.[A-Za-z]+\s*:=",
        Severity.WARNING,
        "Modification directe de résultat patient (.Result.*) — "
        "ajouter AddLogEntry() pour traçabilité obligatoire",
    ),
    (
        r"\.Sample\.(Barcode|Id|ExternalId)\s*:=",
        Severity.WARNING,
        "Modification d'identifiant échantillon — risque de confusion inter-patients",
    ),
    # ── CONSEILS QUALITÉ ───────────────────────────────────────────────────────
    (
        r"\bWHILE\b.*\bNumEntries\b.*\bDO\b",
        Severity.WARNING,
        "NumEntries() appelé dans la condition WHILE — calculer UNE FOIS avant la boucle "
        "(ex: total := NumEntries(...); WHILE i <= total DO ...)",
    ),
    (
        r"SetSiteAttribute\s*\(",
        Severity.INFO,
        "SetSiteAttribute() modifie l'état global GLIMS (partagé entre tous les utilisateurs) — "
        "s'assurer que la valeur est thread-safe",
    ),
    (
        r"\bRETURN\b(?!\s*[A-Za-z0-9_\"'\?\.\(])",
        Severity.WARNING,
        "RETURN sans valeur explicite — vérifier que le type de retour est correct",
    ),
    # Règle ":= ." déplacée dans _LINE_RULES pour avoir le contexte des lignes suivantes

]

# Patterns nécessitant une analyse ligne par ligne
_LINE_RULES: list[tuple[str, Severity, str]] = [
    (
        r"^\s*(INTEGER|STRING|FRACTIONAL|LOGICAL|DATE|DATETIME|TIME)\s+PROGRAM",
        Severity.INFO,
        "Structure de programme détectée — vérifier que RETURN est présent en fin de programme",
    ),
]

# Fonctions inexistantes en MISPL souvent hallucinations de LLM → erreur bloquante
_FAKE_FUNCTIONS = [
    ("StringToReal", "StringToFractional"),
    ("StringToFloat", "StringToFractional"),
    ("StringToDouble", "StringToFractional"),
    ("IntToString", "IntegerToString"),
    ("FloatToString", "FractionalToString"),
    ("DateToInt", "FractionalToInteger(DateDiffInYears(...))"),
    ("GetDate", "Today()"),
    ("GetTime", "Now()"),
    ("GetUser", "CurrentUser()"),
    ("CreateOrder", "Order.AddRequest() ou interface GLIMS"),
    ("NewOrder", "Order.AddRequest() ou interface GLIMS"),
    ("Left",     "Substr(Source, 1, N)"),
    ("Right",    "Substr(Source, Len(Source)-N+1, N)"),
    ("Length",   "Len(String)"),
    ("Mid",      "Substr(Source, Start, Length)"),
    ("InStr",    "Index(Source, Target)"),
    ("UCase",    "ToUpper(String)"),
    ("LCase",    "ToLower(String)"),
    ("Trim",     "Trim(String) — existe en MISPL mais vérifier signature"),
    ("Val",      "StringToFractional ou StringToInteger"),
    ("Str",      "IntegerToString ou FractionalToString"),
    ("CStr",     "IntegerToString ou FractionalToString"),
    ("CInt",     "StringToInteger ou FractionalToInteger"),
    ("CDbl",     "StringToFractional"),
    ("CreatePerson", "impossible via MISPL — configuration admin GLIMS"),
    ("CreatePatient", "impossible via MISPL — configuration admin GLIMS"),
    ("NewPatient", "impossible via MISPL — configuration admin GLIMS"),
    ("NewPerson", "impossible via MISPL — configuration admin GLIMS"),
    ("AddPatient", "impossible via MISPL — configuration admin GLIMS"),
    ("InsertPerson", "impossible via MISPL — configuration admin GLIMS"),
    ("CreateObject", "impossible via MISPL — configuration admin GLIMS"),
    ("CreateCorrespondent", "impossible via MISPL — configuration admin GLIMS"),
    ("SendMailToRole", "GetRole(\"MNEM\").SendMail(Subject, Content, Priority)"),
    ("GetValue", "NumericValue() ou Attribute(\"Value\")"),
    ("SetReferenceRange", "impossible via MISPL — configuration admin GLIMS"),
    ("SetAnalyteUnit", "impossible via MISPL — configuration admin GLIMS"),
]


def lint_mispl_code(code: str) -> LintResult:
    """
    Analyse un bloc de code MISPL et retourne les problèmes détectés.
    """
    result = LintResult()
    if not code or not code.strip():
        return result

    # ── Détection AVANT strip : commentaires // invalides en MISPL ──────────────
    for m in re.finditer(r"//[^\n]*", code):
        line_num = code[: m.start()].count("\n") + 1
        result.issues.append(LintIssue(
            severity=Severity.WARNING,
            message="Commentaire // invalide en MISPL — utiliser /* ... */",
            line=line_num,
            pattern_matched=m.group(0)[:40],
        ))

    # ── CascadeRequest : fonction legacy ancienne version GLIMS ────────────────
    for m in re.finditer(r"\bCascadeRequest\s*\(", code):
        line_num = code[: m.start()].count("\n") + 1
        result.issues.append(LintIssue(
            severity=Severity.WARNING,
            message="CascadeRequest est une fonction d'ancienne version GLIMS — utiliser Action.Order().AddRequest(\"MNEM\", ?, ?)",
            line=line_num,
        ))

    # ── sc_Role.SendMail sans GetRole ──────────────────────────────────────────
    if re.search(r"\bsc_Role\.SendMail\s*\(", code) and "GetRole" not in code:
        result.issues.append(LintIssue(
            severity=Severity.ERROR,
            message="sc_Role.SendMail appelé sur le type — utiliser GetRole(\"MNEM\").SendMail(...)",
        ))

    # ── Navigation ERD invalide pour l'âge ─────────────────────────────────────
    if re.search(r"\.Order\(\)\.Specimen\.Object\.AgeInYears", code):
        result.issues.append(LintIssue(
            severity=Severity.WARNING,
            message="Navigation ERD invalide pour l'âge — utiliser .Action().Object.AgeInYears(Today())",
        ))

    # Normaliser le code (supprimer les commentaires MISPL si présents)
    clean_code = re.sub(r"//[^\n]*", "", code)  # commentaires ligne
    clean_code = re.sub(r"/\*[\s\S]*?\*/", "", clean_code)  # commentaires bloc

    # Détection fonctions inexistantes (hallucinations LLM fréquentes)
    for fake_fn, correct_fn in _FAKE_FUNCTIONS:
        if re.search(r"\b" + re.escape(fake_fn) + r"\s*\(", clean_code):
            result.issues.append(LintIssue(
                severity=Severity.ERROR,
                message=f"Fonction MISPL inexistante : {fake_fn}() — utiliser {correct_fn}",
                line=None,
            ))

    # Règles globales (sur tout le code)
    for pattern, severity, message in _RULES:
        match = re.search(pattern, clean_code, re.IGNORECASE | re.MULTILINE)
        if match:
            # Trouver le numéro de ligne
            line_num = clean_code[: match.start()].count("\n") + 1
            result.issues.append(LintIssue(
                severity=severity,
                message=message,
                line=line_num,
                pattern_matched=match.group(0)[:50],
            ))

    # Vérification RETURN présent dans tout programme
    if re.search(r"\bPROGRAM\b", clean_code, re.IGNORECASE):
        if not re.search(r"\bRETURN\b", clean_code, re.IGNORECASE):
            result.issues.append(LintIssue(
                severity=Severity.ERROR,
                message="Programme MISPL sans instruction RETURN — le programme ne retournera pas de valeur",
            ))

    # Vérification ENDIF pour chaque IF
    if_count = len(re.findall(r"\bIF\b", clean_code, re.IGNORECASE))
    endif_count = len(re.findall(r"\bENDIF\b", clean_code, re.IGNORECASE))
    if if_count != endif_count:
        result.issues.append(LintIssue(
            severity=Severity.ERROR,
            message=f"Déséquilibre IF/ENDIF : {if_count} IF pour {endif_count} ENDIF",
        ))

    # Vérification DONE pour chaque WHILE
    while_count = len(re.findall(r"\bWHILE\b", clean_code, re.IGNORECASE))
    done_count = len(re.findall(r"\bDONE\b", clean_code, re.IGNORECASE))
    if while_count != done_count:
        result.issues.append(LintIssue(
            severity=Severity.ERROR,
            message=f"Déséquilibre WHILE/DONE : {while_count} WHILE pour {done_count} DONE",
        ))

    return result


def extract_mispl_blocks(text: str) -> list[str]:
    """
    Extrait les blocs de code MISPL d'une réponse LLM (entre ```mispl ... ``` ou ``` ... ```).
    """
    blocks = []
    # Blocs marqués ```mispl
    for match in re.finditer(r"```mispl\s*([\s\S]*?)```", text, re.IGNORECASE):
        blocks.append(match.group(1).strip())
    # Blocs génériques ``` contenant PROGRAM
    if not blocks:
        for match in re.finditer(r"```\s*([\s\S]*?)```", text):
            content = match.group(1).strip()
            if re.search(r"\bPROGRAM\b", content, re.IGNORECASE):
                blocks.append(content)
    return blocks


def lint_response(llm_response: str) -> LintResult:
    """
    Lint complet d'une réponse LLM : extrait tous les blocs MISPL et les analyse.
    """
    blocks = extract_mispl_blocks(llm_response)
    if not blocks:
        return LintResult()

    combined = LintResult()
    for block in blocks:
        result = lint_mispl_code(block)
        combined.issues.extend(result.issues)

    return combined


# ── Auto-correction des erreurs réparables ────────────────────────────────────

def _split_top_level_args(s: str) -> list[str]:
    """Découpe les arguments d'appel au niveau supérieur (ignore virgules dans parenthèses/guillemets)."""
    args, depth, in_str, cur = [], 0, False, ""
    for ch in s:
        if ch == '"':
            in_str = not in_str; cur += ch
        elif ch == "(" and not in_str:
            depth += 1; cur += ch
        elif ch == ")" and not in_str:
            depth -= 1; cur += ch
        elif ch == "," and depth == 0 and not in_str:
            args.append(cur); cur = ""
        else:
            cur += ch
    if cur.strip():
        args.append(cur)
    return args


def autofix_mispl(text: str) -> tuple[str, list[str]]:
    """
    Corrige automatiquement les erreurs réparables dans les blocs ```mispl :
      1. // → /* */
      2. CascadeRequest("X") → Action.Order().AddRequest("X", ?, ?) (legacy)
      3. SendMailToRole("R", ...) → GetRole("R").SendMail(...)
    Retourne (texte_corrigé, liste_corrections).
    """
    corrections: list[str] = []

    def fix_block(m):
        code = m.group(1)

        # 1. // → /* */
        before = code
        code = re.sub(r"//\s*([^\n]*)", lambda c: f"/* {c.group(1).strip()} */", code)
        if code != before:
            corrections.append("Commentaires // convertis en /* */")

        # 2. CascadeRequest("X") → Action.Order().AddRequest("X", ?, ?)
        before = code
        code = re.sub(
            r'\.?CascadeRequest\(\s*("(?:[^"]+)")\s*\)',
            r'Action.Order().AddRequest(\1, ?, ?)',
            code,
        )
        if code != before:
            corrections.append("CascadeRequest() (legacy) converti en Action.Order().AddRequest()")

        # 3. SendMailToRole("R", subj, content, prio) → GetRole("R").SendMail(subj, content, prio)
        def repl_sendmail(sm):
            parts = _split_top_level_args(sm.group(1))
            if len(parts) >= 2:
                role = parts[0].strip()
                rest = ", ".join(p.strip() for p in parts[1:])
                return f'GetRole({role}).SendMail({rest})'
            return sm.group(0)
        before = code
        code = re.sub(r"SendMailToRole\s*\(([\s\S]*?)\)\s*;", lambda x: repl_sendmail(x) + ";", code)
        if code != before:
            corrections.append("SendMailToRole() converti en GetRole().SendMail()")

        return "```mispl\n" + code + "```"

    fixed = re.sub(r"```mispl\s*([\s\S]*?)```", fix_block, text, flags=re.IGNORECASE)
    return fixed, corrections
