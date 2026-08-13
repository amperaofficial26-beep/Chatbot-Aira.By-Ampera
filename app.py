#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
app.py
======
Antarmuka utama (UI) + hub logika Chatbot Aira.
Tampilan: Cyberpunk Anime Glassmorphism + PCB + WhatsApp chat
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

    def generate_aira_response(llm: Any, user_input: str, context: str = "", history=None, **kwargs: Any) -> str:
        if context and context != NO_MEMORY_MSG:
            return f"Berdasarkan memori lokal yang aku punya:\n\n{context}"
        return (
            "Aku Aira! Saat ini model GGUF belum dimuat penuh di server Cloud. "
            "Tapi kamu bisa bertanya seputar error Android, APK, RAM, atau fitur sistem lainnya!"
        )


# ---------------------------------------------------------------------------
# Konfigurasi Halaman
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
            --violet: #7c3aed;
            --text: #e6edf7;
            --muted: #8ea0b8;
            --ok: #22d3ee;
            --warn: #fbbf24;
            --err: #fb7185;
        }

        html, body, [data-testid="stAppViewContainer"], .stApp {
            background: var(--bg) !important;
            color: var(--text);
            font-family: "Share Tech Mono", "Segoe UI", sans-serif;
        }

        [data-testid="stHeader"],
        [data-testid="stToolbar"],
        [data-testid="stDecoration"] {
            background: transparent !important;
        }
        #MainMenu { visibility: hidden; }
        footer { visibility: hidden; }

        /* PCB substrate */
        [data-testid="stAppViewContainer"]::before {
            content: "";
            position: fixed;
            inset: 0;
            z-index: 0;
            pointer-events: none;
            background-color: var(--bg);
            background-image:
                radial-gradient(circle at 2px 2px, rgba(0, 243, 255, 0.22) 1.2px, transparent 0),
                linear-gradient(rgba(0, 243, 255, 0.045) 1px, transparent 1px),
                linear-gradient(90deg, rgba(0, 243, 255, 0.045) 1px, transparent 1px);
            background-size: 42px 42px, 42px 42px, 42px 42px;
        }

        [data-testid="stMain"], [data-testid="stMainBlockContainer"] {
            background: transparent !important;
            position: relative;
            z-index: 1;
        }

        [data-testid="stMainBlockContainer"] {
            padding-top: 0.6rem !important;
            max-width: 780px;
        }

        /* ---------- PCB overlay ---------- */
        .pcb-layer {
            position: fixed;
            inset: 0;
            z-index: 0;
            pointer-events: none;
            overflow: hidden;
        }
        .pcb-layer svg { width: 100%; height: 100%; display: block; }
        .pcb-trace {
            fill: none;
            stroke-linecap: square;
            stroke-linejoin: miter;
        }
        .pcb-base { stroke: rgba(0, 243, 255, 0.18); stroke-width: 1.6; }
        .pcb-base.pink { stroke: rgba(255, 0, 128, 0.16); }
        .pcb-run {
            stroke: #00f3ff;
            stroke-width: 2.2;
            filter: drop-shadow(0 0 6px #00f3ff);
            stroke-dasharray: 28 220;
            animation: traceRun 5.5s linear infinite;
        }
        .pcb-run.slow {
            stroke: #ff4db8;
            filter: drop-shadow(0 0 7px #ff0080);
            stroke-dasharray: 22 280;
            animation-duration: 8s;
            animation-direction: reverse;
        }
        .pcb-pad {
            fill: #050814;
            stroke: rgba(0, 243, 255, 0.55);
            stroke-width: 1.4;
            filter: drop-shadow(0 0 5px rgba(0, 243, 255, 0.45));
        }
        .pcb-node {
            fill: #00f3ff;
            filter: drop-shadow(0 0 8px #00f3ff);
            animation: nodePulse 2.8s ease-in-out infinite;
        }

        .element-container:has(.pcb-layer) {
            position: fixed !important;
            inset: 0;
            height: 0 !important;
            margin: 0 !important;
            overflow: visible !important;
        }

        /* ---------- text fade ---------- */
        @keyframes textIn {
            from { opacity: 0; transform: translateY(10px); filter: blur(4px); }
            to   { opacity: 1; transform: none; filter: none; }
        }
        h1, h2, h3, [data-testid="stCaption"],
        .app-head, .aira-profile, .wa-row, .aira-foot, .splash-inner {
            animation: textIn 0.65s ease both;
        }

        /* ---------- header ---------- */
        .app-head {
            display: flex;
            align-items: center;
            gap: 14px;
            margin: 6px 0 18px;
        }
        .app-logo {
            flex: 0 0 auto;
            width: 58px;
            height: 58px;
            border-radius: 16px;
            display: grid;
            place-items: center;
            background: #000;
            border: 1px solid rgba(0, 243, 255, 0.45);
            box-shadow: 0 0 22px rgba(0, 243, 255, 0.25);
            font-family: Orbitron, sans-serif;
            font-weight: 700;
            color: var(--cyan);
            letter-spacing: -0.04em;
        }
        .app-logo span { color: var(--pink); font-size: 0.72rem; }
        .app-head h1 {
            font-family: Orbitron, sans-serif !important;
            font-size: 1.55rem;
            margin: 0 !important;
            color: #f5fbff !important;
            text-shadow: 0 0 16px rgba(0, 243, 255, 0.3);
        }
        .app-head p {
            margin: 2px 0 0;
            color: var(--muted);
            font-size: 0.86rem;
        }

        /* ---------- WhatsApp-like chat ---------- */
        .wa-thread { display: flex; flex-direction: column; gap: 10px; }
        .wa-row {
            display: flex;
            align-items: flex-end;
            gap: 8px;
            width: 100%;
        }
        .wa-row.left { justify-content: flex-start; }
        .wa-row.right { justify-content: flex-end; }

        .wa-avatar {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            object-fit: cover;
            flex: 0 0 36px;
        }
        .wa-avatar-aira {
            border: 2px solid var(--cyan);
            box-shadow: 0 0 10px rgba(0, 243, 255, 0.45);
        }
        .wa-avatar-user {
            display: grid;
            place-items: center;
            background: #16081a;
            border: 2px solid var(--pink);
            box-shadow: 0 0 10px rgba(255, 0, 128, 0.35);
            font-size: 16px;
        }
        .wa-fallback {
            display: grid;
            place-items: center;
            background: #04161b;
            color: var(--cyan);
            font-family: Orbitron, sans-serif;
            font-weight: 700;
        }

        .wa-bubble {
            max-width: min(74%, 520px);
            padding: 10px 13px 12px;
            line-height: 1.5;
            font-size: 0.95rem;
            position: relative;
            word-wrap: break-word;
        }
        .wa-bubble strong { color: #fff; }
        .wa-bubble code {
            background: rgba(0,0,0,.35);
            padding: 1px 5px;
            border-radius: 5px;
            color: var(--cyan);
        }

        .wa-aira {
            background: linear-gradient(180deg, #16324a 0%, #102536 100%);
            color: #e8f4ff;
            border-radius: 16px 16px 16px 5px;
            border: 1px solid rgba(0, 243, 255, 0.22);
            box-shadow: 0 8px 22px rgba(0,0,0,.28), 0 0 12px rgba(0, 243, 255, 0.08);
        }
        .wa-user {
            background: linear-gradient(180deg, #3a1840 0%, #2a0f30 100%);
            color: #ffeaf6;
            border-radius: 16px 16px 5px 16px;
            border: 1px solid rgba(255, 0, 128, 0.28);
            box-shadow: 0 8px 22px rgba(0,0,0,.28), 0 0 12px rgba(255, 0, 128, 0.10);
        }

        /* ---------- console logic ---------- */
        .clog {
            min-width: 230px;
            background: #02060b;
            border: 1px solid rgba(0, 243, 255, 0.28);
            border-radius: 10px;
            overflow: hidden;
            box-shadow: inset 0 0 18px rgba(0, 243, 255, 0.08);
            font-family: "Share Tech Mono", monospace;
        }
        .clog-top {
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 6px 10px;
            background: #071018;
            border-bottom: 1px solid rgba(0, 243, 255, 0.15);
        }
        .clog-dot { width: 8px; height: 8px; border-radius: 50%; }
        .clog-dot.r { background: #ff5f57; }
        .clog-dot.y { background: #febc2e; }
        .clog-dot.g { background: #28c840; }
        .clog-title { margin-left: 6px; color: var(--cyan); font-size: 0.72rem; letter-spacing: 0.08em; }
        .clog-body { padding: 8px 10px 10px; }
        .clog-line {
            color: #7dffe3;
            font-size: 0.78rem;
            line-height: 1.55;
            animation: textIn 0.28s ease both;
        }
        .clog-gt { color: var(--pink); margin-right: 4px; }
        .clog-cursor {
            display: inline-block;
            color: var(--cyan);
            animation: blink 0.8s step-end infinite;
            font-size: 0.78rem;
        }

        /* ---------- chat input: kapsul hitam + glow mutar ---------- */
        [data-testid="stBottom"],
        [data-testid="stBottomBlockContainer"],
        [data-testid="stChatInputContainer"],
        .stChatFloatingInputContainer {
            background: transparent !important;
            overflow: visible !important;
        }

        [data-testid="stChatInput"] {
            position: relative !important;
            background: #000 !important;
            border: 0 !important;
            border-radius: 999px !important;
            overflow: visible !important;
            box-shadow: 0 0 18px rgba(0, 243, 255, 0.12);
        }
        [data-testid="stChatInput"]::before {
            content: "";
            position: absolute;
            inset: -3px;
            border-radius: 999px;
            padding: 3px;
            background: conic-gradient(from var(--spin), #00f3ff, #7c3aed, #ff0080, #00f3ff);
            -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
            -webkit-mask-composite: xor;
            mask-composite: exclude;
            animation: spinBorder 2.6s linear infinite;
            z-index: 0;
            filter: drop-shadow(0 0 8px rgba(0, 243, 255, 0.55));
            pointer-events: none;
        }
        [data-testid="stChatInput"] > * { position: relative; z-index: 1; }

        [data-testid="stChatInput"] textarea,
        [data-testid="stChatInput"] [data-baseweb="textarea"],
        [data-testid="stChatInput"] [data-baseweb="base-input"],
        [data-testid="stChatInput"] div[data-testid="stChatInputTextArea"] {
            background: #000 !important;
            color: #eaf4ff !important;
            border: none !important;
            border-radius: 999px !important;
        }
        [data-testid="stChatInput"] textarea::placeholder { color: #6d7f96 !important; }

        @property --spin {
            syntax: "<angle>";
            initial-value: 0deg;
            inherits: false;
        }

        /* ---------- buttons: glow + timbul ---------- */
        .stButton > button {
            background: #000 !important;
            color: var(--cyan) !important;
            border: 1px solid rgba(0, 243, 255, 0.45) !important;
            border-radius: 12px !important;
            letter-spacing: 0.03em;
            transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease !important;
        }
        .stButton > button:hover {
            transform: translateY(-3px) scale(1.02) !important;
            border-color: var(--cyan) !important;
            box-shadow:
                0 0 8px rgba(0, 243, 255, 0.55),
                0 0 22px rgba(0, 243, 255, 0.28),
                0 10px 18px rgba(0, 0, 0, 0.35) !important;
            color: #fff !important;
        }
        .stButton > button:active {
            transform: translateY(0) scale(0.99) !important;
        }
        button[data-testid="baseButton-primary"] {
            min-height: 54px;
            font-family: Orbitron, sans-serif !important;
            letter-spacing: 0.42em !important;
            font-size: 1.05rem !important;
            border-radius: 999px !important;
            box-shadow: 0 0 24px rgba(0, 243, 255, 0.25) !important;
        }

        /* ---------- sidebar / WA profile ---------- */
        [data-testid="stSidebar"] {
            background: rgba(4, 8, 18, 0.94) !important;
            border-right: 1px solid rgba(0, 243, 255, 0.14) !important;
        }
        [data-testid="stSidebar"] * { color: var(--text); }

        .aira-profile {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 8px 4px 14px;
        }
        .aira-profile img, .aira-profile .ph {
            width: 64px;
            height: 64px;
            border-radius: 50%;
            object-fit: cover;
            border: 3px solid var(--cyan);
            box-shadow: 0 0 0 4px rgba(0, 243, 255, 0.12), 0 0 18px rgba(0, 243, 255, 0.4);
        }
        .aira-profile .ph {
            display: grid;
            place-items: center;
            background: #04161b;
            font-family: Orbitron, sans-serif;
            color: var(--cyan);
            font-weight: 700;
        }
        .aira-name {
            font-family: Orbitron, sans-serif;
            font-size: 1.15rem;
            color: #fff;
        }
        .aira-online {
            display: flex;
            align-items: center;
            gap: 6px;
            color: #9fe7c4;
            font-size: 0.82rem;
            margin-top: 2px;
        }
        .aira-online i {
            width: 8px; height: 8px; border-radius: 50%;
            background: #25d366;
            box-shadow: 0 0 8px #25d366;
            display: inline-block;
        }

        .aira-chip {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 999px;
            font-size: 0.76rem;
            margin: 3px 0;
        }
        .aira-chip.ok { background: rgba(34, 211, 238, 0.16); color: #7df0ff !important; border: 1px solid rgba(34,211,238,.4); }
        .aira-chip.warn { background: rgba(251, 191, 36, 0.14); color: #ffe08a !important; border: 1px solid rgba(251,191,36,.4); }
        .aira-chip.err { background: rgba(251, 113, 133, 0.14); color: #ffb3be !important; border: 1px solid rgba(251,113,133,.4); }

        .aira-foot {
            text-align: center;
            color: var(--muted) !important;
            font-size: 0.78rem;
            opacity: .75;
            margin-top: 18px;
        }

        /* ---------- splash ---------- */
        .splash-inner {
            min-height: 72vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
            position: relative;
            z-index: 2;
        }
        .splash-logo {
            font-family: Orbitron, sans-serif;
            font-size: clamp(4.2rem, 12vw, 7rem);
            font-weight: 700;
            color: #00f3ff;
            letter-spacing: -0.06em;
            line-height: 1;
            text-shadow:
                0 0 18px #00f3ff,
                0 0 48px rgba(0, 243, 255, 0.55),
                0 0 90px rgba(255, 0, 128, 0.25);
            animation: logoIn 1.3s cubic-bezier(.2,.8,.2,1) both, logoFlicker 4.5s 1.6s infinite;
        }
        .splash-logo span { color: #ff4db8; font-size: .42em; letter-spacing: 0; }
        .splash-brand {
            margin-top: 14px;
            letter-spacing: 0.55em;
            font-size: 0.78rem;
            color: #9adfff;
            animation: textIn 0.8s 0.7s both;
        }
        .splash-hello {
            margin-top: 18px;
            max-width: 440px;
            color: #d5e6f5;
            font-size: 1.05rem;
            line-height: 1.55;
            animation: textIn 0.9s 1.15s both;
        }
        .splash-scan {
            width: min(420px, 88vw);
            height: 2px;
            margin: 26px auto 10px;
            background: linear-gradient(90deg, transparent, #00f3ff, #ff0080, transparent);
            box-shadow: 0 0 12px #00f3ff;
            animation: scan 2.2s ease-in-out infinite;
        }

        ::-webkit-scrollbar { width: 8px; height: 8px; }
        ::-webkit-scrollbar-thumb { background: rgba(0,243,255,.35); border-radius: 99px; }

        @keyframes traceRun { to { stroke-dashoffset: -260; } }
        @keyframes nodePulse {
            0%, 100% { opacity: .45; r: 2.2; }
            50% { opacity: 1; }
        }
        @keyframes spinBorder { to { --spin: 360deg; } }
        @keyframes blink { 50% { opacity: 0; } }
        @keyframes scan {
            0%, 100% { transform: scaleX(.2); opacity: .4; }
            50% { transform: scaleX(1); opacity: 1; }
        }
        @keyframes logoIn {
            from { opacity: 0; transform: scale(.6) rotateX(40deg); filter: blur(12px); }
            to   { opacity: 1; transform: none; filter: none; }
        }
        @keyframes logoFlicker {
            0%, 92%, 100% { opacity: 1; }
            94% { opacity: .55; }
            96% { opacity: 1; transform: translateX(1px); }
        }

        @media (prefers-reduced-motion: reduce) {
            .pcb-run, [data-testid="stChatInput"]::before, .splash-logo,
            h1, h2, h3, .wa-row, .app-head, .aira-profile { animation: none !important; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_pcb_layer() -> None:
    st.markdown(
        """
        <div class="pcb-layer" aria-hidden="true">
          <svg viewBox="0 0 1600 900" preserveAspectRatio="xMidYMid slice">
            <path class="pcb-trace pcb-base" d="M40 110 H320 V230 H610 V120 H880 V300 H1200 V90 H1560"/>
            <path class="pcb-trace pcb-run"  d="M40 110 H320 V230 H610 V120 H880 V300 H1200 V90 H1560"/>

            <path class="pcb-trace pcb-base pink" d="M1560 210 H1280 V380 H980 V260 H720 V470 H430 V340 H80"/>
            <path class="pcb-trace pcb-run slow" d="M1560 210 H1280 V380 H980 V260 H720 V470 H430 V340 H80"/>

            <path class="pcb-trace pcb-base" d="M20 520 H260 V680 H540 V560 H830 V760 H1140 V620 H1500"/>
            <path class="pcb-trace pcb-run"  d="M20 520 H260 V680 H540 V560 H830 V760 H1140 V620 H1500"/>

            <path class="pcb-trace pcb-base pink" d="M200 820 H500 V700 H760 V840 H1100 V730 H1460"/>
            <path class="pcb-trace pcb-run slow" d="M200 820 H500 V700 H760 V840 H1100 V730 H1460"/>

            <path class="pcb-trace pcb-base" d="M780 20 V180 H980 V40"/>
            <path class="pcb-trace pcb-run"  d="M780 20 V180 H980 V40"/>

            <circle class="pcb-pad" cx="320" cy="110" r="6"/>
            <circle class="pcb-pad" cx="610" cy="230" r="6"/>
            <circle class="pcb-pad" cx="880" cy="120" r="6"/>
            <circle class="pcb-pad" cx="1280" cy="210" r="6"/>
            <circle class="pcb-pad" cx="720" cy="260" r="6"/>
            <circle class="pcb-pad" cx="540" cy="680" r="6"/>
            <circle class="pcb-pad" cx="830" cy="560" r="6"/>
            <circle class="pcb-pad" cx="760" cy="700" r="6"/>
            <circle class="pcb-node" cx="320" cy="110" r="2.3"/>
            <circle class="pcb-node" cx="880" cy="120" r="2.3"/>
            <circle class="pcb-node" cx="720" cy="260" r="2.3"/>
            <circle class="pcb-node" cx="830" cy="560" r="2.3"/>
          </svg>
        </div>
        """,
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

MAX_HISTORY_FOR_LLM = 12


# ---------------------------------------------------------------------------
# Utilitas teks
# ---------------------------------------------------------------------------

def _normalize_intent_text(text: str) -> str:
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
# Media + bubble WhatsApp
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def get_profile_image() -> Dict[str, str]:
    names = ("aira.jpg", "aira.jpeg", "aira.png", "aira.webp")
    folders = (_BASE_DIR, os.path.join(_BASE_DIR, "assets"))
    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }
    for folder in folders:
        for name in names:
            path = os.path.join(folder, name)
            if os.path.isfile(path):
                ext = os.path.splitext(name)[1].lower()
                with open(path, "rb") as fh:
                    raw = fh.read()
                return {
                    "mime": mime_map.get(ext, "image/jpeg"),
                    "b64": base64.b64encode(raw).decode("ascii"),
                    "path": path,
                }
    return {"mime": "", "b64": "", "path": ""}


def md_lite(text: str) -> str:
    t = html.escape(text or "")
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    return t.replace("\n", "<br>")


def aira_avatar_html(photo: Dict[str, str]) -> str:
    if photo.get("b64"):
        return (
            f'<img class="wa-avatar wa-avatar-aira" '
            f'src="data:{photo["mime"]};base64,{photo["b64"]}" alt="Aira">'
        )
    return '<div class="wa-avatar wa-avatar-aira wa-fallback">A</div>'


def build_wa_row(role: str, inner_html: str, photo: Dict[str, str]) -> str:
    if role == "user":
        avatar = '<div class="wa-avatar wa-avatar-user">🙂</div>'
        return (
            f'<div class="wa-row right">'
            f'<div class="wa-bubble wa-user">{inner_html}</div>{avatar}'
            f"</div>"
        )
    avatar = aira_avatar_html(photo)
    return (
        f'<div class="wa-row left">{avatar}'
        f'<div class="wa-bubble wa-aira">{inner_html}</div>'
        f"</div>"
    )


def show_wa(role: str, text: str, photo: Dict[str, str], *, raw: bool = False) -> None:
    inner = text if raw else md_lite(text)
    st.markdown(build_wa_row(role, inner, photo), unsafe_allow_html=True)


def render_console_html(lines: List[str]) -> str:
    rows = "".join(
        f'<div class="clog-line"><span class="clog-gt">&gt;</span> {html.escape(line)}</div>'
        for line in lines
    )
    return (
        '<div class="clog">'
        '<div class="clog-top">'
        '<span class="clog-dot r"></span><span class="clog-dot y"></span>'
        '<span class="clog-dot g"></span>'
        '<span class="clog-title">AIRA://logic-trace</span>'
        "</div>"
        f'<div class="clog-body">{rows}<div class="clog-cursor">█</div></div>'
        "</div>"
    )


def push_console(placeholder: Any, photo: Dict[str, str], lines: List[str], delay: float = 0.16) -> None:
    placeholder.markdown(
        build_wa_row("assistant", render_console_html(lines), photo),
        unsafe_allow_html=True,
    )
    if delay > 0:
        time.sleep(delay)


# ---------------------------------------------------------------------------
# Resource caching
# ---------------------------------------------------------------------------

@st.cache_resource(show_spinner="Memuat otak Aira...")
def get_cached_llm() -> Dict[str, Any]:
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


def ensure_runtime_ready() -> None:
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
    st.session_state.pending_prompt = prompt


# ---------------------------------------------------------------------------
# RAG + message handling
# ---------------------------------------------------------------------------

def run_rag_pipeline(
    user_input: str,
    last_bot_response: str,
    llm: Any,
    photo: Dict[str, str],
    console_box: Any,
) -> Tuple[str, str, str]:
    logs = ["[BOOT] AIRA.CORE online"]
    push_console(console_box, photo, logs)

    resolved = user_input
    context = ""

    logs.append("[PARSE] tokenize + resolve query")
    push_console(console_box, photo, logs)
    try:
        resolved = resolve_query(user_input, last_bot_response=last_bot_response) or user_input
    except Exception:
        resolved = user_input
    snippet = resolved.replace("\n", " ")[:46]
    logs.append(f"[PTR] q = \"{snippet}\"")
    push_console(console_box, photo, logs)

    logs.append("[MEM] scan local knowledge.json")
    push_console(console_box, photo, logs, 0.05)
    try:
        context = search_knowledge(resolved) or ""
    except Exception:
        context = ""

    if context and context != NO_MEMORY_MSG:
        logs.append("[HIT] memory fragment locked")
    else:
        logs.append("[MISS] no specific memory")
    push_console(console_box, photo, logs)

    logs.append("[GEN] synthesize neural reply...")
    push_console(console_box, photo, logs, 0.08)

    history = history_for_llm(st.session_state.messages)
    reply = generate_aira_response(
        llm=llm,
        user_input=user_input,
        context=context,
        history=history,
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
        st.session_state.last_debug = {
            "bypass": True,
            "resolved_query": text,
            "context": "(dilewati — intent sapaan/identitas)",
        }
    else:
        try:
            answer, resolved, context = run_rag_pipeline(
                user_input=text,
                last_bot_response=last_bot,
                llm=llm,
                photo=photo,
                console_box=console_box,
            )
        except Exception as exc:
            traceback.print_exc()
            answer = f"Ada kendala teknis saat memproses jawaban: `{exc.__class__.__name__}`"
            resolved, context = text, ""

        if not answer:
            answer = "Hmm, aku belum tau jawabannya. Bisa coba tanyakan dengan kalimat lain?"

        st.session_state.last_debug = {
            "bypass": False,
            "resolved_query": resolved,
            "context": context,
        }

    time.sleep(0.12)
    console_box.markdown(build_wa_row("assistant", md_lite(answer), photo), unsafe_allow_html=True)
    st.session_state.messages.append({"role": "assistant", "content": answer})


# ---------------------------------------------------------------------------
# Sidebar / header / splash
# ---------------------------------------------------------------------------

def render_sidebar(model_info: Dict[str, Any], photo: Dict[str, str]) -> None:
    kb = get_kb_status()
    mode = model_info.get("mode", "error")

    with st.sidebar:
        if photo.get("b64"):
            pic = (
                f'<img src="data:{photo["mime"]};base64,{photo["b64"]}" alt="Aira">'
            )
        else:
            pic = '<div class="ph">A</div>'

        st.markdown(
            f"""
            <div class="aira-profile">
              {pic}
              <div>
                <div class="aira-name">Aira</div>
                <div class="aira-online"><i></i> online · A.ai</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption("Status Sistem Lokal")

        if mode == "gguf":
            st.markdown('<span class="aira-chip ok">MODEL · GGUF Siap</span>', unsafe_allow_html=True)
        elif mode == "mock":
            st.markdown('<span class="aira-chip warn">MODEL · Knowledge-Base Active</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="aira-chip err">MODEL · Offline</span>', unsafe_allow_html=True)

        st.write("")
        if kb["exists"] and kb["count"] > 0:
            st.markdown(
                f'<span class="aira-chip ok">MEMORI · {kb["count"]} Entri</span>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<span class="aira-chip warn">MEMORI · knowledge.json tidak ditemukan</span>',
                unsafe_allow_html=True,
            )

        st.divider()
        st.markdown("**Informasi Sistem**")
        st.write(f"Mode: `{mode}`")
        st.write(f"Knowledge Items: `{kb.get('count', 0)}`")
        if not photo.get("b64"):
            st.caption("Letakkan `aira.jpg` di folder app untuk foto profil.")

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
    st.markdown(
        '<p class="aira-foot">Aira · Asisten AI Lokal · Ampera Official</p>',
        unsafe_allow_html=True,
    )


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
          <p class="splash-hello">
            Selamat datang di salah satu app<br>
            <strong>Ampera Official</strong>
          </p>
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
