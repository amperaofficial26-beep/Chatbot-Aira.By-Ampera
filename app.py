#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
app.py
======
Aira · Cyberpunk UI + PCB artwork + WhatsApp chat + splash Ampera Official
"""

from __future__ import annotations

import base64
import html
import os
import re
import sys
import time
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

# ---------------------------------------------------------------------------
# Impor modul lokal
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
except Exception as _search_exc:  # pragma: no cover
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
except Exception as _llm_exc:  # pragma: no cover
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

    def generate_aira_response(
        llm: Any, user_input: str, context: str = "", history=None, **kwargs: Any
    ) -> str:
        if context and context != NO_MEMORY_MSG:
            return f"Berdasarkan memori lokal yang aku punya:\n\n{context}"
        return (
            "Aku Aira! Saat ini model GGUF belum dimuat penuh di server Cloud. "
            "Tapi kamu bisa bertanya seputar error Android, APK, RAM, atau fitur sistem lainnya!"
        )


# ---------------------------------------------------------------------------
# Halaman
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Aira - Asisten AI Lokal",
    page_icon="💠",
    layout="centered",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

def set_ui_style() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700&family=Share+Tech+Mono&display=swap');

        :root {
            --bg: #03050c;
            --cyan: #00f3ff;
            --pink: #ff0080;
            --text: #e6edf7;
            --muted: #8ea0b8;
        }

        html, body, [data-testid="stAppViewContainer"], .stApp {
            background: var(--bg) !important;
            color: var(--text);
            font-family: "Share Tech Mono", "Segoe UI", sans-serif;
        }

        [data-testid="stHeader"],
        [data-testid="stToolbar"],
        [data-testid="stDecoration"] { background: transparent !important; }
        #MainMenu, footer { visibility: hidden; }

        [data-testid="stAppViewContainer"]::before {
            content: "";
            position: fixed;
            inset: 0;
            z-index: 0;
            pointer-events: none;
            background:
                radial-gradient(ellipse 70% 50% at 15% 10%, rgba(0,70,60,.16), transparent 55%),
                radial-gradient(ellipse 60% 45% at 88% 90%, rgba(70,0,45,.12), transparent 50%),
                #03050c;
        }

        [data-testid="stMain"], [data-testid="stMainBlockContainer"] {
            background: transparent !important;
            position: relative;
            z-index: 1;
        }
        [data-testid="stMainBlockContainer"] {
            padding-top: .6rem !important;
            max-width: 780px;
        }

        /* PCB */
        .pcb-layer { position: fixed; inset: 0; z-index: 0; pointer-events: none; overflow: hidden; }
        .pcb-layer svg { width: 100%; height: 100%; display: block; }
        .pcb-tr {
            fill: none; stroke: rgba(0,230,210,.40); stroke-width: 2.05;
            stroke-linecap: round; stroke-linejoin: miter;
        }
        .pcb-glow {
            fill: none; stroke-linecap: round; stroke-linejoin: miter;
            stroke-width: 2.5; stroke-dasharray: 34 240;
            animation: traceDraw 6.4s linear infinite;
        }
        .pcb-glow.c { stroke: #00f3ff; filter: drop-shadow(0 0 5px #00f3ff) drop-shadow(0 0 12px rgba(0,243,255,.45)); }
        .pcb-glow.p { stroke: #ff4db8; filter: drop-shadow(0 0 5px #ff0080) drop-shadow(0 0 12px rgba(255,0,128,.4)); animation-direction: reverse; }
        .pcb-glow.g { stroke: #ffe08a; filter: drop-shadow(0 0 5px #fbbf24); }
        .pcb-glow.d1 { animation-delay: -1.1s; animation-duration: 5.2s; }
        .pcb-glow.d2 { animation-delay: -2.6s; animation-duration: 7.4s; }
        .pcb-glow.d3 { animation-delay: -4.0s; animation-duration: 8.6s; }
        .pcb-glow.d4 { animation-delay: -5.5s; animation-duration: 6.0s; }
        .pcb-glow.d5 { animation-delay: -0.6s; animation-duration: 9.2s; }
        .pcb-pad { fill: #03050c; stroke: rgba(0,243,255,.75); stroke-width: 1.55; }
        .pcb-hole { fill: rgba(0,243,255,.55); }
        .element-container:has(.pcb-layer) {
            position: fixed !important; inset: 0; height: 0 !important;
            margin: 0 !important; overflow: visible !important;
        }
        @keyframes traceDraw { to { stroke-dashoffset: -280; } }

        /* fade teks */
        @keyframes textIn {
            from { opacity: 0; transform: translateY(10px); filter: blur(4px); }
            to   { opacity: 1; transform: none; filter: none; }
        }
        h1, h2, h3, [data-testid="stCaption"],
        .app-head, .aira-name, .aira-online, .wa-row, .aira-foot, .splash-inner {
            animation: textIn .65s ease both;
        }

        /* header */
        .app-head { display: flex; align-items: center; gap: 14px; margin: 6px 0 18px; }
        .app-logo {
            width: 58px; height: 58px; border-radius: 16px; display: grid; place-items: center;
            background: #000; border: 1px solid rgba(0,243,255,.45);
            box-shadow: 0 0 22px rgba(0,243,255,.25);
            font-family: Orbitron, sans-serif; font-weight: 700; color: var(--cyan);
        }
        .app-logo span { color: var(--pink); font-size: .72rem; }
        .app-head h1 {
            font-family: Orbitron, sans-serif !important; font-size: 1.55rem;
            margin: 0 !important; color: #f5fbff !important;
            text-shadow: 0 0 16px rgba(0,243,255,.3);
        }
        .app-head p { margin: 2px 0 0; color: var(--muted); font-size: .86rem; }

        /* chat WA */
        .wa-thread { display: flex; flex-direction: column; gap: 10px; }
        .wa-row { display: flex; align-items: flex-end; gap: 8px; width: 100%; }
        .wa-row.left { justify-content: flex-start; }
        .wa-row.right { justify-content: flex-end; }
        .wa-avatar {
            width: 36px; height: 36px; border-radius: 50%; flex: 0 0 36px;
            background-size: cover; background-position: center;
        }
        .wa-avatar-aira {
            border: 2px solid var(--cyan);
            box-shadow: 0 0 10px rgba(0,243,255,.45);
            background-color: #04161b;
        }
        .wa-avatar-user {
            display: grid; place-items: center; background: #16081a;
            border: 2px solid var(--pink); box-shadow: 0 0 10px rgba(255,0,128,.35);
        }
        .wa-fallback {
            display: grid; place-items: center; color: var(--cyan);
            font-family: Orbitron, sans-serif; font-weight: 700;
        }
        .wa-bubble {
            max-width: min(74%, 520px); padding: 10px 13px 12px;
            line-height: 1.5; font-size: .95rem; word-wrap: break-word;
        }
        .wa-bubble strong { color: #fff; }
        .wa-bubble code {
            background: rgba(0,0,0,.35); padding: 1px 5px; border-radius: 5px; color: var(--cyan);
        }
        .wa-aira {
            background: linear-gradient(180deg, #16324a 0%, #102536 100%);
            color: #e8f4ff; border-radius: 16px 16px 16px 5px;
            border: 1px solid rgba(0,243,255,.22);
            box-shadow: 0 8px 22px rgba(0,0,0,.28), 0 0 12px rgba(0,243,255,.08);
        }
        .wa-user {
            background: linear-gradient(180deg, #3a1840 0%, #2a0f30 100%);
            color: #ffeaf6; border-radius: 16px 16px 5px 16px;
            border: 1px solid rgba(255,0,128,.28);
            box-shadow: 0 8px 22px rgba(0,0,0,.28), 0 0 12px rgba(255,0,128,.10);
        }

        /* konsol */
        .clog {
            min-width: 230px; background: #02060b;
            border: 1px solid rgba(0,243,255,.28); border-radius: 10px;
            overflow: hidden; box-shadow: inset 0 0 18px rgba(0,243,255,.08);
            font-family: "Share Tech Mono", monospace;
        }
        .clog-top {
            display: flex; align-items: center; gap: 6px; padding: 6px 10px;
            background: #071018; border-bottom: 1px solid rgba(0,243,255,.15);
        }
        .clog-dot { width: 8px; height: 8px; border-radius: 50%; }
        .clog-dot.r { background: #ff5f57; }
        .clog-dot.y { background: #febc2e; }
        .clog-dot.g { background: #28c840; }
        .clog-title { margin-left: 6px; color: var(--cyan); font-size: .72rem; letter-spacing: .08em; }
        .clog-body { padding: 8px 10px 10px; }
        .clog-line { color: #7dffe3; font-size: .78rem; line-height: 1.55; animation: textIn .28s ease both; }
        .clog-gt { color: var(--pink); margin-right: 4px; }
        .clog-cursor { display: inline-block; color: var(--cyan); animation: blink .8s step-end infinite; }

        /* input kapsul + glow mutar */
        [data-testid="stBottom"],
        [data-testid="stBottomBlockContainer"],
        [data-testid="stChatInputContainer"],
        .stChatFloatingInputContainer {
            background: transparent !important; overflow: visible !important;
        }
        [data-testid="stChatInput"] {
            position: relative !important; background: #000 !important;
            border: 0 !important; border-radius: 999px !important;
            overflow: visible !important; box-shadow: 0 0 18px rgba(0,243,255,.12);
        }
        [data-testid="stChatInput"]::before {
            content: ""; position: absolute; inset: -3px; border-radius: 999px; padding: 3px;
            background: conic-gradient(from var(--spin), #00f3ff, #7c3aed, #ff0080, #00f3ff);
            -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
            -webkit-mask-composite: xor; mask-composite: exclude;
            animation: spinBorder 2.6s linear infinite; z-index: 0;
            filter: drop-shadow(0 0 8px rgba(0,243,255,.55)); pointer-events: none;
        }
        [data-testid="stChatInput"] > * { position: relative; z-index: 1; }
        [data-testid="stChatInput"] textarea,
        [data-testid="stChatInput"] [data-baseweb="textarea"],
        [data-testid="stChatInput"] [data-baseweb="base-input"] {
            background: #000 !important; color: #eaf4ff !important;
            border: none !important; border-radius: 999px !important;
        }
        [data-testid="stChatInput"] textarea::placeholder { color: #6d7f96 !important; }
        @property --spin { syntax: "<angle>"; initial-value: 0deg; inherits: false; }

        /* tombol */
        .stButton > button {
            background: #000 !important; color: var(--cyan) !important;
            border: 1px solid rgba(0,243,255,.45) !important; border-radius: 12px !important;
            transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease !important;
        }
        .stButton > button:hover {
            transform: translateY(-3px) scale(1.02) !important;
            border-color: var(--cyan) !important; color: #fff !important;
            box-shadow: 0 0 8px rgba(0,243,255,.55), 0 0 22px rgba(0,243,255,.28), 0 10px 18px rgba(0,0,0,.35) !important;
        }
        .stButton > button:active { transform: translateY(0) scale(.99) !important; }
        button[data-testid="baseButton-primary"] {
            min-height: 54px; font-family: Orbitron, sans-serif !important;
            letter-spacing: .42em !important; font-size: 1.05rem !important;
            border-radius: 999px !important; box-shadow: 0 0 24px rgba(0,243,255,.25) !important;
        }

        /* sidebar */
        [data-testid="stSidebar"] {
            background: rgba(4,8,18,.94) !important;
            border-right: 1px solid rgba(0,243,255,.14) !important;
        }
        [data-testid="stSidebar"] * { color: var(--text); }
        [data-testid="stSidebar"] [data-testid="stImage"] img {
            border-radius: 50% !important; object-fit: cover !important;
            width: 72px !important; height: 72px !important;
            border: 3px solid #00f3ff !important;
            box-shadow: 0 0 0 4px rgba(0,243,255,.12), 0 0 18px rgba(0,243,255,.45) !important;
        }
        .aira-name { font-family: Orbitron, sans-serif; font-size: 1.15rem; color: #fff; }
        .aira-online { display: flex; align-items: center; gap: 6px; color: #9fe7c4; font-size: .82rem; margin-top: 2px; }
        .aira-online i {
            width: 8px; height: 8px; border-radius: 50%; background: #25d366;
            box-shadow: 0 0 8px #25d366; display: inline-block;
        }
        .ph {
            width: 72px; height: 72px; border-radius: 50%; display: grid; place-items: center;
            background: #04161b; border: 3px solid var(--cyan);
            font-family: Orbitron, sans-serif; color: var(--cyan); font-weight: 700;
        }
        .aira-chip {
            display: inline-block; padding: 4px 10px; border-radius: 999px; font-size: .76rem; margin: 3px 0;
        }
        .aira-chip.ok { background: rgba(34,211,238,.16); color: #7df0ff !important; border: 1px solid rgba(34,211,238,.4); }
        .aira-chip.warn { background: rgba(251,191,36,.14); color: #ffe08a !important; border: 1px solid rgba(251,191,36,.4); }
        .aira-chip.err { background: rgba(251,113,133,.14); color: #ffb3be !important; border: 1px solid rgba(251,113,133,.4); }
        .aira-foot { text-align: center; color: var(--muted) !important; font-size: .78rem; opacity: .75; margin-top: 18px; }

        /* splash */
        .splash-inner {
            min-height: 72vh; display: flex; flex-direction: column;
            align-items: center; justify-content: center; text-align: center; z-index: 2;
        }
        .splash-logo {
            font-family: Orbitron, sans-serif; font-size: clamp(4.2rem, 12vw, 7rem);
            font-weight: 700; color: #00f3ff; letter-spacing: -.06em; line-height: 1;
            text-shadow: 0 0 18px #00f3ff, 0 0 48px rgba(0,243,255,.55), 0 0 90px rgba(255,0,128,.25);
            animation: logoIn 1.3s cubic-bezier(.2,.8,.2,1) both, logoFlicker 4.5s 1.6s infinite;
        }
        .splash-logo span { color: #ff4db8; font-size: .42em; }
        .splash-brand { margin-top: 14px; letter-spacing: .55em; font-size: .78rem; color: #9adfff; animation: textIn .8s .7s both; }
        .splash-hello { margin-top: 18px; max-width: 440px; color: #d5e6f5; font-size: 1.05rem; line-height: 1.55; animation: textIn .9s 1.15s both; }
        .splash-scan {
            width: min(420px, 88vw); height: 2px; margin: 26px auto 10px;
            background: linear-gradient(90deg, transparent, #00f3ff, #ff0080, transparent);
            box-shadow: 0 0 12px #00f3ff; animation: scan 2.2s ease-in-out infinite;
        }

        ::-webkit-scrollbar { width: 8px; height: 8px; }
        ::-webkit-scrollbar-thumb { background: rgba(0,243,255,.35); border-radius: 99px; }

        @keyframes spinBorder { to { --spin: 360deg; } }
        @keyframes blink { 50% { opacity: 0; } }
        @keyframes scan { 0%,100% { transform: scaleX(.2); opacity: .4; } 50% { transform: scaleX(1); opacity: 1; } }
        @keyframes logoIn {
            from { opacity: 0; transform: scale(.6) rotateX(40deg); filter: blur(12px); }
            to   { opacity: 1; transform: none; filter: none; }
        }
        @keyframes logoFlicker {
            0%,92%,100% { opacity: 1; }
            94% { opacity: .55; }
            96% { opacity: 1; transform: translateX(1px); }
        }

        @media (prefers-reduced-motion: reduce) {
            .pcb-glow, [data-testid="stChatInput"]::before, .splash-logo,
            h1,h2,h3,.wa-row,.app-head { animation: none !important; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# PCB artwork (jalur 90/45 + pad, glow di banyak jalur)
# ---------------------------------------------------------------------------

def _pcb_pts(x: float, y: float, spec: str) -> List[Tuple[float, float]]:
    pts = [(x, y)]
    tok = spec.split()
    i = 0
    while i < len(tok):
        op, val = tok[i], float(tok[i + 1])
        i += 2
        if op == "H":
            x += val
        elif op == "V":
            y += val
        elif op == "SE":
            x += val
            y += val
        elif op == "NE":
            x += val
            y -= val
        elif op == "SW":
            x -= val
            y += val
        elif op == "NW":
            x -= val
            y -= val
        pts.append((x, y))
    return pts


def _pcb_markup() -> str:
    traces = [
        (-30, 32, "H 690", 1, "c d1"),
        (-30, 46, "H 560", 1, ""),
        (-30, 60, "H 780", 1, "c d3"),
        (-30, 74, "H 430 SE 28 H 170", 1, "p d2"),
        (-30, 88, "H 840", 1, ""),
        (-30, 102, "H 390", 1, "c d4"),
        (-30, 116, "H 610 V 34 H 150", 1, "g d1"),
        (-30, 130, "H 500", 1, ""),
        (-30, 144, "H 720", 1, "c d5"),
        (-30, 158, "H 340 SE 36 H 220", 1, "p d3"),
        (-30, 172, "H 660", 1, ""),
        (-30, 186, "H 470", 1, "c d2"),
        (-30, 200, "H 810", 1, ""),
        (-30, 214, "H 300 V 48 H 260", 1, "g d4"),
        (-30, 228, "H 590", 1, "c d1"),
        (-30, 242, "H 450 SE 24 H 90", 1, ""),
        (-30, 256, "H 700", 1, "p d5"),
        (-30, 270, "H 380", 1, ""),
        (-30, 284, "H 640 V -40 H 120", 1, "c d3"),
        (-30, 298, "H 520", 1, ""),
        (430, 74, "V 90 SE 40 H 80", 1, "c d2"),
        (610, 150, "V 70 SW 30 V 40", 1, ""),
        (720, 200, "SE 50 H 140 V 36", 1, "p d1"),
        (300, 262, "V 80 SE 46 H 100", 1, "g d5"),
        (120, 340, "H 260 SE 60 H 180 NE 40 H 220", 1, "c d4"),
        (80, 370, "H 200 SE 80 V 50 H 160", 1, ""),
        (200, 410, "H 340 NE 36 H 90 SE 50 H 130", 1, "p d2"),
        (40, 450, "H 180 V 70 H 240 SE 30 H 80", 1, "c d1"),
        (520, 360, "H 200 V 90 H 160 NE 44 H 70", 1, "g d3"),
        (700, 330, "SE 70 H 180 V 40 H 90", 1, "c d5"),
        (860, 300, "H 160 SE 36 H 200", 1, ""),
        (940, 380, "H 220 V 60 SE 40 H 80", 1, "p d4"),
        (400, 500, "H 280 SE 54 H 190 V 30", 1, "c d2"),
        (160, 540, "H 210 NE 40 H 150 SE 70 H 100", 1, ""),
        (620, 480, "V 80 H 140 SE 36 H 200", 1, "g d1"),
        (1620, 860, "H -220 NW 48 H -140 SW 36 H -180", 1, "c d1"),
        (1620, 838, "H -160 NW 70 H -90 SW 28 H -130", 1, "p d3"),
        (1620, 816, "H -300 NE 40 H -120 NW 50 H -80", 1, "c d5"),
        (1620, 794, "H -110 SW 60 H -200 NW 34 H -90", 1, "g d2"),
        (1620, 772, "H -250 NW 30 H -160", 1, ""),
        (1620, 750, "H -80 NW 90 H -140 SE 40 H -100", 1, "c d4"),
        (1620, 728, "H -190 SW 44 H -70 NW 60 H -150", 1, "p d1"),
        (1620, 706, "H -330", 1, ""),
        (1580, 684, "H -120 NW 56 H -200 V -40 H -80", 1, "c d3"),
        (1580, 662, "H -260 SE 30 H -90", 1, "g d5"),
        (1540, 640, "H -90 SW 70 H -180 NE 36 H -70", 1, "p d2"),
        (1500, 600, "H -160 NW 40 V -50 H -120", 1, "c d1"),
        (1480, 560, "H -220 SE 48 H -80 NW 30", 1, ""),
        (1460, 520, "H -100 NE 60 H -170 SW 40 H -60", 1, "c d4"),
        (1520, 480, "H -240 V 36 H -90", 1, "g d3"),
        (1560, 440, "H -180 SE 50 H -140", 1, "p d5"),
        (1600, 400, "H -300 NW 28 H -80", 1, "c d2"),
        (1600, 360, "H -140 SW 60 H -200", 1, ""),
        (1580, 320, "H -90 NE 44 H -230 SE 36", 1, "c d1"),
        (1180, 780, "NW 70 H -160 NE 40 H -90", 1, "p d4"),
        (1100, 700, "H -130 SW 50 H -80 V 40", 1, "c d3"),
        (1020, 620, "NE 36 H -150 SE 60 H -70", 1, "g d1"),
        (980, 820, "H -200 NW 48 V -30 H -90", 1, "c d5"),
        (880, 760, "SW 40 H -120 NE 70 H -60", 1, ""),
        (820, 680, "H -90 V 80 H -140 SE 30", 1, "p d2"),
        (-20, 780, "H 240 SE 40 H 180 V 30 H 90", 1, "c d4"),
        (-20, 810, "H 320 NE 28 H 140", 1, ""),
        (-20, 840, "H 180 SE 50 H 260 NW 20 H 80", 1, "p d1"),
        (-20, 870, "H 420", 1, "g d3"),
        (80, 720, "H 160 V 50 SE 36 H 120", 1, "c d2"),
        (200, 680, "SE 60 H 150 V 40 H 70", 1, ""),
        (360, 740, "H 200 NE 40 H 90 SE 30", 1, "c d5"),
        (900, 40, "H 220 SE 36 H 160", 1, "c d2"),
        (980, 70, "H 180 V 44 H 140", 1, ""),
        (1040, 110, "H 260 NE 24 H 80", 1, "p d4"),
        (1120, 150, "H 140 SE 50 H 190", 1, "c d1"),
        (1200, 200, "H 180 V -36 H 120", 1, "g d5"),
        (1280, 250, "SE 40 H 160 V 30", 1, ""),
        (900, 180, "H 160 V 70 SE 30 H 80", 1, "c d3"),
        (760, 90, "H 130 SE 46 H 70", 1, ""),
    ]
    extra_vias = [
        (430, 74), (610, 150), (300, 262), (520, 360), (700, 330),
        (1180, 780), (1100, 700), (820, 680), (200, 680), (760, 90),
        (940, 380), (400, 500),
    ]
    chunks = ['<svg viewBox="0 0 1600 900" preserveAspectRatio="xMidYMid slice">']
    for x, y, spec, via, glow in traces:
        pts = _pcb_pts(x, y, spec)
        d = "M " + " L ".join(f"{px:.1f} {py:.1f}" for px, py in pts)
        chunks.append(f'<path class="pcb-tr" d="{d}"/>')
        if glow:
            chunks.append(f'<path class="pcb-glow {glow}" d="{d}"/>')
        if via:
            vx, vy = pts[-1]
            chunks.append(f'<circle class="pcb-pad" cx="{vx:.1f}" cy="{vy:.1f}" r="5.1"/>')
            chunks.append(f'<circle class="pcb-hole" cx="{vx:.1f}" cy="{vy:.1f}" r="1.8"/>')
    for vx, vy in extra_vias:
        chunks.append(f'<circle class="pcb-pad" cx="{vx}" cy="{vy}" r="5.1"/>')
        chunks.append(f'<circle class="pcb-hole" cx="{vx}" cy="{vy}" r="1.8"/>')
    chunks.append("</svg>")
    return "".join(chunks)


def render_pcb_layer() -> None:
    st.markdown(
        f'<div class="pcb-layer" aria-hidden="true">{_pcb_markup()}</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Konstanta
# ---------------------------------------------------------------------------

APP_TITLE = "Aira - Asisten AI Lokal"
APP_TAGLINE = "Asisten AI lokal · ramah, privat, dan siap bantu di perangkatmu"

WELCOME_TEXT = (
    "Hai, aku **Aira**. Asisten AI lokal yang ramah dan siap bantu—mulai dari "
    "error Android, APK bandel, RAM mepet, sampai pertanyaan sehari-hari.\n\n"
    "Tulis aja keluhannya, atau pilih salah satu contoh di bawah. Percakapan "
    "kita jalan di perangkatmu, bukan di cloud."
)

IDENTITY_REPLY = (
    "Aku **Aira**. Asisten AI lokal yang ramah, santai, dan siap bantu. "
    "Aku dirancang untuk berjalan privat di perangkatmu.\n\n"
    "Bisa aku bantu urusan teknis (terutama Android), penjelasan sistem, "
    "atau pertanyaan umum. Panggil aja Aira kapan pun kamu butuh."
)

EXAMPLE_PROMPTS = [
    "Siapa kamu?",
    "APK gagal install, Package Installer error",
    "RAM penuh, game keluar sendiri",
    "Bedanya RAM sama storage apa?",
]

_TECH_HINTS = {
    "apk", "xapk", "apkm", "apks", "installer", "install", "instal",
    "package", "parse", "error", "ram", "storage", "memori", "memory",
    "lag", "lemot", "fps", "game", "android", "ios", "windows", "os",
    "root", "rom", "update", "cache", "data", "battery", "panas",
    "overheat", "throttle", "signature", "unknown", "sources", "gguf",
    "model", "bug", "crash", "force", "close", "hp", "gpu", "cpu",
}

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
    r"|kamu\s+siapa|kau\s+siapa|namamu\s+siapa|nama\s+kamu\s+siapa|nama\s+anda\s+siapa"
    r"|kamu\s+ini\s+siapa|kamu\s+siapa\s+(?:sih|ya|dong)"
    r"|kenalan(?:\s+(?:dong|yuk|yu[k]|dulu))?"
    r"|perkenalkan(?:\s+diri(?:mu)?)?|perkenalan(?:\s+dong)?"
    r"|aira\s+itu\s+siapa|kamu\s+(?:robot|ai|asisten)(?:\s+ya)?|kamu\s+aira"
    r")$",
    re.IGNORECASE,
)
_PUNCT_RE = re.compile(r"[\"'`~!@#$%^&*()_+\-={}\[\]|\\:;<>?,./]+")
_SPACE_RE = re.compile(r"\s+")
MAX_HISTORY_FOR_LLM = 12


# ---------------------------------------------------------------------------
# Intent
# ---------------------------------------------------------------------------

def _normalize_intent_text(text: str) -> str:
    cleaned = (text or "").lower().strip()
    cleaned = _PUNCT_RE.sub(" ", cleaned)
    return _SPACE_RE.sub(" ", cleaned).strip()


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
    waktu = _daypart_label()
    if "pagi" in normalized:
        return "Selamat pagi! Aku Aira. Semoga harinya lancar. Ada yang bisa aku bantu pagi ini?"
    if "siang" in normalized:
        return "Selamat siang! Aku Aira. Mau dibantu apa hari ini?"
    if "sore" in normalized:
        return "Selamat sore! Aku Aira. Ada yang mau ditanyakan?"
    if "malam" in normalized:
        return "Selamat malam! Aku Aira. Masih semangat—mau dibantu apa?"
    if "kabar" in normalized:
        return "Kabar baik. Aku Aira, siap sedia bantu kamu. Ada kendala atau pertanyaan?"
    return f"Halo, selamat {waktu}! Aku Aira, asisten AI kamu. Mau tanya sesuatu atau lagi ada yang error?"


def detect_intent_bypass(user_input: str) -> Optional[str]:
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
    for item in reversed(messages):
        if item.get("role") == "assistant":
            return str(item.get("content") or "")
    return ""


def history_for_llm(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
    trimmed = [m for m in messages if m.get("role") in {"user", "assistant"}]
    if trimmed and trimmed[-1].get("role") == "user":
        trimmed = trimmed[:-1]
    if len(trimmed) > MAX_HISTORY_FOR_LLM:
        trimmed = trimmed[-MAX_HISTORY_FOR_LLM:]
    return trimmed


# ---------------------------------------------------------------------------
# Foto + bubble
# ---------------------------------------------------------------------------

def find_profile_file() -> str:
    roots = [
        _BASE_DIR,
        os.path.join(_BASE_DIR, "assets"),
        os.path.join(_BASE_DIR, "static"),
        os.path.join(_BASE_DIR, "images"),
        os.getcwd(),
    ]
    names = (
        "aira.jpg", "aira.jpeg", "aira.png", "aira.webp",
        "Aira.jpg", "Aira.JPG", "AIRA.jpg", "aira.JPG",
    )
    seen = set()
    for root in roots:
        if not root or not os.path.isdir(root):
            continue
        for name in names:
            path = os.path.abspath(os.path.join(root, name))
            if path in seen:
                continue
            seen.add(path)
            if os.path.isfile(path):
                return path
        try:
            for fn in os.listdir(root):
                low = fn.lower()
                if low.startswith("aira") and low.endswith((".jpg", ".jpeg", ".png", ".webp")):
                    return os.path.abspath(os.path.join(root, fn))
        except OSError:
            pass
    return ""


@st.cache_data(show_spinner=False)
def get_profile_image() -> Dict[str, str]:
    path = find_profile_file()
    if not path:
        return {"mime": "", "b64": "", "path": ""}
    ext = os.path.splitext(path)[1].lower()
    mime = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}.get(ext, "image/jpeg")
    with open(path, "rb") as fh:
        raw = fh.read()
    return {"mime": mime, "b64": base64.b64encode(raw).decode("ascii"), "path": path}


def inject_avatar_css(photo: Dict[str, str]) -> None:
    if not photo.get("b64"):
        return
    st.markdown(
        f"""
        <style>
        .wa-avatar-aira {{
            background-image: url("data:{photo["mime"]};base64,{photo["b64"]}") !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def md_lite(text: str) -> str:
    t = html.escape(text or "")
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    return t.replace("\n", "<br>")


def aira_avatar_html(photo: Dict[str, str]) -> str:
    if photo.get("b64"):
        return '<div class="wa-avatar wa-avatar-aira" title="Aira"></div>'
    return '<div class="wa-avatar wa-avatar-aira wa-fallback">A</div>'


def build_wa_row(role: str, inner_html: str, photo: Dict[str, str]) -> str:
    if role == "user":
        return (
            f'<div class="wa-row right">'
            f'<div class="wa-bubble wa-user">{inner_html}</div>'
            f'<div class="wa-avatar wa-avatar-user">🙂</div></div>'
        )
    return (
        f'<div class="wa-row left">{aira_avatar_html(photo)}'
        f'<div class="wa-bubble wa-aira">{inner_html}</div></div>'
    )


def show_wa(role: str, text: str, photo: Dict[str, str]) -> None:
    st.markdown(build_wa_row(role, md_lite(text), photo), unsafe_allow_html=True)


def render_console_html(lines: List[str]) -> str:
    rows = "".join(
        f'<div class="clog-line"><span class="clog-gt">&gt;</span> {html.escape(line)}</div>'
        for line in lines
    )
    return (
        '<div class="clog"><div class="clog-top">'
        '<span class="clog-dot r"></span><span class="clog-dot y"></span>'
        '<span class="clog-dot g"></span><span class="clog-title">AIRA://logic-trace</span>'
        f'</div><div class="clog-body">{rows}<div class="clog-cursor">█</div></div></div>'
    )


def push_console(placeholder: Any, photo: Dict[str, str], lines: List[str], delay: float = 0.16) -> None:
    placeholder.markdown(
        build_wa_row("assistant", render_console_html(lines), photo),
        unsafe_allow_html=True,
    )
    if delay > 0:
        time.sleep(delay)


# ---------------------------------------------------------------------------
# Resource
# ---------------------------------------------------------------------------

@st.cache_resource(show_spinner="Memuat otak Aira...")
def get_cached_llm() -> Dict[str, Any]:
    payload: Dict[str, Any] = {"llm": None, "mode": "error", "error": "", "path": DEFAULT_MODEL_PATH}
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
    path = DEFAULT_KB_PATH
    info: Dict[str, Any] = {"path": path, "exists": os.path.isfile(path), "count": 0, "error": SEARCH_IMPORT_ERROR}
    if not info["exists"]:
        return info
    try:
        info["count"] = len(load_knowledge(path))
    except Exception as exc:
        info["error"] = str(exc)
    return info


def warmup_retriever() -> Tuple[bool, str]:
    try:
        from search_engine import get_engine  # type: ignore
        get_engine()
        return True, ""
    except Exception as exc:
        return False, str(exc)


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------

def init_session_state() -> None:
    if "entered_app" not in st.session_state:
        st.session_state.entered_app = False
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": WELCOME_TEXT}]
    if "pending_prompt" not in st.session_state:
        st.session_state.pending_prompt = ""
    if "last_debug" not in st.session_state:
        st.session_state.last_debug = {"bypass": False, "resolved_query": "", "context": ""}


def ensure_runtime_ready() -> None:
    if "retriever_ready" not in st.session_state:
        ok, err = warmup_retriever()
        st.session_state.retriever_ready = ok
        st.session_state.retriever_error = err


def reset_conversation() -> None:
    st.session_state.messages = [{"role": "assistant", "content": WELCOME_TEXT}]
    st.session_state.last_debug = {"bypass": False, "resolved_query": "", "context": ""}
    st.session_state.pending_prompt = ""


def queue_example(prompt: str) -> None:
    st.session_state.pending_prompt = prompt


# ---------------------------------------------------------------------------
# RAG
# ---------------------------------------------------------------------------

def run_rag_pipeline(
    user_input: str, last_bot_response: str, llm: Any, photo: Dict[str, str], console_box: Any
) -> Tuple[str, str, str]:
    logs = ["[BOOT] AIRA.CORE online"]
    push_console(console_box, photo, logs)

    resolved, context = user_input, ""
    logs.append("[PARSE] tokenize + resolve query")
    push_console(console_box, photo, logs)
    try:
        resolved = resolve_query(user_input, last_bot_response=last_bot_response) or user_input
    except Exception:
        resolved = user_input
    logs.append(f'[PTR] q = "{resolved.replace(chr(10), " ")[:46]}"')
    push_console(console_box, photo, logs)

    logs.append("[MEM] scan local knowledge.json")
    push_console(console_box, photo, logs, 0.05)
    try:
        context = search_knowledge(resolved) or ""
    except Exception:
        context = ""
    logs.append("[HIT] memory fragment locked" if context and context != NO_MEMORY_MSG else "[MISS] no specific memory")
    push_console(console_box, photo, logs)

    logs.append("[GEN] synthesize neural reply...")
    push_console(console_box, photo, logs, 0.08)

    reply = generate_aira_response(
        llm=llm, user_input=user_input, context=context, history=history_for_llm(st.session_state.messages)
    )
    return (reply or "").strip(), resolved, context


def handle_user_message(user_input: str, llm: Any, photo: Dict[str, str]) -> None:
    text = (user_input or "").strip()
    if not text:
        return

    last_bot = get_last_bot_response(st.session_state.messages)
    st.session_state.messages.append({"role": "user", "content": text})
    show_wa("user", text, photo)

    console_box = st.empty()
    bypass_reply = detect_intent_bypass(text)

    if bypass_reply:
        push_console(console_box, photo, ["[SYS] intent classifier"], 0.18)
        push_console(console_box, photo, ["[SYS] intent classifier", "[OK]  bypass template"], 0.22)
        answer = bypass_reply
        st.session_state.last_debug = {"bypass": True, "resolved_query": text, "context": "(dilewati — intent sapaan/identitas)"}
    else:
        try:
            answer, resolved, context = run_rag_pipeline(text, last_bot, llm, photo, console_box)
        except Exception as exc:
            traceback.print_exc()
            answer = f"Ada kendala teknis saat memproses jawaban: `{exc.__class__.__name__}`"
            resolved, context = text, ""
        if not answer:
            answer = "Hmm, aku belum tau jawabannya. Bisa coba tanyakan dengan kalimat lain?"
        st.session_state.last_debug = {"bypass": False, "resolved_query": resolved, "context": context}

    time.sleep(0.12)
    console_box.markdown(build_wa_row("assistant", md_lite(answer), photo), unsafe_allow_html=True)
    st.session_state.messages.append({"role": "assistant", "content": answer})


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

def render_sidebar(model_info: Dict[str, Any], photo: Dict[str, str]) -> None:
    kb = get_kb_status()
    mode = model_info.get("mode", "error")

    with st.sidebar:
        c1, c2 = st.columns([0.85, 1.7])
        with c1:
            if photo.get("path"):
                st.image(photo["path"], width=72)
            else:
                st.markdown('<div class="ph">A</div>', unsafe_allow_html=True)
        with c2:
            st.markdown(
                '<div class="aira-name">Aira</div><div class="aira-online"><i></i> online · A.ai</div>',
                unsafe_allow_html=True,
            )

        if not photo.get("path"):
            st.caption("Foto tidak ketemu. Taruh `aira.jpg` di folder yang sama dengan `app.py`.")

        st.caption("Status Sistem Lokal")
        if mode == "gguf":
            st.markdown('<span class="aira-chip ok">MODEL · GGUF Siap</span>', unsafe_allow_html=True)
        elif mode == "mock":
            st.markdown('<span class="aira-chip warn">MODEL · Knowledge-Base Active</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="aira-chip err">MODEL · Offline</span>', unsafe_allow_html=True)

        st.write("")
        if kb["exists"] and kb["count"] > 0:
            st.markdown(f'<span class="aira-chip ok">MEMORI · {kb["count"]} Entri</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="aira-chip warn">MEMORI · knowledge.json tidak ditemukan</span>', unsafe_allow_html=True)

        st.divider()
        st.markdown("**Informasi Sistem**")
        st.write(f"Mode: `{mode}`")
        st.write(f"Knowledge Items: `{kb.get('count', 0)}`")

        st.divider()
        if st.button("🧹 Percakapan Baru", use_container_width=True):
            reset_conversation()
            st.rerun()

        st.markdown("**Contoh Pertanyaan**")
        for sample in EXAMPLE_PROMPTS:
            if st.button(sample, use_container_width=True, key=f"ex_{sample}"):
                queue_example(sample)
                st.rerun()


def render_header() -> None:
    st.markdown(
        f"""
        <div class="app-head">
          <div class="app-logo">A<span>.ai</span></div>
          <div>
            <h1>{html.escape(APP_TITLE.split(" - ")[0])}</h1>
            <p>{html.escape(APP_TAGLINE)}</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_history(photo: Dict[str, str]) -> None:
    chunks = [
        build_wa_row(item.get("role", "assistant"), md_lite(item.get("content") or ""), photo)
        for item in st.session_state.messages
    ]
    st.markdown(f'<div class="wa-thread">{"".join(chunks)}</div>', unsafe_allow_html=True)


def render_footer() -> None:
    st.markdown('<p class="aira-foot">Aira · Asisten AI Lokal · Ampera Official</p>', unsafe_allow_html=True)


def render_splash() -> None:
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"],
        [data-testid="stSidebarCollapsedControl"],
        [data-testid="stHeader"] { display: none !important; }
        </style>
        <div class="splash-inner">
          <div class="splash-logo">A<span>.ai</span></div>
          <div class="splash-brand">AMPERA OFFICIAL</div>
          <div class="splash-scan"></div>
          <p class="splash-hello">Selamat datang di salah satu app<br><strong>Ampera Official</strong></p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    left, mid, right = st.columns([1, 1.15, 1])
    with mid:
        if st.button("MASUK", type="primary", use_container_width=True, key="btn_masuk"):
            st.session_state.entered_app = True
            st.rerun()


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------

def main() -> None:
    set_ui_style()
    render_pcb_layer()
    init_session_state()

    if not st.session_state.entered_app:
        render_splash()
        return

    ensure_runtime_ready()
    photo = get_profile_image()
    inject_avatar_css(photo)
    model_info = get_cached_llm()

    render_sidebar(model_info, photo)
    render_header()
    render_history(photo)

    typed = st.chat_input("Tulis pesan untuk Aira…")
    pending = (st.session_state.get("pending_prompt") or "").strip()
    if pending:
        st.session_state.pending_prompt = ""

    user_text = (typed or pending or "").strip()
    if user_text:
        handle_user_message(user_text, llm=model_info.get("llm"), photo=photo)

    render_footer()


if __name__ == "__main__":
    main()
