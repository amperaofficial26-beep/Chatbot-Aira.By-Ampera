from __future__ import annotations

import os
import re
import sys
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import streamlit as st


# ---------------------------------------------------------------------------
# Impor modul lokal (aman: UI tetap hidup meski dependensi belum lengkap)
# ---------------------------------------------------------------------------

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if _BASE_DIR not in sys.path:
    sys.path.insert(0, _BASE_DIR)

SEARCH_IMPORT_ERROR = ""
LLM_IMPORT_ERROR = ""

try:
    from search_engine import (  # type: ignore
        resolve_query,
        search_knowledge,
        load_knowledge,
        DEFAULT_KB_PATH,
        NO_MEMORY_MSG,
    )
except Exception as _search_exc:  # pragma: no cover - fallback runtime
    SEARCH_IMPORT_ERROR = f"{_search_exc.__class__.__name__}: {_search_exc}"
    DEFAULT_KB_PATH = os.path.join(_BASE_DIR, "knowledge.json")
    NO_MEMORY_MSG = "Tidak ada memori spesifik"

    def resolve_query(user_input: str, last_bot_response: str = "") -> str:
        return (user_input or "").strip()

    def search_knowledge(query: str, **kwargs: Any) -> str:
        return NO_MEMORY_MSG

    def load_knowledge(path: str = DEFAULT_KB_PATH) -> list:
        return []

try:
    from llm_engine import (  # type: ignore
        load_model,
        generate_aira_response,
        load_model_or_mock,
        find_gguf_models,
        DEFAULT_MODEL_PATH,
        ModelNotFoundError,
    )
except Exception as _llm_exc:  # pragma: no cover - fallback runtime
    LLM_IMPORT_ERROR = f"{_llm_exc.__class__.__name__}: {_llm_exc}"
    DEFAULT_MODEL_PATH = os.path.join(
        _BASE_DIR, "models", "qwen2.5-3b-instruct-q4_k_m.gguf"
    )

    class ModelNotFoundError(FileNotFoundError):
        pass

    def find_gguf_models(models_dir: str = "") -> list:
        return []

    def load_model(model_path: str = DEFAULT_MODEL_PATH, **kwargs: Any) -> Any:
        raise RuntimeError(LLM_IMPORT_ERROR or "llm_engine tidak tersedia")

    def load_model_or_mock(model_path: str = DEFAULT_MODEL_PATH, **kwargs: Any) -> Any:
        return None

    def generate_aira_response(llm: Any, user_input: str, context: str = "", history=None, **kwargs: Any) -> str:
        return (
            "Modul llm_engine.py belum siap, jadi aku belum bisa berpikir pakai model. "
            "Cek instalasi llama-cpp-python dan file GGUF di folder models/ ya."
        )


# ---------------------------------------------------------------------------
# Konfigurasi halaman — HARUS menjadi perintah Streamlit pertama
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Aira - Asisten AI Lokal",
    page_icon="💠",
    layout="centered",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# Konstanta UI & persona cepat
# ---------------------------------------------------------------------------

APP_TITLE = "Aira - Asisten AI Lokal"
APP_TAGLINE = "Asisten AI lokal · ramah, privat, dan siap bantu di perangkatmu"

WELCOME_TEXT = (
    "Hai, aku **Aira**. Asisten AI lokal yang ramah dan siap bantu—mulai dari "
    "error Android, APK bandel, RAM mepet, sampai pertanyaan sehari-hari.\n\n"
    "Tulis aja keluhannya, atau pilih salah satu contoh di bawah. Percakapan "
    "kita jalan di perangkatmu, bukan di cloud."
)

GREETING_REPLY_DEFAULT = (
    "Halo! Aku Aira, asisten AI lokal kamu. Mau tanya sesuatu, lagi ada error, "
    "atau cuma mau kenalan dulu? Aku siap bantu."
)

IDENTITY_REPLY = (
    "Aku **Aira**. Asisten AI lokal yang ramah, santai, dan siap bantu. "
    "Aku jalan di perangkatmu—jadi obrolan kita lebih privat dibanding asisten cloud.\n\n"
    "Bisa aku bantu urusan teknis (terutama Android), penjelasan sistem, "
    "atau pertanyaan umum. Panggil aja Aira kapan pun kamu butuh."
)

EXAMPLE_PROMPTS = [
    "Siapa kamu?",
    "APK gagal install, Package Installer error",
    "RAM penuh, game keluar sendiri",
    "Bedanya RAM sama storage apa?",
]

# Kata teknis: kalau muncul, sapaan/identitas TIDAK di-bypass
# (mis. "halo, apkku error" harus masuk alur RAG).
_TECH_HINTS = {
    "apk", "xapk", "apkm", "apks", "installer", "install", "instal",
    "package", "parse", "error", "ram", "storage", "memori", "memory",
    "lag", "lemot", "fps", "game", "android", "ios", "windows", "os",
    "root", "rom", "update", "cache", "data", "battery", "panas",
    "overheat", "throttle", "signature", "unknown", "sources", "gguf",
    "model", "bug", "crash", "force", "close", "hp", "gpu", "cpu",
}

# Pola sapaan yang dianggap "langsung" (setelah dinormalisasi).
_GREETING_EXACT = {
    "halo", "hai", "hay", "hi", "hello", "hey", "yo", "helo",
    "halo aira", "hai aira", "hay aira", "hi aira", "hello aira", "hey aira",
    "halo kak", "hai kak", "halo dong", "hai dong",
    "selamat pagi", "selamat siang", "selamat sore", "selamat malam",
    "pagi", "siang", "sore", "malam",
    "pagi aira", "siang aira", "sore aira", "malam aira",
    "selamat pagi aira", "selamat siang aira", "selamat sore aira",
    "selamat malam aira",
    "apa kabar", "apa kabar aira", "apakabar", "gimana kabar",
    "gimana kabarnya", "how are you",
    "halo halo", "hai hai",
}

_IDENTITY_RE = re.compile(
    r"^(?:"
    r"siapa\s+(?:kamu|kau|anda|namamu|nama\s+kamu|nama\s+anda|nama\s+mu)"
    r"|kamu\s+siapa"
    r"|kau\s+siapa"
    r"|namamu\s+siapa"
    r"|nama\s+kamu\s+siapa"
    r"|nama\s+anda\s+siapa"
    r"|kamu\s+ini\s+siapa"
    r"|kamu\s+siapa\s+(?:sih|ya|dong)"
    r"|kenalan(?:\s+(?:dong|yuk|yu[k]|dulu))?"
    r"|perkenalkan(?:\s+diri(?:mu)?)?"
    r"|perkenalan(?:\s+dong)?"
    r"|aira\s+itu\s+siapa"
    r"|kamu\s+(?:robot|ai|asisten)(?:\s+ya)?"
    r"|kamu\s+aira"
    r")$",
    re.IGNORECASE,
)

_PUNCT_RE = re.compile(r"[\"'`~!@#$%^&*()_+\-={}\[\]|\\:;<>?,./]+")
_SPACE_RE = re.compile(r"\s+")

USER_AVATAR = "🙂"
AIRA_AVATAR = "💠"

MAX_HISTORY_FOR_LLM = 12  # pesan, bukan turn


# ---------------------------------------------------------------------------
# Utilitas teks & intent bypass
# ---------------------------------------------------------------------------

def _normalize_intent_text(text: str) -> str:
    """Huruf kecil, buang tanda baca, rapikan spasi."""
    cleaned = (text or "").lower().strip()
    cleaned = _PUNCT_RE.sub(" ", cleaned)
    cleaned = _SPACE_RE.sub(" ", cleaned).strip()
    return cleaned


def _daypart_label(now: Optional[datetime] = None) -> str:
    hour = (now or datetime.now()).hour
    if 4 <= hour < 11:
        return "pagi"
    if 11 <= hour < 15:
        return "siang"
    if 15 <= hour < 18:
        return "sore"
    return "malam"


def _greeting_reply(normalized: str) -> str:
    """Balasan sapaan singkat, menyesuaikan waktu bila relevan."""
    waktu = _daypart_label()
    if "pagi" in normalized:
        return (
            f"Selamat pagi! Aku Aira. Semoga harinya lancar. "
            f"Ada yang bisa aku bantu pagi ini?"
        )
    if "siang" in normalized:
        return "Selamat siang! Aku Aira. Mau dibantu apa hari ini?"
    if "sore" in normalized:
        return "Selamat sore! Aku Aira. Ada yang mau ditanyakan?"
    if "malam" in normalized:
        return "Selamat malam! Aku Aira. Masih semangat—mau dibantu apa?"
    if "kabar" in normalized:
        return (
            "Kabar baik. Aku Aira, siap sedia di perangkatmu. "
            "Kamu sendiri gimana—ada yang mau diurai?"
        )
    return (
        f"Halo, selamat {waktu}! Aku Aira, asisten AI lokal kamu. "
        f"Mau tanya sesuatu atau lagi ada yang error?"
    )


def detect_intent_bypass(user_input: str) -> Optional[str]:
    """Deteksi sapaan / identitas langsung.

    Jika cocok, kembalikan teks balasan cepat (tanpa retriever & tanpa SLM).
    Jika tidak, kembalikan None agar alur RAG jalan seperti biasa.

    Aturan ketat:
      - pesan pendek (maks 8 kata)
      - tidak memuat kata teknis
      - cocok exact greeting ATAU pola identitas
    """
    text = _normalize_intent_text(user_input)
    if not text:
        return None

    words = text.split()
    if len(words) > 8:
        return None

    if any(w in _TECH_HINTS for w in words):
        return None

    if text in _GREETING_EXACT:
        return _greeting_reply(text)

    if _IDENTITY_RE.match(text):
        return IDENTITY_REPLY

    return None


def get_last_bot_response(messages: List[Dict[str, str]]) -> str:
    """Ambil content asisten terakhir dari riwayat UI."""
    for item in reversed(messages):
        if item.get("role") == "assistant":
            return str(item.get("content") or "")
    return ""


def history_for_llm(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Siapkan history untuk SLM: tanpa pesan user yang baru saja masuk."""
    trimmed = [m for m in messages if m.get("role") in {"user", "assistant"}]
    if trimmed and trimmed[-1].get("role") == "user":
        trimmed = trimmed[:-1]
    if len(trimmed) > MAX_HISTORY_FOR_LLM:
        trimmed = trimmed[-MAX_HISTORY_FOR_LLM:]
    return trimmed

def set_ui_style():
    st.set_page_config(page_title="Aira - Cyberpunk AI Assistant", page_icon="⚡", layout="centered")

    st.markdown("""
    <style>
    /* ==========================================================
       1. BACKGROUND CIRCUIT BOARD (PCB) DENGAN EFEK GLOW BERJALAN
       ========================================================== */
    .stApp {
        background-color: #050814;
        background-image: 
            radial-gradient(circle at 50% 50%, rgba(0, 243, 255, 0.08) 0%, transparent 60%),
            linear-gradient(rgba(5, 8, 20, 0.85), rgba(5, 8, 20, 0.85)),
            url("data:image/svg+xml,%3Csvg width='80' height='80' viewBox='0 0 80 80' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='%2300f3ff' fill-opacity='0.05' fill-rule='evenodd'%3E%3Cpath d='M0 0h40v40H0V0zm40 40h40v40H40V40zm0-40h2v40h-2V0zm-40 40h40v2H0v-2zM20 0v80h2V0h-2zm40 0v80h2V0h-2z'/%3E%3C/g%3E%3C/svg%3E");
        background-size: cover;
        animation: circuitPulse 12s infinite alternate ease-in-out;
    }

    @keyframes circuitPulse {
        0% { filter: hue-rotate(0deg) brightness(1); }
        50% { filter: hue-rotate(180deg) brightness(1.2); }
        100% { filter: hue-rotate(360deg) brightness(1); }
    }

    /* ==========================================================
       2. EFEK MUNCUL PERLAHAN (FADE-IN & SLIDE-UP) UNTUK SEMUA TEKS/CHAT
       ========================================================== */
    @keyframes smoothAppear {
        from {
            opacity: 0;
            transform: translateY(12px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    [data-testid="stChatMessage"] {
        animation: smoothAppear 0.7s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        backdrop-filter: blur(16px) !important;
        -webkit-backdrop-filter: blur(16px) !important;
        border-radius: 20px !important;
        padding: 16px !important;
        margin-bottom: 14px !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
    }

    /* ==========================================================
       3. GELEMBUNG CHAT WHATSAPP STYLE (KIRI: AIRA, KANAN: USER)
       ========================================================== */
    /* Kotak Pesan Aira (Kiri - Glassmorphism Biru/Ungu Anime) */
    [data-testid="stChatMessage"]:nth-child(odd) {
        background: rgba(20, 25, 45, 0.75) !important;
        border: 1px solid rgba(0, 243, 255, 0.25) !important;
        border-left: 5px solid #00f3ff !important;
        margin-right: 20% !important;
        border-top-left-radius: 4px !important;
    }

    /* Kotak Pesan User (Kanan - Glassmorphism Neon Pink/Aksen Anime) */
    [data-testid="stChatMessage"]:nth-child(even) {
        background: rgba(45, 20, 55, 0.75) !important;
        border: 1px solid rgba(255, 0, 128, 0.25) !important;
        border-right: 5px solid #ff0080 !important;
        margin-left: 20% !important;
        border-top-right-radius: 4px !important;
    }

    /* ==========================================================
       4. TOMBOL DENGAN EFEK GLOW DAN TIMBUL SAAT DISENTUH KURSOR
       ========================================================== */
    div.stButton > button {
        background: rgba(15, 22, 36, 0.8) !important;
        backdrop-filter: blur(10px) !important;
        border: 1px solid rgba(0, 243, 255, 0.4) !important;
        color: #00f3ff !important;
        border-radius: 14px !important;
        font-weight: 600 !important;
        padding: 10px 24px !important;
        transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
    }

    div.stButton > button:hover {
        transform: translateY(-4px) scale(1.03) !important;
        background: rgba(0, 243, 255, 0.15) !important;
        border-color: #00f3ff !important;
        color: #ffffff !important;
        box-shadow: 0 0 25px rgba(0, 243, 255, 0.8), inset 0 0 10px rgba(0, 243, 255, 0.4) !important;
    }

    /* ==========================================================
       5. KOTAK INPUT PESAN ALA GEMINI (PANJANG LONJONG & NEON BERPUTAR)
       ========================================================== */
    @keyframes neonRotate {
        0% { filter: hue-rotate(0deg); }
        100% { filter: hue-rotate(360deg); }
    }

    /* Wrapper luar untuk efek garis neon berputar */
    [data-testid="stChatInput"] {
        border-radius: 35px !important;
        background: linear-gradient(60deg, #00f3ff, #ff0080, #7928ca, #00f3ff) !important;
        background-size: 300% 300% !important;
        animation: neonRotate 6s linear infinite !important;
        padding: 2px !important; /* Ketebalan garis neon berputar */
        box-shadow: 0 0 20px rgba(0, 243, 255, 0.4);
    }

    /* Kotak dalam input (Warna hitam legam khas Gemini) */
    [data-testid="stChatInput"] > div {
        background-color: #080c14 !important;
        border-radius: 33px !important;
        backdrop-filter: blur(10px);
    }

    [data-testid="stChatInput"] textarea {
        color: #ffffff !important;
    }

    /* Styling Teks Umum agar Konsisten */
    html, body, [class*="css"] {
        font-family: 'Segoe UI', Roboto, Helvetica, sans-serif !important;
        color: #e2e8f0 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# Panggil fungsi ini di baris paling atas app.py
set_ui_style()
# ---------------------------------------------------------------------------
# Resource yang di-cache (model GGUF TIDAK boleh di-load ulang tiap Enter)
# ---------------------------------------------------------------------------

@st.cache_resource(show_spinner="Memuat otak Aira (model GGUF)... jangan ditutup dulu.")
def get_cached_llm() -> Dict[str, Any]:
    """Muat SLM sekali seumur proses Streamlit.

    `@st.cache_resource` menahan objek Llama di memori. Tanpa ini, setiap
    interaksi UI akan memuat ulang file .gguf (sangat lambat).
    """
    payload: Dict[str, Any] = {
        "llm": None,
        "mode": "error",
        "error": "",
        "path": DEFAULT_MODEL_PATH,
    }
    try:
        llm = load_model(model_path=DEFAULT_MODEL_PATH)
        payload["llm"] = llm
        payload["mode"] = "gguf"
        payload["path"] = getattr(llm, "aira_model_path", DEFAULT_MODEL_PATH)
        return payload
    except (ModelNotFoundError, FileNotFoundError, ImportError, RuntimeError) as exc:
        payload["error"] = str(exc).split("\n")[0]
        try:
            mock = load_model_or_mock(model_path=DEFAULT_MODEL_PATH)
            payload["llm"] = mock
            payload["mode"] = "mock" if mock is not None else "error"
            return payload
        except Exception as exc2:
            payload["error"] = f"{payload['error']} | fallback gagal: {exc2}"
            return payload
    except Exception as exc:
        payload["error"] = f"{exc.__class__.__name__}: {exc}"
        return payload


@st.cache_data(show_spinner=False)
def get_kb_status() -> Dict[str, Any]:
    """Status knowledge base untuk sidebar (aman dipanggil berulang)."""
    path = DEFAULT_KB_PATH
    info: Dict[str, Any] = {
        "path": path,
        "exists": os.path.isfile(path),
        "count": 0,
        "error": SEARCH_IMPORT_ERROR,
    }
    if not info["exists"]:
        return info
    try:
        items = load_knowledge(path)
        info["count"] = len(items)
    except Exception as exc:
        info["error"] = str(exc)
    return info


def warmup_retriever() -> Tuple[bool, str]:
    """Bangun indeks BM25 sekali di awal agar chat pertama tidak terasa jeda."""
    try:
        from search_engine import get_engine  # type: ignore

        get_engine()
        return True, ""
    except Exception as exc:
        return False, str(exc)


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

def init_session_state() -> None:
    """Inisialisasi memori chat UI dan flag bantu."""
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": WELCOME_TEXT}
        ]
    if "pending_prompt" not in st.session_state:
        st.session_state.pending_prompt = ""
    if "last_debug" not in st.session_state:
        st.session_state.last_debug = {
            "bypass": False,
            "resolved_query": "",
            "context": "",
        }
    if "retriever_ready" not in st.session_state:
        ok, err = warmup_retriever()
        st.session_state.retriever_ready = ok
        st.session_state.retriever_error = err


def reset_conversation() -> None:
    st.session_state.messages = [
        {"role": "assistant", "content": WELCOME_TEXT}
    ]
    st.session_state.last_debug = {
        "bypass": False,
        "resolved_query": "",
        "context": "",
    }
    st.session_state.pending_prompt = ""


def queue_example(prompt: str) -> None:
    """Tombol contoh: antrekan teks seolah user mengetiknya."""
    st.session_state.pending_prompt = prompt


# ---------------------------------------------------------------------------
# Alur RAG
# ---------------------------------------------------------------------------

def run_rag_pipeline(
    user_input: str,
    last_bot_response: str,
    llm: Any,
) -> Tuple[str, str, str]:
    """resolve_query -> search_knowledge -> generate_aira_response.

    Returns:
        (jawaban, resolved_query, context)
    """
    resolved = user_input
    context = ""

    try:
        resolved = resolve_query(user_input, last_bot_response=last_bot_response) or user_input
    except Exception:
        resolved = user_input

    try:
        context = search_knowledge(resolved) or ""
    except Exception:
        context = ""

    history = history_for_llm(st.session_state.messages)
    reply = generate_aira_response(
        llm=llm,
        user_input=user_input,
        context=context,
        history=history,
    )
    return (reply or "").strip(), resolved, context


def handle_user_message(user_input: str, llm: Any) -> None:
    """Satu siklus chat: tampilkan user -> bypass / RAG -> tampilkan Aira."""
    text = (user_input or "").strip()
    if not text:
        return

    last_bot = get_last_bot_response(st.session_state.messages)

    st.session_state.messages.append({"role": "user", "content": text})
    with st.chat_message("user", avatar=USER_AVATAR):
        st.markdown(text)

    bypass_reply = detect_intent_bypass(text)
    if bypass_reply:
        answer = bypass_reply
        st.session_state.last_debug = {
            "bypass": True,
            "resolved_query": text,
            "context": "(dilewati — intent sapaan/identitas)",
        }
    else:
        with st.spinner("Aira sedang berpikir..."):
            try:
                answer, resolved, context = run_rag_pipeline(
                    user_input=text,
                    last_bot_response=last_bot,
                    llm=llm,
                )
            except Exception as exc:
                traceback.print_exc()
                answer = (
                    "Aduh, ada kendala waktu aku merangkai jawaban. "
                    f"Detail teknis: `{exc.__class__.__name__}`."
                )
                resolved, context = text, ""
        if not answer:
            answer = "Hmm, aku blank barusan. Coba kirim ulang ya."
        st.session_state.last_debug = {
            "bypass": False,
            "resolved_query": resolved,
            "context": context,
        }

    st.session_state.messages.append({"role": "assistant", "content": answer})
    with st.chat_message("assistant", avatar=AIRA_AVATAR):
        st.markdown(answer)


# ---------------------------------------------------------------------------
# Komponen UI
# ---------------------------------------------------------------------------

def render_sidebar(model_info: Dict[str, Any]) -> None:
    kb = get_kb_status()
    mode = model_info.get("mode", "error")

    with st.sidebar:
        st.markdown("## 💠 Aira")
        st.caption("Status sistem lokal")

        if mode == "gguf":
            st.markdown(
                '<span class="aira-chip ok">MODEL · GGUF siap</span>',
                unsafe_allow_html=True,
            )
        elif mode == "mock":
            st.markdown(
                '<span class="aira-chip warn">MODEL · mode mock</span>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<span class="aira-chip err">MODEL · tidak dimuat</span>',
                unsafe_allow_html=True,
            )

        st.write("")
        if kb["exists"] and kb["count"] > 0:
            st.markdown(
                f'<span class="aira-chip ok">MEMORI · {kb["count"]} entri</span>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<span class="aira-chip warn">MEMORI · knowledge.json?</span>',
                unsafe_allow_html=True,
            )

        st.divider()
        st.markdown("**Perangkat**")
        st.write(f"Model: `{os.path.basename(str(model_info.get('path') or DEFAULT_MODEL_PATH))}`")
        st.write(f"Mode inferensi: `{mode}`")
        retriever_flag = "siap" if st.session_state.get("retriever_ready") else "bermasalah"
        st.write(f"Retriever BM25: `{retriever_flag}`")
        st.write(f"Riwayat UI: `{len(st.session_state.messages)}` pesan")

        if mode == "mock":
            st.info(
                "File GGUF belum dipakai. Letakkan model instruct di folder "
                "`models/` (mis. Qwen 2.5 3B Q4_K_M) agar jawaban benar-benar dari SLM.",
                icon="ℹ️",
            )
        if model_info.get("error") and mode != "gguf":
            with st.expander("Detail pemuatan model"):
                st.code(str(model_info["error"])[:1200])
        if SEARCH_IMPORT_ERROR:
            st.warning(f"search_engine: {SEARCH_IMPORT_ERROR}")
        if LLM_IMPORT_ERROR:
            st.warning(f"llm_engine: {LLM_IMPORT_ERROR}")
        if kb.get("error") and not SEARCH_IMPORT_ERROR:
            st.caption(f"KB: {kb['error']}")

        detected = []
        try:
            detected = find_gguf_models(os.path.join(_BASE_DIR, "models"))
        except Exception:
            detected = []
        if detected:
            with st.expander("File GGUF terdeteksi"):
                for path in detected:
                    st.caption(os.path.basename(path))

        st.divider()
        if st.button("🧹  Percakapan baru", use_container_width=True):
            reset_conversation()
            st.rerun()

        st.markdown("**Coba tanyakan**")
        for sample in EXAMPLE_PROMPTS:
            if st.button(sample, use_container_width=True, key=f"ex_{sample}"):
                queue_example(sample)
                st.rerun()

        with st.expander("Debug RAG terakhir"):
            dbg = st.session_state.get("last_debug") or {}
            st.write("Bypass intent:", dbg.get("bypass"))
            st.write("Query ter-resolve:")
            st.code(dbg.get("resolved_query") or "-")
            st.write("Konteks memori:")
            ctx = dbg.get("context") or "-"
            st.text(ctx if len(str(ctx)) < 2500 else str(ctx)[:2500] + "…")

        st.caption("Aira berjalan lokal. Tidak ada data yang dikirim ke server eksternal oleh aplikasi ini.")


def render_header() -> None:
    st.title(APP_TITLE)
    st.caption(APP_TAGLINE)


def render_history() -> None:
    for item in st.session_state.messages:
        role = item.get("role", "assistant")
        avatar = USER_AVATAR if role == "user" else AIRA_AVATAR
        with st.chat_message(role, avatar=avatar):
            st.markdown(item.get("content") or "")


def render_footer() -> None:
    st.markdown(
        '<p class="aira-foot">Aira · asisten AI lokal · RAG + SLM GGUF</p>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Entry point Streamlit
# ---------------------------------------------------------------------------

def main() -> None:
    inject_css()
    init_session_state()

    model_info = get_cached_llm()
    render_sidebar(model_info)
    render_header()
    render_history()

    typed = st.chat_input("Tulis pesan untuk Aira…")
    pending = (st.session_state.get("pending_prompt") or "").strip()
    if pending:
        st.session_state.pending_prompt = ""

    user_text = (typed or pending or "").strip()
    if user_text:
        handle_user_message(user_text, llm=model_info.get("llm"))

    render_footer()


main()

