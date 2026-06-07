"""
Ingestion pipeline — rag_knowledge_base/*.md → ChromaDB + BM25 corpus.

Stratégie :
  - 1 section H2 = 1 chunk atomique (pas de RecursiveCharacterTextSplitter)
  - Frontmatter YAML → métadonnées ChromaDB (domaine, context, priority, tags, anti_hallucination)
  - keywords_fr + tags injectés dans le texte BM25 (boost recall FR)
  - Même collection ChromaDB que build_vectorstore.py (ADDITIVE — ne supprime pas les chunks HTML)
  - Fonction idempotente : si chunk déjà présent (même hash), skip

Usage :
    python src/rag/ingest_knowledge_base.py          # ingestion additive
    python src/rag/ingest_knowledge_base.py --rebuild # reset collection complète
    python src/rag/ingest_knowledge_base.py --dry-run # affiche stats sans ingérer
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import chromadb
from chromadb.utils import embedding_functions

try:
    import yaml
    YAML_OK = True
except ImportError:
    YAML_OK = False

ROOT = Path(__file__).parent.parent.parent
KB_ROOT = ROOT / "rag_knowledge_base"
VECTORSTORE_PATH = ROOT / "docs" / "chunks" / "vectorstore"
BM25_CORPUS_PATH = ROOT / "docs" / "chunks" / "bm25_corpus.json"
COLLECTION_NAME = "glims_mispl_docs"

# Taille cible d'un chunk MD — au-dessus, on sous-découpe par ## (pas par char)
CHUNK_TARGET_CHARS = 1400
# Préfixe d'ID pour distinguer les chunks MD des chunks HTML
MD_ID_PREFIX = "kb_"


# ── YAML frontmatter ──────────────────────────────────────────────────────────

def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """
    Extrait le bloc YAML entre les deux '---' de tête.
    Retourne (metadata_dict, body_sans_frontmatter).
    Fonctionne sans PyYAML (fallback regex) pour ne pas bloquer l'ingestion.
    """
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        return {}, text

    fm_text = m.group(1)
    body = text[m.end():]

    if YAML_OK:
        try:
            fm = yaml.safe_load(fm_text) or {}
            return fm, body
        except Exception:
            pass

    # Fallback regex : extrait les champs scalaires + listes simples
    fm: dict[str, Any] = {}
    for line in fm_text.splitlines():
        kv = re.match(r'^(\w+):\s*"?([^"\n]+)"?', line)
        if kv:
            fm[kv.group(1)] = kv.group(2).strip()
        list_match = re.match(r'^(\w+):\s*\[(.+)\]', line)
        if list_match:
            items = [i.strip().strip('"') for i in list_match.group(2).split(',')]
            fm[list_match.group(1)] = items

    return fm, body


# ── Chunking section H2 + fallback sous-découpe ──────────────────────────────

def _split_oversized_section(
    title: str,
    content: str,
    max_chars: int = CHUNK_TARGET_CHARS,
) -> list[tuple[str, str]]:
    """
    Sous-découpe une section trop longue en sous-chunks.

    Stratégie (ordre de priorité) :
    1. Découpe par blocs séparés par '---' (délimiteur sémantique MD)
    2. Découpe par paragraphe vide (\\n\\n) si les blocs sont encore trop grands
    3. Toujours préserver le header ## pour que chaque sous-chunk soit autonome.

    Chaque sous-chunk hérite du titre de la section parente (suffixé d'un index).
    """
    # Séparer par --- (délimiteur thématique fort dans nos fiches)
    raw_blocks = re.split(r"\n---+\n", content)
    result: list[tuple[str, str]] = []

    for bi, block in enumerate(raw_blocks):
        block = block.strip()
        if not block:
            continue

        # Si le bloc contient déjà le header ## on le garde tel quel
        has_header = block.startswith("## ")
        sub_title = title if bi == 0 else f"{title} [{bi+1}]"

        if len(block) <= max_chars:
            chunk_text = block if has_header else f"## {sub_title}\n\n{block}"
            result.append((sub_title, chunk_text))
            continue

        # Bloc encore trop grand : sous-découpe par paragraphe (\\n\\n)
        paras = re.split(r"\n{2,}", block)
        current_parts: list[str] = []
        current_len = 0
        part_idx = 0

        for para in paras:
            if current_len + len(para) + 2 > max_chars and current_parts:
                chunk_body = "\n\n".join(current_parts)
                sub_sub_title = f"{sub_title} [{part_idx+1}]" if part_idx > 0 else sub_title
                chunk_text = chunk_body if chunk_body.startswith("## ") else f"## {sub_sub_title}\n\n{chunk_body}"
                result.append((sub_sub_title, chunk_text))
                current_parts = []
                current_len = 0
                part_idx += 1
            current_parts.append(para)
            current_len += len(para) + 2

        if current_parts:
            chunk_body = "\n\n".join(current_parts)
            sub_sub_title = f"{sub_title} [{part_idx+1}]" if part_idx > 0 else sub_title
            chunk_text = chunk_body if chunk_body.startswith("## ") else f"## {sub_sub_title}\n\n{chunk_body}"
            result.append((sub_sub_title, chunk_text))

    return result if result else [(title, content)]


def _split_by_h2(body: str) -> list[tuple[str, str]]:
    """
    Découpe le corps MD par sections ## (H2).
    Retourne liste de (section_title, section_content).
    La première section sans ## est titrée 'intro'.

    Fallback : si une section dépasse CHUNK_TARGET_CHARS, elle est
    sous-découpée par _split_oversized_section (blocs --- puis paragraphes).
    """
    parts = re.split(r"\n(?=## )", body)
    sections: list[tuple[str, str]] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        h2 = re.match(r"## (.+)", part)
        title = h2.group(1).strip() if h2 else "intro"
        if len(part) > CHUNK_TARGET_CHARS:
            sections.extend(_split_oversized_section(title, part))
        else:
            sections.append((title, part))
    return sections


# ── Extraction features depuis contenu section ───────────────────────────────

def _extract_section_metadata(title: str, content: str, fm: dict) -> dict:
    """
    Enrichit les métadonnées d'une section avec des features extraites du contenu.
    """
    has_code = "```" in content
    has_signature = "**Signature**" in content or "Signature" in content[:80]

    # Nom de fonction = premier mot du titre (H2) si c'est un identifiant CamelCase/PascalCase
    # EXCLUS : mots génériques (Les, La, Le, Navigation, Concept, Cas, Appendice, etc.)
    fn_name = ""
    _NOT_FN_WORDS = {
        "Les", "La", "Le", "Un", "Une", "Des", "Navigation", "Concept", "Cas",
        "Appendice", "Avertissement", "Complément", "Pattern", "Contexte",
        "Fonctions", "Table", "Section", "Règle", "Analogie", "Structure",
        "Types", "Déclaration", "Instructions", "Opérateurs", "Valeur",
        "Exemple", "Usage", "Notes", "Note", "Attention", "Signature", "Syntaxe",
        "Fonctions", "Anti", "Overview",
    }
    first_word = title.split()[0].rstrip("()") if title else ""
    # Vrai nom de fonction : PascalCase avec au moins une lettre minuscule suivant une majuscule
    # ex: AddRequest ✓, NumericValue ✓, Les ✗, Navigation ✗
    is_pascal = bool(re.search(r"[A-Z][a-z][A-Za-z0-9]+", first_word))
    if first_word and first_word not in _NOT_FN_WORDS and is_pascal and len(first_word) > 3:
        fn_name = first_word

    # Extraire signature depuis le contenu
    sig_match = re.search(r"`([A-Za-z][A-Za-z0-9 |<>().,?_*]+)`\s*\n", content)
    signature = sig_match.group(1).strip() if sig_match else ""

    # Extraire return type depuis la signature
    return_type = ""
    rt_match = re.match(r"(String|Integer|Fractional|Logical|Date|Datetime|Time|Void|PositiveInteger)", signature)
    if rt_match:
        return_type = rt_match.group(1)

    # Tags depuis frontmatter
    tags = fm.get("tags", [])
    if isinstance(tags, list):
        tags_str = " ".join(str(t) for t in tags)
    else:
        tags_str = str(tags)

    # Anti-hallucinations
    anti = fm.get("anti_hallucination", [])
    if isinstance(anti, list):
        anti_str = " | ".join(str(a) for a in anti)
    else:
        anti_str = str(anti)

    # Context d'exécution
    context = fm.get("context", ["all"])
    if isinstance(context, list):
        context_str = ",".join(str(c) for c in context)
    else:
        context_str = str(context)

    # keywords_fr
    kw = fm.get("keywords_fr", [])
    if isinstance(kw, list):
        kw_str = " ".join(str(k) for k in kw)
    else:
        kw_str = str(kw)

    return {
        "source": "rag_knowledge_base",
        "section": title[:80],
        "function_name": fn_name,
        "signature": signature[:200],
        "return_type": return_type,
        "has_examples": has_code,
        "has_signature": has_signature,
        "category": str(fm.get("domaine", "")),
        "table_abbrev": str(fm.get("table_abbrev", "")),
        "priority": fm.get("priority", "medium"),
        "context": context_str,
        "tags": tags_str[:500],
        "anti_hallucination": anti_str[:500],
        "keywords_fr": kw_str[:500],
        "type": str(fm.get("type", "fonction_core")),
        "chunk_type": "md_kb",   # distingue des chunks HTML
    }


# ── Construction texte BM25 enrichi ──────────────────────────────────────────

def _build_bm25_text(chunk_text: str, meta: dict, fm: dict) -> str:
    """
    Texte BM25 enrichi pour le corpus JSON.
    Stratégie identique à build_vectorstore.py :
      texte original + function_name x3 + keywords_fr + tags + anti_hallucination
    """
    parts = [chunk_text]

    fn = meta.get("function_name", "")
    if fn:
        parts.append(f"{fn} {fn} {fn}")  # boost TF
        # Décomposer PascalCase : AddRequest → add request
        sub = re.findall(r"[A-Z][a-z0-9]+", fn)
        if sub:
            parts.append(" ".join(sub) * 2)

    # Mots-clés français → recall queries utilisateur
    kw = fm.get("keywords_fr", [])
    if isinstance(kw, list):
        parts.extend(str(k) for k in kw)

    # Tags techniques
    tags = fm.get("tags", [])
    if isinstance(tags, list):
        parts.append(" ".join(str(t) for t in tags))

    # Anti-hallucinations dans BM25 pour détecter les mauvais noms
    anti = fm.get("anti_hallucination", [])
    if isinstance(anti, list):
        parts.extend(str(a) for a in anti)

    sig = meta.get("signature", "")
    if sig:
        parts.append(sig)

    return " ".join(p for p in parts if p)


# ── Ingestion principale ──────────────────────────────────────────────────────

def ingest_knowledge_base(
    rebuild: bool = False,
    dry_run: bool = False,
    model: str = "paraphrase-multilingual-MiniLM-L12-v2",
    verbose: bool = True,
) -> None:
    """
    Ingère tous les fichiers MD de rag_knowledge_base/ dans ChromaDB + BM25.

    Args:
        rebuild:  Si True, supprime et recrée la collection entière.
                  Si False (défaut), ingestion additive — skip des IDs déjà présents.
        dry_run:  Affiche les stats sans écrire dans la base.
        model:    Modèle SentenceTransformer local.
        verbose:  Affichage détaillé.
    """
    def log(msg: str) -> None:
        if verbose:
            print(msg)

    log(f"\n{'='*60}")
    log("MISPL RAG — Ingestion rag_knowledge_base/")
    log(f"  KB root    : {KB_ROOT}")
    log(f"  Vectorstore: {VECTORSTORE_PATH}")
    log(f"  Modèle     : {model}")
    log(f"  Mode       : {'DRY RUN' if dry_run else ('REBUILD' if rebuild else 'ADDITIVE')}")
    log(f"{'='*60}\n")

    # ── Trouver tous les fichiers MD ──────────────────────────────────────────
    SKIP_FILES = {"README.md", "SOURCES.md"}
    md_files = sorted([
        f for f in KB_ROOT.rglob("*.md")
        if f.name not in SKIP_FILES
    ])
    log(f"Fichiers MD trouvés : {len(md_files)}")

    # ── Parser tous les fichiers → chunks ──────────────────────────────────
    all_chunks: list[dict] = []
    stats = {"files": 0, "sections": 0, "with_code": 0, "with_fn": 0, "skipped_tiny": 0}

    for md_path in md_files:
        text = md_path.read_text(encoding="utf-8", errors="replace")
        fm, body = _parse_frontmatter(text)
        sections = _split_by_h2(body)
        stats["files"] += 1

        for section_title, section_content in sections:
            # Ignorer les micro-sections (< 60 chars après header)
            content_no_header = re.sub(r"^## .+\n", "", section_content).strip()
            if len(content_no_header) < 60:
                stats["skipped_tiny"] += 1
                continue

            meta = _extract_section_metadata(section_title, section_content, fm)
            bm25_text = _build_bm25_text(section_content, meta, fm)

            # ID déterministe : hash (fichier + titre section)
            id_source = f"{md_path.relative_to(ROOT)}::{section_title}"
            chunk_id = MD_ID_PREFIX + hashlib.md5(id_source.encode()).hexdigest()[:16]

            all_chunks.append({
                "id": chunk_id,
                "text": section_content,
                "bm25_text": bm25_text,
                "metadata": meta,
                "file": str(md_path.relative_to(KB_ROOT)),
                "section": section_title,
            })
            stats["sections"] += 1
            if meta["has_examples"]:
                stats["with_code"] += 1
            if meta["function_name"]:
                stats["with_fn"] += 1

    log(f"Chunks générés    : {stats['sections']}")
    log(f"  Avec code MISPL : {stats['with_code']} ({stats['with_code']*100//max(stats['sections'],1)}%)")
    log(f"  Avec fn_name    : {stats['with_fn']}")
    log(f"  Trop petits (skip): {stats['skipped_tiny']}")

    if dry_run:
        log("\n[DRY RUN] Aucune écriture.")
        # Afficher un aperçu des chunks
        for c in all_chunks[:5]:
            log(f"\n  [{c['id']}] {c['file']} :: {c['section']}")
            log(f"    category={c['metadata']['category']} fn={c['metadata']['function_name']}")
            log(f"    tags={c['metadata']['tags'][:80]}")
        return

    # ── ChromaDB ──────────────────────────────────────────────────────────────
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=model
    )
    VECTORSTORE_PATH.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(VECTORSTORE_PATH))

    if rebuild:
        try:
            client.delete_collection(COLLECTION_NAME)
            log(f"Collection '{COLLECTION_NAME}' supprimée (rebuild)")
        except Exception:
            pass
        collection = client.create_collection(
            name=COLLECTION_NAME,
            embedding_function=ef,
            metadata={"hnsw:space": "cosine"},
        )
    else:
        try:
            collection = client.get_collection(name=COLLECTION_NAME, embedding_function=ef)
            log(f"Collection existante chargée ({collection.count()} docs)")
        except Exception:
            collection = client.create_collection(
                name=COLLECTION_NAME,
                embedding_function=ef,
                metadata={"hnsw:space": "cosine"},
            )
            log(f"Nouvelle collection '{COLLECTION_NAME}' créée")

    # ── Filtrage IDs déjà présents (mode additive) ────────────────────────────
    if not rebuild:
        existing_ids = set(collection.get(ids=[c["id"] for c in all_chunks])["ids"])
        chunks_to_add = [c for c in all_chunks if c["id"] not in existing_ids]
        log(f"Chunks déjà présents : {len(existing_ids)}")
        log(f"Nouveaux chunks      : {len(chunks_to_add)}")
    else:
        chunks_to_add = all_chunks

    # ── Ingestion par batch ───────────────────────────────────────────────────
    BATCH = 200
    added = 0
    for i in range(0, len(chunks_to_add), BATCH):
        batch = chunks_to_add[i: i + BATCH]
        collection.add(
            ids=[c["id"] for c in batch],
            documents=[c["text"] for c in batch],
            metadatas=[c["metadata"] for c in batch],
        )
        added += len(batch)
        log(f"  Ingéré {added}/{len(chunks_to_add)} chunks...", )

    log(f"\nChromaDB: {added} chunks ajoutes -> total {collection.count()}")

    # ── Mise à jour BM25 corpus ───────────────────────────────────────────────
    # Charger corpus existant (chunks HTML) et ajouter les chunks MD
    existing_bm25: list[dict] = []
    existing_fn_names: set[str] = set()

    if BM25_CORPUS_PATH.exists() and not rebuild:
        with open(BM25_CORPUS_PATH, encoding="utf-8") as f:
            old_data = json.load(f)
        # Garder uniquement les chunks non-MD (préserver les chunks HTML)
        existing_bm25 = [c for c in old_data.get("chunks", []) if not c.get("id", "").startswith(MD_ID_PREFIX)]
        existing_fn_names = set(old_data.get("known_functions", []))
        log(f"BM25 corpus existant : {len(existing_bm25)} chunks HTML préservés")

    # Nouveaux chunks MD pour BM25
    new_bm25_chunks = [
        {
            "id": c["id"],
            "text": c["bm25_text"],        # texte enrichi pour BM25
            "function_name": c["metadata"]["function_name"],
            "source": c["metadata"]["source"] + "/" + c["file"],
            "section": c["section"],
            "return_type": c["metadata"]["return_type"],
            "signature": c["metadata"]["signature"],
            "category": c["metadata"]["category"],
            "priority": c["metadata"]["priority"] in ("critical", "high"),
            "has_examples": c["metadata"]["has_examples"],
            "chunk_type": "md_kb",
        }
        for c in all_chunks  # TOUS les chunks MD (pas seulement les nouveaux)
    ]

    # Extraire function_names pour exact-match
    md_fn_names = {c["function_name"] for c in new_bm25_chunks if c["function_name"]}
    all_known_fns = existing_fn_names | md_fn_names

    # Corpus final = HTML + MD
    final_bm25 = existing_bm25 + new_bm25_chunks

    BM25_CORPUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(BM25_CORPUS_PATH, "w", encoding="utf-8") as f:
        json.dump(
            {
                "chunks": final_bm25,
                "known_functions": sorted(all_known_fns),
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    log(f"BM25 corpus mis à jour : {len(final_bm25)} chunks total")
    log(f"Fonctions connues     : {len(all_known_fns)}")

    # ── Manifest ─────────────────────────────────────────────────────────────
    manifest_path = VECTORSTORE_PATH.parent / "manifest_kb.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump({
            "total_md_chunks": len(all_chunks),
            "total_md_files": stats["files"],
            "chunks_with_code": stats["with_code"],
            "chunks_with_fn_name": stats["with_fn"],
            "embedding_model": model,
            "collection": COLLECTION_NAME,
            "collection_total": collection.count(),
            "bm25_total": len(final_bm25),
        }, f, indent=2, ensure_ascii=False)

    log(f"\n[OK] Ingestion terminée")
    log(f"   Chunks MD    : {len(all_chunks)}")
    log(f"   Collection   : {collection.count()} docs total")
    log(f"   BM25 corpus  : {len(final_bm25)} entrées")
    log(f"   Manifest     : {manifest_path}")


# ── Test requête ─────────────────────────────────────────────────────────────

def test_query(
    query: str = "ajouter une analyse automatiquement si résultat anormal",
    n_results: int = 5,
    where_filter: dict | None = None,
) -> None:
    """
    Requête de test sur le vectorstore avec filtre optionnel sur métadonnées.

    Exemples de filtres :
        where_filter={"domaine": "table_result"}
        where_filter={"chunk_type": "md_kb"}
        where_filter={"priority": "critical"}
        where_filter={"context": {"$contains": "result"}}
    """
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="paraphrase-multilingual-MiniLM-L12-v2"
    )
    client = chromadb.PersistentClient(path=str(VECTORSTORE_PATH))
    collection = client.get_collection(name=COLLECTION_NAME, embedding_function=ef)

    kwargs: dict = {
        "query_texts": [query],
        "n_results": n_results,
        "include": ["documents", "metadatas", "distances"],
    }
    if where_filter:
        kwargs["where"] = where_filter

    results = collection.query(**kwargs)

    print("\nQuery : '" + query + "'")
    if where_filter:
        print("Filtre : " + str(where_filter))
    print("-" * 60)

    docs = results["documents"][0]
    metas = results["metadatas"][0]
    dists = results["distances"][0]

    for i, (doc, meta, dist) in enumerate(zip(docs, metas, dists)):
        score = round(1 - dist, 3)
        fn = meta.get("function_name", "—")
        cat = meta.get("category", "—")
        src = meta.get("source", "—")
        chunk_t = meta.get("chunk_type", "html")
        print(f"\n#{i+1} [{chunk_t}] fn={fn} cat={cat} score={score}")
        print(f"     src={src} section={meta.get('section','')[:50]}")
        print(f"     {doc[:120].strip()}...")


# ── Entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ingest rag_knowledge_base/ MD → ChromaDB + BM25")
    parser.add_argument("--rebuild", action="store_true",
                        help="Supprimer et recréer la collection complète")
    parser.add_argument("--dry-run", action="store_true",
                        help="Simuler sans écrire")
    parser.add_argument("--model", default="paraphrase-multilingual-MiniLM-L12-v2",
                        help="Modèle SentenceTransformer local")
    parser.add_argument("--test", action="store_true",
                        help="Lancer une requête de test après ingestion")
    parser.add_argument("--query", default="ajouter une analyse automatiquement si résultat anormal",
                        help="Requête de test")
    parser.add_argument("--filter-domain", default=None,
                        help="Filtre ChromaDB sur le domaine (ex: table_result)")
    args = parser.parse_args()

    ingest_knowledge_base(
        rebuild=args.rebuild,
        dry_run=args.dry_run,
        model=args.model,
    )

    if args.test and not args.dry_run:
        where = {"category": args.filter_domain} if args.filter_domain else None
        test_query(query=args.query, where_filter=where)
