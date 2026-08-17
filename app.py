"""MISPL Agent — Interface finale · thème natif dark + CSS minimal"""
from __future__ import annotations
import html, json, logging, os, sys, traceback, uuid
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from src.security.dlp import dlp_check
from src.security.access_mode import (
    MODE_DSI, MODE_TECHNICIEN, DEFAULT_MODE, verify_dsi_password,
)

# ── Avatars — SVG inline (data URI), aucun appel réseau tiers (ex-DiceBear) ───
from urllib.parse import quote as _urlquote

def _svg_avatar(bg: str, fg: str, label: str) -> str:
    svg = (
        f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40'>"
        f"<circle cx='20' cy='20' r='20' fill='{bg}'/>"
        f"<text x='50%' y='53%' font-family='sans-serif' font-size='15' font-weight='600' "
        f"fill='{fg}' text-anchor='middle' dominant-baseline='middle'>{label}</text></svg>"
    )
    return "data:image/svg+xml," + _urlquote(svg)

USER_AVATAR = _svg_avatar("#1e3a5f", "#60a5fa", "MF")
ASSISTANT_AVATAR = _svg_avatar("#0f172a", "#6ee7b7", "AI")

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

# ── Monitoring ressources — démarre le relevé CPU/RAM/disque/réseau/GPU en
# tâche de fond dès le lancement. Le rapport Plotly HTML est écrit à l'arrêt
# (atexit) dans outputs/monitoring/. Désactivable via MISPL_MONITOR=0.
# NB : PAS de @st.cache_resource ici — start_monitoring() est déjà idempotent
# (singleton _MONITOR), et le décorateur placé avant le bloc _CSS plus bas
# fait planter inspect.getsource (Streamlit lit le code source en avant et
# tombe dans le triple-quote CSS).
def _start_resource_monitor():
    if os.environ.get("MISPL_MONITOR", "1") == "0":
        return None
    try:
        from src.utils.resource_monitor import start_monitoring
        return start_monitoring()
    except Exception as e:  # jamais bloquer l'appli pour du monitoring
        logging.getLogger(__name__).warning(f"Monitoring ressources indisponible : {e}")
        return None

_mon = _start_resource_monitor()


@st.cache_resource(show_spinner=False)
def _purge_sessions_once():
    # cache_resource garantit un seul passage par process, pas à chaque rerun
    from src.agent.mispl_agent import purge_old_cache, purge_old_sessions
    return purge_old_sessions(), purge_old_cache()

_purge_sessions_once()

st.set_page_config(
    page_title="MISPL Agent",
    page_icon=None,
    layout="centered",
    initial_sidebar_state="collapsed",
)

# CSS custom minimal — seulement ce que le thème natif ne couvre pas
_CSS = """
<script>
(function(){
  var existing = window.parent.document.getElementById('mispl-css');
  if(existing) existing.remove();
  // Polices système uniquement — aucun appel réseau tiers (RGPD/SSI : évite
  // de divulguer l'IP de l'utilisateur à Google Fonts à chaque visite).

  var css = `
    /* ── Layout ── */
    #MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"],
    [data-testid="stHeader"], header, [data-testid="collapsedControl"] { display:none!important }
    * { font-family:-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif!important }
    .block-container { padding:2rem 1.5rem 6rem!important; max-width:780px!important }

    /* ── Chat messages ── */
    [data-testid="stChatMessage"] { background:transparent!important; border:none!important; padding:.3rem 0!important }

    /* ── User bubble ── */
    .user-msg {
      background:#1e3a5f; border:1px solid rgba(59,130,246,.35);
      border-radius:12px 12px 3px 12px; padding:.75rem 1rem;
      color:#f1f5f9!important; font-size:.875rem; line-height:1.65;
      display:inline-block; max-width:100%;
    }

    /* ── Assistant markdown ── */
    [data-testid="stMarkdown"] { color:#f1f5f9!important }
    [data-testid="stMarkdown"] h2 {
      font-size:.93rem!important; font-weight:700!important; color:#60a5fa!important;
      margin:1.2rem 0 .45rem!important; padding-bottom:.35rem;
      border-bottom:1px solid #2d2d44;
    }
    [data-testid="stMarkdown"] h3 { font-size:.87rem!important; color:#94a3b8!important; margin:.8rem 0 .3rem!important }
    [data-testid="stMarkdown"] p  { font-size:.875rem!important; color:#f1f5f9!important; line-height:1.7!important }
    [data-testid="stMarkdown"] li { font-size:.87rem!important; color:#a8b3c7!important; line-height:1.6!important; margin-bottom:.2rem!important }
    [data-testid="stMarkdown"] strong { color:#f1f5f9!important; font-weight:600!important }

    /* ── Inline code ── */
    code {
      font-family:'Cascadia Code','Consolas','SFMono-Regular',monospace!important;
      background:rgba(59,130,246,.13)!important; color:#93c5fd!important;
      padding:2px 6px!important; border-radius:5px!important;
      font-size:.82em!important; border:1px solid rgba(59,130,246,.22)
    }

    /* ── Code blocks (MISPL — vert émeraude) ── */
    pre {
      background:#0a0e14!important; border:1px solid #2d3748!important;
      border-radius:10px!important; padding:1.1rem 1.2rem!important;
      box-shadow:inset 0 1px 4px rgba(0,0,0,.5)
    }
    pre code {
      background:transparent!important; color:#6ee7b7!important;
      font-size:.82rem!important; padding:0!important;
      border:none!important; line-height:1.65!important;
    }

    /* ── Expander ── */
    [data-testid="stExpander"] {
      background:#1a1a2e!important; border:1px solid #2d2d44!important;
      border-radius:10px!important; margin-top:.65rem!important
    }
    /* Cacher TOUT ce que Streamlit met dans le summary (icône texte + svg) */
    [data-testid="stExpander"] summary svg,
    [data-testid="stExpander"] summary [data-testid="stExpanderToggleIcon"],
    [data-testid="stExpander"] summary span.material-icons,
    [data-testid="stExpander"] summary i { display:none!important; font-size:0!important }
    /* Flèche CSS custom */
    [data-testid="stExpander"] summary {
      position:relative!important; padding-left:1.2rem!important; cursor:pointer!important; list-style:none!important
    }
    [data-testid="stExpander"] summary::-webkit-details-marker { display:none!important }
    [data-testid="stExpander"] summary::before {
      content:'▶'; position:absolute; left:0; top:50%; transform:translateY(-50%);
      font-size:.6rem; color:#6b7591; transition:transform 150ms ease;
    }
    [data-testid="stExpander"] details[open] > summary::before { transform:translateY(-50%) rotate(90deg) }
    /* Texte label — cibler tous les éléments texte du summary */
    [data-testid="stExpander"] summary p,
    [data-testid="stExpander"] summary span:not([class*="icon"]):not([data-testid]),
    [data-testid="stExpander"] summary div:not([data-testid]) {
      color:#94a3b8!important; font-size:.875rem!important; font-weight:600!important; margin:0!important; display:inline!important
    }

    /* ── Citation RAG ── */
    .cite {
      display:flex; align-items:flex-start; gap:8px;
      padding:.45rem .6rem; background:#1e1e32; border:1px solid #2d2d44;
      border-radius:8px; margin-bottom:5px; border-left:3px solid #3b82f6
    }
    .cite-exact { border-left-color:#10b981 }
    .cite-fn { font-family:'Cascadia Code','Consolas','SFMono-Regular',monospace; font-size:.77rem; color:#f1f5f9; font-weight:600 }
    .cite-src { font-family:'Cascadia Code','Consolas','SFMono-Regular',monospace; font-size:.69rem; color:#6b7591; margin-top:1px; word-break:break-all }
    .cite-score { font-size:.68rem; color:#6b7591; white-space:nowrap; font-family:'Cascadia Code','Consolas','SFMono-Regular',monospace; margin-left:auto; padding-left:6px }

    /* ── Thinking animation ── */
    .thinking { display:flex; align-items:center; gap:8px; color:#6b7591; font-size:.83rem; padding:.4rem 0 }
    .thinking .d { width:6px; height:6px; border-radius:50%; background:#3b82f6; animation:pl 1.2s ease-in-out infinite }
    .thinking .d:nth-child(2){ animation-delay:.2s }
    .thinking .d:nth-child(3){ animation-delay:.4s }
    @keyframes pl { 0%,80%,100%{opacity:.2;transform:scale(.7)} 40%{opacity:1;transform:scale(1)} }

    /* ── Empty state ── */
    .empty { text-align:center; padding:3rem 1rem; color:#6b7591 }
    .empty-t { font-size:1rem; font-weight:600; color:#94a3b8; margin-bottom:.4rem }
    .empty-d { font-size:.83rem; color:#6b7591; line-height:1.65; max-width:360px; margin:0 auto }

    /* ── Buttons (exemples) ── */
    div[data-testid="column"] button {
      background:#1e1e32!important; border:1px solid #2d2d44!important;
      border-radius:9px!important; color:#94a3b8!important;
      font-size:.81rem!important; font-weight:500!important;
      padding:.55rem .8rem!important; text-align:left!important;
      height:auto!important; min-height:0!important;
      white-space:normal!important; line-height:1.35!important;
      transition:border-color 130ms,color 130ms!important
    }
    div[data-testid="column"] button:hover {
      border-color:#3b82f6!important; color:#f1f5f9!important; background:#1e1e32!important
    }
    div[data-testid="column"] button p { color:inherit!important; font-size:inherit!important }

    /* ── Status pills ── */
    .pill { display:inline-flex; align-items:center; gap:5px; padding:3px 10px; border-radius:99px; font-size:.71rem; font-weight:600; margin:2px 3px 2px 0 }
    .pill-ok   { background:rgba(16,185,129,.1); color:#34d399; border:1px solid rgba(16,185,129,.3) }
    .pill-warn { background:rgba(245,158,11,.1);  color:#fbbf24; border:1px solid rgba(245,158,11,.3) }
    .pill-err  { background:rgba(239,68,68,.1);   color:#f87171; border:1px solid rgba(239,68,68,.3) }

    /* ── Alert ── */
    [data-testid="stAlert"] { border-radius:10px!important }

    /* ── Signature ── */
    .signature {
      position:fixed; bottom:10px; right:14px;
      font-size:.68rem; color:#475569; pointer-events:none; user-select:none;
    }

    /* ── Reset button ── */
    .reset-row button {
      background:transparent!important; border:1px solid #2d2d44!important;
      color:#6b7591!important; font-size:.77rem!important; padding:.35rem .8rem!important; border-radius:7px!important
    }
    .reset-row button:hover { border-color:#ef4444!important; color:#ef4444!important }
  `;
  var s = window.parent.document.createElement('style');
  s.id = 'mispl-css'; s.textContent = css;
  window.parent.document.head.appendChild(s);

  // Patch DOM direct : remplace le texte "keyboard_arrow_right" dans les summary
  function patchExpanders() {
    window.parent.document.querySelectorAll('[data-testid="stExpander"] summary').forEach(function(sum) {
      sum.childNodes.forEach(function(node) {
        if (node.nodeType === 3 && node.textContent.trim().match(/^keyboard_arrow/)) {
          node.textContent = '';
        }
      });
      // Cacher spans avec texte icône
      sum.querySelectorAll('span, i').forEach(function(el) {
        if (el.textContent.trim().match(/^keyboard_arrow/)) {
          el.style.display = 'none';
          el.style.fontSize = '0';
        }
      });
    });
  }
  // Observer les mutations pour catcher les expanders ajoutés dynamiquement
  var obs = new MutationObserver(patchExpanders);
  obs.observe(window.parent.document.body, { childList:true, subtree:true });
  patchExpanders();

  // Signature fixe bas droite
  if (!window.parent.document.getElementById('mispl-sig')) {
    var sig = window.parent.document.createElement('div');
    sig.id = 'mispl-sig';
    sig.textContent = 'Magne Florian';
    sig.style.cssText = 'position:fixed;bottom:10px;right:14px;font-size:.68rem;color:#475569;pointer-events:none;user-select:none;z-index:99999;font-family:Inter,sans-serif';
    window.parent.document.body.appendChild(sig);
  }
})();
</script>
"""
components.html(_CSS, height=0, scrolling=False)


# ── Agent ─────────────────────────────────────────────────────────────────────
# cache_resource (PAS cache_data) : _load_agent retourne des fonctions non-sérialisables
@st.cache_resource(show_spinner=False)
def _load_agent():
    try:
        from src.agent.mispl_agent import ask_mispl, FREE_MODELS, DEFAULT_MODEL
        from src.agent.prompt_builder import SKILL_PROFILES
        return True, "", ask_mispl, FREE_MODELS, DEFAULT_MODEL, SKILL_PROFILES
    except Exception:
        return False, traceback.format_exc(), None, {}, "", {}

# Chargement différé via cache_resource : l'appel est dans le corps Streamlit
# → Streamlit répond au health check HF avant de charger ChromaDB/BM25
# cache_resource garantit que le chargement n'a lieu qu'une seule fois (singleton)
_ok, _err, _ask_mispl, FREE_MODELS, DEFAULT_MODEL, SKILL_PROFILES = _load_agent()

def _is_vs_ready():
    return (ROOT/"docs"/"chunks"/"vectorstore").exists() and \
           (ROOT/"docs"/"chunks"/"bm25_corpus.json").exists()

def _manifest():
    p = ROOT/"docs"/"chunks"/"manifest.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}

EXAMPLES = [
    ("Substr — extraire une sous-chaine",           "Comment utiliser Substr pour extraire une sous-chaine en MISPL ?"),
    ("Today / DateToString — formater la date",     "Comment formater la date du jour en MISPL ?"),
    ("IntegerToString — convertir entier en texte", "Comment convertir un entier en chaine de caracteres ?"),
    ("AddLogEntry — log d'audit",                   "Comment ecrire un log d'audit lors d'un changement de resultat ?"),
    ("CurrentUser — utilisateur connecte",          "Comment recuperer le nom de l'utilisateur connecte ?"),
    ("Round — arrondir un decimal",                 "Comment arrondir un nombre decimal avec Round ?"),
]

ICON_BOOK = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>'


# ── Mode d'accès (DSI / Technicien) ─────────────────────────────────────────
if "access_mode" not in st.session_state:
    st.session_state.access_mode = DEFAULT_MODE

# ── Settings expander (clé API, modèle, RAG) ──────────────────────────────────
with st.expander("Parametres", expanded=False):
    st.markdown("**Mode d'accès**")
    mode_pill = (
        '<span class="pill pill-ok">Mode DSI — génération complète</span>'
        if st.session_state.access_mode == MODE_DSI
        else '<span class="pill pill-warn">Mode Technicien — boucles désactivées</span>'
    )
    st.markdown(mode_pill, unsafe_allow_html=True)
    if st.session_state.access_mode == MODE_DSI:
        if st.button("Repasser en mode Technicien"):
            st.session_state.access_mode = MODE_TECHNICIEN
            st.rerun()
    else:
        dsi_pwd = st.text_input("Mot de passe DSI", type="password", key="dsi_pwd_input")
        if st.button("Activer le mode DSI"):
            if verify_dsi_password(dsi_pwd):
                st.session_state.access_mode = MODE_DSI
                st.rerun()
            else:
                st.error("Mot de passe incorrect.")
    st.markdown("---")

    c1, c2 = st.columns(2)
    with c1:
        # Toujours recharger depuis .env si session vide (fix après restart Streamlit)
        if "api_key" not in st.session_state or not st.session_state.api_key:
            from dotenv import load_dotenv
            load_dotenv(ROOT / ".env")
            st.session_state.api_key = os.environ.get("OPENROUTER_API_KEY", "")
        key_in = st.text_input("Cle API OpenRouter", value=st.session_state.api_key,
                               type="password", placeholder="sk-or-v1-...")
        if key_in.strip():
            st.session_state.api_key = key_in.strip()
    with c2:
        model_labels = list(FREE_MODELS.keys()) if FREE_MODELS else ["nemotron-super-120b"]
        model_ids    = list(FREE_MODELS.values()) if FREE_MODELS else ["nvidia/nemotron-3-super-120b-a12b:free"]
        def_idx      = model_ids.index(DEFAULT_MODEL) if DEFAULT_MODEL in model_ids else 0
        sel          = st.selectbox("Modele LLM", range(len(model_labels)), index=def_idx,
                                    format_func=lambda i: model_labels[i])
        model_choice = model_ids[sel]

    c3, c4 = st.columns(2)
    with c3:
        top_k = st.slider("Chunks RAG (top_k)", 3, 10, 6)
    with c4:
        skill_mode = st.selectbox(
            "Mode skill",
            ["auto","code","report","erd","perf"],
            help="auto: détection automatique | code: scripts MISPL | report: comptes-rendus | erd: tables GLIMS | perf: optimisations"
        )

    # Statut système
    m = _manifest()
    pills = []
    if _is_vs_ready():
        pills.append(f'<span class="pill pill-ok">Base · {m.get("known_functions_count","?")} fn</span>')
        build_ts = m.get("build_date") or m.get("timestamp") or m.get("built_at", "")
        if build_ts:
            try:
                date_str = str(build_ts)[:10]
                pills.append(f'<span class="pill pill-ok">Build {date_str}</span>')
            except Exception:
                pass
    else:
        pills.append('<span class="pill pill-err">Base absente</span>')
    pills.append(f'<span class="pill {"pill-ok" if _ok else "pill-err"}">{"Agent OK" if _ok else "Erreur"}</span>')
    api_ok = bool(st.session_state.get("api_key", ""))
    pills.append(f'<span class="pill {"pill-ok" if api_ok else "pill-warn"}">{"API OK" if api_ok else "API manquante"}</span>')
    st.markdown(" ".join(pills), unsafe_allow_html=True)

    if _err:
        with st.expander("Erreur import agent"):
            st.code(_err, language="text")

    # ── Monitoring ressources ─────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("**Ressources machine**")
    # Réutilise le moniteur déjà démarré au chargement du module (voir _mon plus
    # haut) — ne pas rappeler _start_resource_monitor() ici, un seul point d'entrée.
    if _mon is None:
        st.caption("Monitoring désactivé (MISPL_MONITOR=0) ou indisponible.")
    else:
        try:
            import psutil
            _vm = psutil.virtual_memory()
            mc1, mc2, mc3 = st.columns(3)
            mc1.metric("CPU", f"{psutil.cpu_percent():.0f}%")
            mc2.metric("RAM", f"{_vm.percent:.0f}%", f"{_vm.used/1024/1024/1024:.1f} Go")
            try:
                import GPUtil
                _g = GPUtil.getGPUs()
                if _g:
                    mc3.metric("GPU", f"{_g[0].load*100:.0f}%", f"{_g[0].memoryUsed:.0f} Mo VRAM")
                else:
                    mc3.metric("GPU", "—")
            except Exception:
                mc3.metric("GPU", "—")
        except Exception:
            pass
        st.caption(f"Relevé continu · {_mon.sample_count()} points collectés.")
        if st.button("Générer le rapport ressources (Plotly HTML)"):
            _report = _mon.write_report()
            if _report:
                st.success(f"Rapport écrit : {_report}")
                try:
                    with open(_report, "rb") as _f:
                        st.download_button("Télécharger le rapport HTML", _f,
                                           file_name=_report.name, mime="text/html")
                except Exception:
                    pass
            else:
                st.warning("Aucune donnée collectée pour le moment.")


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="margin:1.25rem 0 1.5rem">
  <div>
    <div style="font-size:1.45rem;font-weight:700;color:#f1f5f9;letter-spacing:-.02em;margin-bottom:.2rem">
      Assistant MISPL
    </div>
    <div style="font-size:.84rem;color:#64748b">
      Posez vos questions en francais — reponses sourcees depuis une base de connaissances MISPL constituee manuellement et enrichie de scripts de production valides du laboratoire.
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
if "messages"    not in st.session_state: st.session_state.messages    = []
if "rag_sources" not in st.session_state: st.session_state.rag_sources = []
if "lab_context" not in st.session_state: st.session_state.lab_context = ""


# ── Render sources ─────────────────────────────────────────────────────────────
def _render_sources(docs: list) -> None:
    if not docs:
        st.markdown('<span class="pill pill-warn">Sources non disponibles</span>', unsafe_allow_html=True)
        return
    with st.expander(f"Sources documentaires ({len(docs)})", expanded=False):
        for j, d in enumerate(docs, 1):
            fn    = html.escape(d.get("function_name",""))
            src   = html.escape(d.get("source","?").split("/")[-1])
            sc    = d.get("score",0)
            exact = d.get("exact_match")
            cls   = "cite cite-exact" if exact else "cite"
            tag   = "EXACT" if exact else f"#{j}"
            fn_row = f'<div class="cite-fn">{tag} · {fn}</div>' if fn else f'<div class="cite-fn">{tag}</div>'
            st.markdown(
                f'<div class="{cls}">'
                f'<div style="color:{"#10b981" if exact else "#3b82f6"};flex-shrink:0;margin-top:1px">{ICON_BOOK}</div>'
                f'<div class="cite-body" style="flex:1;min-width:0">{fn_row}'
                f'<div class="cite-src">{src}</div></div>'
                f'</div>',
                unsafe_allow_html=True,
            )


# ── Historique ────────────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    if msg["role"] == "user":
        with st.chat_message("user", avatar=USER_AVATAR):
            st.markdown(f'<div class="user-msg">{html.escape(msg["content"])}</div>', unsafe_allow_html=True)
    else:
        with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
            st.markdown(msg["content"])
            idx = msg.get("src_idx")
            if idx is not None and idx < len(st.session_state.rag_sources):
                docs = st.session_state.rag_sources[idx]
                if docs:
                    _render_sources(docs)


# ── Empty state + exemples ────────────────────────────────────────────────────
if not st.session_state.messages:
    st.markdown("""
    <div class="empty">
      <div class="empty-t">Aucune conversation</div>
      <div class="empty-d">Selectionnez un exemple ci-dessous ou tapez votre question.</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div style="font-size:.7rem;font-weight:700;color:#475569;text-transform:uppercase;letter-spacing:.1em;margin-bottom:.6rem">Exemples</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    for i, (label, query) in enumerate(EXAMPLES):
        col = c1 if i % 2 == 0 else c2
        if col.button(label, key=f"ex{i}", use_container_width=True):
            st.session_state["_q"] = query
            st.rerun()


# ── Input ─────────────────────────────────────────────────────────────────────
with st.expander("Contexte labo (optionnel)", expanded=False):
    st.session_state.lab_context = st.text_area(
        "Analyseur, tube, unités, contexte clinique...",
        value=st.session_state.lab_context,
        height=68,
        placeholder="ex: Analyseur Cobas c702, tube EDTA, unités SI, service hématologie",
        label_visibility="collapsed",
    )

_PLACEHOLDERS = [
    "ex: Comment utiliser Substr pour extraire une sous-chaîne ?",
    "ex: Comment arrondir un nombre avec Round ?",
    "ex: Comment écrire un log d'audit avec AddLogEntry ?",
    "ex: Comment formater la date du jour ?",
    "ex: Comment récupérer l'utilisateur connecté ?",
    "ex: Comment convertir un entier en chaîne ?",
    "ex: Comment éviter la division entière silencieuse ?",
    "ex: Comment gérer une valeur inconnue en MISPL ?",
]
# Placeholder figé une fois par session (un changement de placeholder recrée le
# widget chat_input et fait perdre la valeur soumise → bug "rien ne se passe")
if "chat_placeholder" not in st.session_state:
    import random as _rnd
    st.session_state.chat_placeholder = _rnd.choice(_PLACEHOLDERS)
_ph = st.session_state.chat_placeholder

# chat_input TOUJOURS appelé (jamais dans un if) — sinon Streamlit ne le rend pas
_typed = st.chat_input(_ph)
question: str | None = st.session_state.pop("_q", None) or _typed or None


# ── Traitement ────────────────────────────────────────────────────────────────
if question:
    if not _ok:
        st.error("Agent non charge. Voir Parametres > Erreur import agent.")
        st.stop()
    if not st.session_state.get("api_key", ""):
        st.error("OPENROUTER_API_KEY manquante — ouvrir Parametres et entrer la cle.")
        st.stop()
    if not _is_vs_ready():
        st.error("Base documentaire absente. Lancer : .\\start.ps1 build")
        st.stop()

    active_skills = None if skill_mode == "auto" else SKILL_PROFILES.get(skill_mode)

    # Enrichir la question avec le contexte labo si renseigné (non affiché dans la bulle)
    question_enriched = question
    if st.session_state.get("lab_context", "").strip():
        question_enriched = f"[Contexte labo: {st.session_state.lab_context.strip()}]\n\n{question}"

    # Historique AVANT d'ajouter la question courante (évite doublon dans le prompt LLM).
    # Filtré sur role/content : les messages assistant portent aussi src_idx (métadonnée
    # UI interne) que certaines API rejettent comme clé de message inconnue.
    _history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages[-12:]]

    # DLP — vérification sur le texte réellement envoyé au LLM : question + contexte
    # labo + historique de conversation de la session, pas uniquement la question
    # brute. Un IPP/NIR (ou toute donnée détectée) déjà présent dans l'historique
    # doit être re-évalué à chaque tour, pas seulement au moment où il a été tapé
    # (miroir du comportement de api/routers/chat.py).
    _history_text = "\n".join(m["content"] for m in _history)
    _dlp_text = f"{question_enriched}\n{_history_text}" if _history_text else question_enriched
    _dlp_blocked, _dlp_alerts = dlp_check(_dlp_text)
    if _dlp_blocked:
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user", avatar=USER_AVATAR):
            st.markdown(f'<div class="user-msg">{html.escape(question)}</div>', unsafe_allow_html=True)
        with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
            st.error(
                "🚫 **Message bloqué — Identifiant patient détecté**\n\n"
                f"Donnée(s) détectée(s) : **{', '.join(_dlp_alerts)}**\n\n"
                "Ne pas inclure de données patient (IPP, NIR...) dans les questions "
                "ou le contexte labo.\nReformulez avec des valeurs fictives ou génériques.",
                icon=None,
            )
        logging.warning(f"[DLP] Message bloqué — patterns: {_dlp_alerts}")
        st.stop()
    elif _dlp_alerts:
        logging.warning(f"[DLP] Avertissement (non bloquant) — patterns: {_dlp_alerts}")
        st.toast(f"⚠️ Donnée potentiellement sensible détectée ({', '.join(_dlp_alerts)}). Fermez la page si envoi non voulu.", icon="⚠️")

    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user", avatar=USER_AVATAR):
        st.markdown(f'<div class="user-msg">{html.escape(question)}</div>', unsafe_allow_html=True)

    with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
        placeholder = st.empty()
        placeholder.markdown(
            '<div class="thinking"><span class="d"></span><span class="d"></span><span class="d"></span>'
            '<span style="margin-left:6px">Recherche dans la documentation GLIMS...</span></div>',
            unsafe_allow_html=True,
        )
        final = ""
        docs  = []
        try:
            # api_key passée en paramètre direct (pas de mutation de os.environ,
            # partagé entre toutes les sessions du process Streamlit)
            final, docs = _ask_mispl(
                question_enriched, use_openai_embeddings=False, top_k=top_k,
                model=model_choice, skill_profile=active_skills,
                save_session=True,
                conversation_history=_history,
                api_key=st.session_state.get("api_key", ""),
                access_mode=st.session_state.access_mode,
            )
            placeholder.markdown(final)
        except Exception as _exc:
            error_id = str(uuid.uuid4())[:8]
            logging.error(f"[{error_id}] Erreur ask_mispl: {traceback.format_exc()}")
            _exc_str = str(_exc).lower()
            if any(k in _exc_str for k in ("connection", "timeout", "rate", "503", "502", "429", "unavailable")):
                final = (
                    "**Service temporairement indisponible** — OpenRouter ne répond pas.\n\n"
                    "- Attendre 30–60 secondes et réessayer\n"
                    "- Changer de modèle dans Paramètres (essayer `llama-3.2-3b` — plus léger)\n"
                    f"- Référence erreur : `{error_id}`"
                )
            else:
                final = f"**Erreur serveur** — Référence : `{error_id}`\n\nContactez l'administrateur si le problème persiste."
            placeholder.markdown(final)

        src_idx = len(st.session_state.rag_sources)
        st.session_state.rag_sources.append(docs)
        st.session_state.messages.append({"role": "assistant", "content": final, "src_idx": src_idx})
        if docs:
            _render_sources(docs)


# ── Reset / Export ────────────────────────────────────────────────────────────
if st.session_state.messages:
    st.markdown("<div style='height:.75rem'></div>", unsafe_allow_html=True)
    col_reset, col_export = st.columns([1, 1])
    with col_reset:
        st.markdown('<div class="reset-row">', unsafe_allow_html=True)
        if st.button("Nouvelle conversation", key="reset", use_container_width=True):
            st.session_state.messages    = []
            st.session_state.rag_sources = []
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with col_export:
        lines = []
        for msg in st.session_state.messages:
            role = "Vous" if msg["role"] == "user" else "Assistant MISPL"
            lines.append(f"[{role}]\n{msg['content']}\n")
        export_txt = "\n---\n".join(lines)
        import datetime as _dt
        fname = f"mispl_conversation_{_dt.datetime.now().strftime('%Y%m%d_%H%M')}.txt"
        st.download_button(
            "Exporter conversation",
            data=export_txt.encode("utf-8"),
            file_name=fname,
            mime="text/plain",
            use_container_width=True,
            key="export",
        )
