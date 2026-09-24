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
    ("CreateOrder", "Order.AddRequest() ou interface GLIMS"),
    ("NewOrder", "Order.AddRequest() ou interface GLIMS"),
    ("Left",     "Substr(Source, 1, N)"),
    ("Right",    "Substr(Source, Len(Source)-N+1, N)"),
    ("Length",   "Len(String)"),
    ("Mid",      "Substr(Source, Start, Length)"),
    ("InStr",    "Index(Source, Target)"),
    ("UCase",    "ToUpper(String)"),
    ("LCase",    "ToLower(String)"),
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


# ── Lexique minimal : chaînes littérales et commentaires ─────────────────────
#
# Un seul balayage gauche → droite, pour que chaque construction masque les
# autres comme le ferait l'analyseur MISPL : un `//` ou un `/*` à l'intérieur
# d'une chaîne n'ouvre pas de commentaire, un `//` à l'intérieur d'un
# commentaire /* ... */ n'en est pas un, et un appel `Nom(` écrit dans une
# chaîne ("... utilise CreatePatient() ...") n'est pas un appel.
# Banc temps réel 2026-09-24 : les anciennes suppressions séquentielles
# (d'abord `//`, puis `/* */`) mangeaient le `*/` d'un commentaire bloc
# contenant `//`, et le commentaire non gourmand avalait ensuite le RETURN
# du programme (faux « Programme sans RETURN », PFI-002) ; les appels dans
# une chaîne étaient signalés comme fonctions inexistantes (PIJ-005).
_LEXEME_RE = re.compile(
    r'(?P<string>"[^"\n]*")'
    r"|(?P<block>/\*[\s\S]*?\*/)"
    r"|(?P<line>//[^\n]*)"
)


def _mask_code(code: str) -> str:
    """Retourne `code` sans commentaires et avec des chaînes vidées (`""`).

    Les commentaires bloc sont remplacés par autant de sauts de ligne qu'ils
    en contenaient : les numéros de ligne des diagnostics restent exacts."""

    def repl(m: re.Match) -> str:
        if m.group("string") is not None:
            return '""'
        return "\n" * m.group(0).count("\n") + " "

    return _LEXEME_RE.sub(repl, code)


def _line_comments(code: str) -> list[re.Match]:
    """Commentaires `//` réels : hors chaînes et hors commentaires bloc."""
    return [m for m in _LEXEME_RE.finditer(code) if m.group("line") is not None]


def lint_mispl_code(code: str) -> LintResult:
    """
    Analyse un bloc de code MISPL et retourne les problèmes détectés.
    """
    result = LintResult()
    if not code or not code.strip():
        return result

    # ── Commentaires // invalides en MISPL (hors chaînes et commentaires bloc)
    for m in _line_comments(code):
        line_num = code[: m.start()].count("\n") + 1
        result.issues.append(LintIssue(
            severity=Severity.WARNING,
            message="Commentaire // invalide en MISPL — utiliser /* ... */",
            line=line_num,
            pattern_matched=m.group(0)[:40],
        ))

    # Code sans commentaires, chaînes vidées : toutes les règles suivantes
    # portent sur le code exécutable uniquement.
    clean_code = _mask_code(code)

    # ── CascadeRequest : fonction legacy ancienne version GLIMS ────────────────
    for m in re.finditer(r"\bCascadeRequest\s*\(", clean_code):
        line_num = clean_code[: m.start()].count("\n") + 1
        result.issues.append(LintIssue(
            severity=Severity.WARNING,
            message="CascadeRequest est une fonction d'ancienne version GLIMS — utiliser Action.Order().AddRequest(\"MNEM\", ?, ?)",
            line=line_num,
        ))

    # ── sc_Role.SendMail sans GetRole ──────────────────────────────────────────
    if re.search(r"\bsc_Role\.SendMail\s*\(", clean_code) and "GetRole" not in clean_code:
        result.issues.append(LintIssue(
            severity=Severity.ERROR,
            message="sc_Role.SendMail appelé sur le type — utiliser GetRole(\"MNEM\").SendMail(...)",
        ))

    # ── Navigation ERD invalide pour l'âge ─────────────────────────────────────
    if re.search(r"\.Order\(\)\.Specimen\.Object\.AgeInYears", clean_code):
        result.issues.append(LintIssue(
            severity=Severity.WARNING,
            message="Navigation ERD invalide pour l'âge — utiliser .Action().Object.AgeInYears(Today())",
        ))

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

    def fix_line_comment(c: re.Match) -> str:
        # Le texte du commentaire ne doit ni fermer le commentaire bloc créé
        # (`*/`), ni en ouvrir un imbriqué (`/*`) ; les `//` internes sont
        # neutralisés pour ne pas être relus comme commentaires.
        text = c.group(0)[2:].strip()
        text = text.replace("*/", "* /").replace("/*", "/ *").replace("//", "/ /")
        return f"/* {text} */"

    def fix_code(code: str) -> str:
        """Réécritures d'appels : uniquement sur du code exécutable, jamais
        dans un commentaire (où « ANCIEN : CascadeRequest(...) » doit rester
        tel quel) ni dans une chaîne."""
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
        return code

    def fix_block(m):
        code = m.group(1)
        # Découpage en segments « code (chaînes comprises) » / « commentaire » :
        # les chaînes restent dans les segments de code pour que les motifs
        # d'appel (dont les arguments sont des chaînes) les voient.
        out: list[str] = []
        converted = False
        pos = 0
        for lx in _LEXEME_RE.finditer(code):
            if lx.group("string") is not None:
                continue
            out.append(fix_code(code[pos:lx.start()]))
            if lx.group("line") is not None:
                out.append(fix_line_comment(lx))
                converted = True
            else:
                out.append(lx.group(0))
            pos = lx.end()
        out.append(fix_code(code[pos:]))
        if converted:
            corrections.append("Commentaires // convertis en /* */")
        return "```mispl\n" + "".join(out) + "```"

    fixed = re.sub(r"```mispl\s*([\s\S]*?)```", fix_block, text, flags=re.IGNORECASE)
    return fixed, list(dict.fromkeys(corrections))
