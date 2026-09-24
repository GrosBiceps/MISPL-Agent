#!/usr/bin/env python3
"""Contrôle anti-régression « propriété intellectuelle » de la base RAG MISPL.

Ce script compare toute la base `rag_knowledge_base/` au manuel GLIMS (aide HTML/PDF) et, si on les fournit,
aux sources déclarées dans SOURCES.md (pages web enregistrées, fichiers .md/.txt).
Il se termine avec le code 1 si une ligne rédactionnelle dépasse l'un des seuils calibrés lors de l'audit
de septembre 2026 (docs/audit_PI_V2_vs_GLIMS_2026-09-23/) :

  ÉLEVÉ   reprise littérale d'au moins 15 mots consécutifs (après normalisation)
  MOYEN   reprise littérale de 8 à 14 mots ; TF-IDF (mots, uni+bigrammes) ≥ 0,80 sur un segment de 8 mots ou plus ;
          e5 ≥ 0,95 avec TF-IDF < 0,60 (paraphrase ou traduction possible, embeddings en option) ;
          EXEMPLE : appel de fonction à arguments littéraux retrouvé à l'identique dans le manuel
  FAIBLE  seulement signalé, jamais bloquant : TF-IDF entre 0,60 et 0,80, reprise de 5 à 7 mots

Ne sont pas contrôlées les lignes purement factuelles : en-tête YAML, titres, signatures, listes de
paramètres, clés JSON autres que « desc ». Les exceptions justifiées se déclarent dans
tools/ip_allowlist.json (fichier, fragment de la ligne, justification).

USAGE (à lancer avant chaque ajout ou modification de la base) :
    python tools/check_ip_similarity.py --manual "C:/chemin/vers/french"
    python tools/check_ip_similarity.py --manual ... --sources docs/sources_declarees/     # + sources déclarées
    python tools/check_ip_similarity.py --manual ... --gpu-host gpu                          # + embeddings e5 via ssh
    python tools/check_ip_similarity.py --manual ... --report ip_check.json                  # rapport détaillé

Option --gpu-host : le script copie les segments dans un répertoire temporaire du poste distant (Windows,
cmd.exe, Python avec torch CUDA et sentence-transformers), calcule les embeddings
intfloat/multilingual-e5-large (préfixe « query: », fp16), rapatrie les vecteurs, vérifie leurs SHA-256 puis
supprime le répertoire distant. Les vecteurs du manuel sont mis en cache localement (--cache).
Dépendances : numpy, scikit-learn, beautifulsoup4 ; pypdf est optionnel (PDF du manuel).
Ce contrôle réduit le risque de reprise de l'expression du manuel. Il ne constitue pas une garantie juridique.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unicodedata
import uuid
from collections import defaultdict
from pathlib import Path

NGRAM = 8
HIGH_RUN, MID_RUN, LOW_RUN = 15, 8, 5
TFIDF_HIGH, TFIDF_MID = 0.80, 0.60
E5_HIGH = 0.95
E5_MODEL = "intfloat/multilingual-e5-large"
ROOT = Path(__file__).resolve().parent.parent

# ------------------------------------------------------------------ normalisation / extraction


def norm(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


BLOCK = {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "ul", "ol", "dl", "dt", "dd", "table", "tr", "td",
         "th", "caption", "pre", "blockquote", "br", "hr", "title", "section", "article", "header", "footer",
         "nav", "tbody", "thead", "figure", "figcaption"}


def html_lines(data):
    from bs4 import BeautifulSoup, NavigableString, Comment, Tag
    soup = BeautifulSoup(data, "html.parser")
    out, buf = [], []

    def flush():
        t = " ".join("".join(buf).split())
        if t:
            out.append(t)
        buf.clear()

    def walk(node):
        for ch in node.children:
            if isinstance(ch, Comment):
                continue
            if isinstance(ch, NavigableString):
                buf.append(str(ch).replace("\xa0", " "))
            elif isinstance(ch, Tag) and ch.name.lower() not in {"script", "style", "noscript", "head", "svg"}:
                if ch.name.lower() in BLOCK:
                    flush(); walk(ch); flush()
                else:
                    walk(ch)
    walk(soup.body or soup)
    flush()
    return out


def file_lines(p):
    ext = p.suffix.lower()
    try:
        if ext in (".htm", ".html", ".xml"):
            return html_lines(p.read_bytes())
        if ext == ".pdf":
            try:
                from pypdf import PdfReader
            except ImportError:
                return []
            return [" ".join(l.split()) for pg in PdfReader(str(p)).pages for l in (pg.extract_text() or "").splitlines() if l.strip()]
        if ext in (".md", ".txt"):
            return [" ".join(l.split()) for l in p.read_text(encoding="utf-8", errors="replace").splitlines() if l.strip()]
    except Exception as e:  # consigné, jamais bloquant pour un fichier isolé
        print(f"  [avertissement] lecture impossible : {p} ({e})", file=sys.stderr)
    return []


def load_reference(dirs, cache):
    """Texte de référence (manuel + sources déclarées), mis en cache par (chemin, taille, date)."""
    refs = []
    for d in dirs:
        d = Path(d)
        files = sorted(x for x in d.rglob("*") if x.is_file() and x.suffix.lower() in
                       {".htm", ".html", ".xml", ".pdf", ".md", ".txt"})
        key = hashlib.sha256("\n".join(f"{f}|{f.stat().st_size}|{f.stat().st_mtime_ns}" for f in files).encode()).hexdigest()[:16]
        cf = cache / f"ref_{key}.json"
        if cf.exists():
            refs += json.loads(cf.read_text(encoding="utf-8"))
            continue
        print(f"  extraction du texte de référence : {d} ({len(files)} fichiers)…", file=sys.stderr)
        part = []
        for f in files:
            for i, l in enumerate(file_lines(f), 1):
                part.append([str(f.relative_to(d)).replace("\\", "/"), i, l])
        cache.mkdir(parents=True, exist_ok=True)
        cf.write_text(json.dumps(part, ensure_ascii=False), encoding="utf-8")
        refs += part
    return refs


# ------------------------------------------------------------------ base V2 : lignes et contexte
SIGLINE = re.compile(r"^\s*(?:[A-Za-z_|]+\s+){1,3}[A-Z][A-Za-z0-9_]*\s*\([^)]*\)\s*;?\s*$")


def kb_lines(kb):
    out = []
    for p in sorted(kb.rglob("*")):
        if not p.is_file() or p.suffix not in (".md", ".json"):
            continue
        rel = str(p.relative_to(kb)).replace("\\", "/")
        # les URL (citations de sources) ne sont pas du texte rédactionnel : elles sont retirées avant mesure
        lines = [re.sub(r"https?://\S+", " ", x) for x in p.read_text(encoding="utf-8").splitlines()]
        in_fm = in_code = False
        for i, l in enumerate(lines, 1):
            s = l.strip()
            if p.suffix == ".json":
                m = re.match(r'\s*"desc"\s*:\s*"(.*)",?\s*$', l)
                out.append((rel, i, m.group(1) if m else l, "desc" if m else "factuel"))
                continue
            if i == 1 and s == "---":
                in_fm = True; out.append((rel, i, l, "factuel")); continue
            if in_fm:
                in_fm = s != "---"; out.append((rel, i, l, "factuel")); continue
            if s.startswith("```"):
                in_code = not in_code; out.append((rel, i, l, "factuel")); continue
            if in_code:
                ctx = "factuel" if SIGLINE.match(l) and not re.search(r'"|:=|\bIF\b|RETURN', l) else "code"
            elif s.startswith("#") or s.startswith("**Signature") or s.startswith("**Type**") \
                    or s.startswith("- **Paramètres**") or s.startswith("- **Surcharge**"):
                ctx = "factuel"
            else:
                ctx = "prose"
            out.append((rel, i, l, ctx))
    return out


# ------------------------------------------------------------------ mesures
def verbatim_runs(kl, refs):
    """Plus longue suite de mots identiques (n-grammes >= NGRAM fusionnés), par ligne V2."""
    idx = defaultdict(list)
    toks = []
    for k, (f, i, l, ctx) in enumerate(kl):
        if ctx == "factuel":
            continue
        t = norm(l).split()
        toks.append((k, t))
        for j in range(len(t) - NGRAM + 1):
            idx[tuple(t[j:j + NGRAM])].append((k, j))
    hits = defaultdict(set)
    where = {}
    for rf, ri, rl in refs:
        t = norm(rl).split()
        for j in range(len(t) - NGRAM + 1):
            g = tuple(t[j:j + NGRAM])
            if g in idx:
                for (k, pos) in idx[g]:
                    hits[k].add(pos)
                    where.setdefault(k, (rf, ri, rl))
    best = {}
    for k, pos in hits.items():
        pos = sorted(pos)
        run = longest = 1
        for a, b in zip(pos, pos[1:]):
            run = run + 1 if b == a + 1 else 1
            longest = max(longest, run)
        best[k] = (longest + NGRAM - 1, where[k])
    # phrases courtes identiques (5 à 7 mots) : sous-chaîne du texte de référence normalisé
    big = " " + " ".join(norm(r[2]) for r in refs) + " "
    for k, t in toks:
        if k in best:
            continue
        for sent in re.split(r"(?<=[.!?;:])\s+", kl[k][2]):
            n = norm(sent)
            if LOW_RUN <= len(n.split()) < NGRAM and f" {n} " in big:
                best[k] = (len(n.split()), ("(phrase courte)", 0, sent))
                break
    return best


def tfidf_best(kl, refs):
    from sklearn.feature_extraction.text import TfidfVectorizer
    seg = [(k, l) for k, (f, i, l, ctx) in enumerate(kl) if ctx != "factuel" and len(norm(l).split()) >= 6]
    ref_text = list(dict.fromkeys(r[2] for r in refs if len(r[2].split()) >= 5))
    vec = TfidfVectorizer(preprocessor=norm, ngram_range=(1, 2), sublinear_tf=True)
    Xs = vec.fit_transform(ref_text)
    Xv = vec.transform([l for _, l in seg])
    S = (Xv @ Xs.T).tocsr()
    out = {}
    for r, (k, _) in enumerate(seg):
        row = S.getrow(r)
        if row.nnz:
            j = row.indices[row.data.argmax()]
            out[k] = (float(row.data.max()), ref_text[j])
    return out, seg, ref_text


REMOTE = r'''
import json, sys, numpy as np
from sentence_transformers import SentenceTransformer
m = SentenceTransformer("%s", device="cuda").half(); m.max_seq_length = 512
for name in sys.argv[1:]:
    t = [json.loads(l)["t"] for l in open(name + ".jsonl", encoding="utf-8")]
    np.save(name + ".npy", m.encode(["query: " + x for x in t], batch_size=64, normalize_embeddings=True).astype(np.float16))
''' % E5_MODEL


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def e5_best(seg, ref_text, host, cache):
    import numpy as np
    key = hashlib.sha256("\n".join(ref_text).encode()).hexdigest()[:16]
    cref = cache / f"e5_ref_{key}.npy"
    tmp = Path(tempfile.mkdtemp())
    names = ["kb"] + ([] if cref.exists() else ["ref"])
    with open(tmp / "kb.jsonl", "w", encoding="utf-8") as f:
        for _, l in seg:
            f.write(json.dumps({"t": l}, ensure_ascii=False) + "\n")
    if "ref" in names:
        with open(tmp / "ref.jsonl", "w", encoding="utf-8") as f:
            for l in ref_text:
                f.write(json.dumps({"t": l}, ensure_ascii=False) + "\n")
    (tmp / "enc.py").write_text(REMOTE, encoding="utf-8")
    rdir = f"C:/ip_check_{uuid.uuid4().hex[:8]}"
    ssh = ["ssh", "-o", "BatchMode=yes", host]
    try:
        subprocess.run(ssh + [f'mkdir "{rdir}"'], check=True, capture_output=True)
        subprocess.run(["scp", "-o", "BatchMode=yes", *[str(tmp / f"{n}.jsonl") for n in names], str(tmp / "enc.py"),
                        f"{host}:{rdir}/"], check=True, capture_output=True)
        subprocess.run(ssh + [f'cd /d "{rdir}" && python enc.py {" ".join(names)}'], check=True, capture_output=True)
        for n in names:
            subprocess.run(["scp", "-o", "BatchMode=yes", f"{host}:{rdir}/{n}.npy", str(tmp)], check=True, capture_output=True)
            r = subprocess.run(ssh + [f'certutil -hashfile "{rdir}\\{n}.npy" SHA256'], capture_output=True, text=True)
            remote = next((x.strip().replace(" ", "") for x in r.stdout.splitlines() if re.fullmatch(r"[0-9a-fA-F ]{64,}", x.strip())), "")
            if remote.lower() != sha(tmp / f"{n}.npy"):
                raise RuntimeError(f"SHA-256 différent pour {n}.npy (transfert corrompu)")
    finally:
        subprocess.run(ssh + [f'rmdir /s /q "{rdir}"'], capture_output=True)
    if "ref" in names:
        cache.mkdir(parents=True, exist_ok=True)
        (tmp / "ref.npy").replace(cref)
    Er = np.load(cref).astype(np.float32)
    Ek = np.load(tmp / "kb.npy").astype(np.float32)
    out = {}
    for a in range(0, len(seg), 256):
        B = Ek[a:a + 256] @ Er.T
        for r in range(B.shape[0]):
            j = int(B[r].argmax())
            out[seg[a + r][0]] = (float(B[r, j]), ref_text[j])
    return out


CALL = re.compile(r"\b([A-Z][A-Za-z0-9_]*)\s*\(([^()\n]*(?:\([^()\n]*\)[^()\n]*)*)\)")


def example_hits(kl, refs):
    raw = "\x00".join(re.sub(r"\s+", "", r[2]).lower().replace("\u201c", '"').replace("\u201d", '"') for r in refs)
    out = {}
    for k, (f, i, l, ctx) in enumerate(kl):
        if ctx not in ("code", "prose"):
            continue
        code = l.split("/*")[0]
        for m in CALL.finditer(code):
            if not re.search(r'"[^"]*"|\b\d', m.group(2)):
                continue
            key = re.sub(r"\s+", "", m.group(0)).lower()
            lits = re.findall(r'"([^"]*)"', m.group(2))
            banal = key in ('attribute("value")',) or (lits and all(re.fullmatch(r"[A-Za-z_]+", x) for x in lits)
                                                        and not re.search(r"\d", m.group(2)))
            if len(key) >= 6 and not banal and key in raw:
                out[k] = m.group(0)
    return out


# ------------------------------------------------------------------ programme principal
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kb", default=str(ROOT / "rag_knowledge_base"))
    ap.add_argument("--manual", required=True, help="racine de l'aide GLIMS (dossier « french »)")
    ap.add_argument("--sources", nargs="*", default=[], help="dossiers de sources déclarées (html/md/txt)")
    ap.add_argument("--allowlist", default=str(Path(__file__).with_name("ip_allowlist.json")))
    ap.add_argument("--gpu-host", default=None, help="alias ssh d'un poste GPU pour le contrôle e5 (optionnel)")
    ap.add_argument("--cache", default=str(Path.home() / ".cache" / "mispl_ip_check"))
    ap.add_argument("--report", default=None)
    a = ap.parse_args()
    cache = Path(a.cache)
    refs = load_reference([a.manual] + a.sources, cache)
    kl = kb_lines(Path(a.kb))
    allow = json.loads(Path(a.allowlist).read_text(encoding="utf-8")) if Path(a.allowlist).exists() else []

    vr = verbatim_runs(kl, refs)
    tf, seg, ref_text = tfidf_best(kl, refs)
    e5 = e5_best(seg, ref_text, a.gpu_host, cache) if a.gpu_host else {}
    ex = example_hits(kl, refs)

    findings = []
    for k, (f, i, l, ctx) in enumerate(kl):
        if ctx == "factuel":
            continue
        run = vr.get(k, (0, None))[0]
        t = tf.get(k, (0.0, ""))[0]
        e = e5.get(k, (0.0, ""))[0]
        n = len(norm(l).split())
        lvl, why = None, []
        if run >= HIGH_RUN:
            lvl = "ÉLEVÉ"; why.append(f"reprise littérale {run} mots")
        elif run >= MID_RUN:
            lvl = "MOYEN"; why.append(f"reprise littérale {run} mots")
        # garde-fou : un score TF-IDF élevé n'est retenu que si la ligne et son voisin partagent au moins
        # 4 mots de 3 lettres ou plus (évite les artefacts de voisins très courts, p. ex. « INTEGER | i »)
        shared = len({w for w in norm(l).split() if len(w) >= 3} & {w for w in norm(tf.get(k, (0, ""))[1]).split() if len(w) >= 3})
        if t >= TFIDF_HIGH and n >= 8 and shared >= 4:
            lvl = lvl or "MOYEN"; why.append(f"TF-IDF {t:.2f} ({shared} mots communs)")
        if e >= E5_HIGH and t < TFIDF_MID and run < LOW_RUN and n >= 8:
            lvl = lvl or "MOYEN"; why.append(f"e5 {e:.3f} (paraphrase ou traduction possible)")
        if k in ex:
            lvl = lvl or "MOYEN"; why.append(f"exemple identique au manuel : {ex[k]}")
        if lvl is None and (run >= LOW_RUN or (t >= TFIDF_MID and shared >= 2)):
            lvl = "FAIBLE"; why.append(f"reprise {run} mots / TF-IDF {t:.2f}")
        if lvl is None:
            continue
        ok = next((x for x in allow if x["fichier"] == f and x["fragment"] in l), None)
        findings.append({"niveau": lvl, "fichier": f, "ligne": i, "texte": l.strip()[:200], "mesures": ", ".join(why),
                         "tfidf": round(t, 3), "e5": round(e, 3) if e else None, "reprise_mots": run,
                         "voisin_tfidf": (tf.get(k, (0, ""))[1] or "")[:200],
                         "voisin_e5": (e5.get(k, (0, ""))[1] or "")[:200],
                         "autorise": bool(ok), "justification": ok["justification"] if ok else None})
    blocking = [x for x in findings if x["niveau"] in ("ÉLEVÉ", "MOYEN") and not x["autorise"]]
    print(f"Base : {a.kb} | lignes contrôlées : {sum(1 for x in kl if x[3] != 'factuel')} | "
          f"référence : {len(refs)} lignes | e5 : {'oui' if e5 else 'non'}")
    for lv in ("ÉLEVÉ", "MOYEN", "FAIBLE"):
        xs = [x for x in findings if x["niveau"] == lv]
        print(f"  {lv:6s} : {len(xs)} (dont autorisés : {sum(x['autorise'] for x in xs)})")
    for x in blocking:
        voisin = x["voisin_e5"] if "e5" in x["mesures"] else x["voisin_tfidf"]
        print(f"  [BLOQUANT] {x['fichier']}:{x['ligne']} — {x['mesures']}\n      V2     : {x['texte'][:140]}\n"
              f"      voisin : {voisin[:140]}")
    if a.report:
        Path(a.report).write_text(json.dumps({"findings": findings, "bloquants": len(blocking)}, ensure_ascii=False, indent=1),
                                  encoding="utf-8")
    print("RÉSULTAT :", "ÉCHEC" if blocking else "OK")
    sys.exit(1 if blocking else 0)


if __name__ == "__main__":
    main()
