#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
app.py
======
Aira · PCB ungu-pink + sidebar glass + splash logo Ampera
       + proses berpikir + teks muncul perlahan
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


st.set_page_config(
    page_title="Aira - Asisten AI-Chatbot By Ampera",
    page_icon="💮",
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
            --bg: #07030f;
            --cyan: #00f3ff;
            --pink: #ff2ea6;
            --violet: #a855f7;
            --text: #f1e9ff;
            --muted: #b5a4c9;
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

        [data-testid="stMain"], [data-testid="stMainBlockContainer"] {
            background: transparent !important;
            position: relative;
            z-index: 1;
        }
        [data-testid="stMainBlockContainer"] {
            padding-top: .6rem !important;
            max-width: 780px;
        }

        .pcb-layer {
            position: fixed; inset: 0; z-index: 0;
            pointer-events: none; overflow: hidden;
            contain: strict; opacity: .78;
        }
        .pcb-layer svg { width: 100%; height: 100%; display: block; }
        .pcb-tr {
            fill: none; stroke: #8b5cf6; stroke-width: 1.7;
            stroke-linecap: square; stroke-linejoin: miter;
        }
        .pcb-tr.alt { stroke: #ec4899; }
        .pcb-glow {
            fill: none; stroke-linecap: square; stroke-linejoin: miter;
            stroke-width: 2.3; stroke-dasharray: 28 220;
            animation: traceDraw 8s linear infinite;
        }
        .pcb-glow.c { stroke: #d946ef; }
        .pcb-glow.p { stroke: #ff4db8; animation-direction: reverse; animation-duration: 10s; }
        .pcb-pad { fill: #07030f; stroke: #e879f9; stroke-width: 1.3; }
        .pcb-hole { fill: #f0abfc; }
        .element-container:has(.pcb-layer) {
            position: fixed !important; inset: 0; height: 0 !important;
            margin: 0 !important; overflow: visible !important;
        }
        @keyframes traceDraw { to { stroke-dashoffset: -248; } }

        .app-head { display: flex; align-items: center; gap: 14px; margin: 6px 0 18px; }
        .app-logo {
            width: 58px; height: 58px; border-radius: 16px; display: grid; place-items: center;
            background: #000; border: 1px solid rgba(236,72,153,.5);
            box-shadow: 0 0 16px rgba(168,85,247,.28);
            font-family: M PLUS Rounded 1c, sans-serif; font-weight: 700; color: #f0abfc;
            background-size: cover; background-position: center;
        }
        .app-logo span { color: var(--pink); font-size: .72rem; }
        .app-head h1 {
            font-family: M PLUS Rounded 1c, sans-serif !important; font-size: 1.55rem;
            margin: 0 !important; color: #ffe9fb !important;
        }
        .app-head p { margin: 2px 0 0; color: var(--muted); font-size: .86rem; }

        .wa-thread { display: flex; flex-direction: column; gap: 10px; }
        .wa-row { display: flex; align-items: flex-end; gap: 8px; width: 100%; }
        .wa-row.left { justify-content: flex-start; }
        .wa-row.right { justify-content: flex-end; }
        .wa-avatar {
            width: 36px; height: 36px; border-radius: 50%; flex: 0 0 36px;
            background-size: cover; background-position: center;
        }
        .wa-avatar-aira { border: 2px solid #e879f9; background-color: #1a0820; }
        .wa-avatar-user {
            display: grid; place-items: center; background: #16081a;
            border: 2px solid var(--pink);
        }
        .wa-fallback {
            display: grid; place-items: center; color: #f0abfc;
            font-family: M PLUS Rounded 1c, sans-serif; font-weight: 700;
        }
        .wa-bubble {
            max-width: min(74%, 520px); padding: 10px 13px 12px;
            line-height: 1.5; font-size: .95rem; word-wrap: break-word;
        }
        .wa-bubble strong { color: #fff; }
        .wa-bubble code {
            background: rgba(0,0,0,.35); padding: 1px 5px; border-radius: 5px; color: #f0abfc;
        }
        .wa-aira {
            background: #2a1540; color: #f6eaff;
            border-radius: 16px 16px 16px 5px;
            border: 1px solid rgba(168,85,247,.35);
        }
        .wa-user {
            background: #3a1030; color: #ffeaf6;
            border-radius: 16px 16px 5px 16px;
            border: 1px solid rgba(255,46,166,.35);
        }

        /* ---------- proses berpikir ---------- */
        .think {
            min-width: 230px;
            font-family: "Share Tech Mono", monospace;
        }
        .think-head {
            display: flex; align-items: center; gap: 8px;
            color: #e9d5ff; font-size: .72rem; letter-spacing: .14em;
            margin-bottom: 8px;
        }
        .think-orb {
            width: 9px; height: 9px; border-radius: 50%;
            background: #ff2ea6;
            box-shadow: 0 0 8px #ff2ea6;
            animation: pulseDot 1.1s ease-in-out infinite;
        }
        .think-now {
            color: #fff; font-size: .95rem; letter-spacing: .04em;
            min-height: 1.4em;
        }
        .think-now b { color: #f0abfc; font-weight: 700; }
        .think-dots::after {
            content: "";
            animation: dots 1.2s steps(4, end) infinite;
        }
        .think-bar {
            margin-top: 10px; height: 3px; border-radius: 99px;
            background: rgba(240,171,252,.12); overflow: hidden;
        }
        .think-bar i {
            display: block; height: 100%; width: 38%;
            background: linear-gradient(90deg, #a855f7, #ff2ea6);
            animation: barRun 1.15s ease-in-out infinite;
        }
        .think-log {
            margin-top: 8px; color: #c4b5fd; font-size: .72rem; line-height: 1.55;
        }
        .think-log .done { color: #86efac; }
        .think-log .wait { color: #f0abfc; }

        .type-caret {
            display: inline-block; width: 7px; height: .95em;
            margin-left: 2px; background: #ff2ea6; vertical-align: -2px;
            animation: blink .7s step-end infinite;
        }

       [data-testid="stBottom"],
        [data-testid="stBottomBlockContainer"],
        [data-testid="stChatInputContainer"],
        .stChatFloatingInputContainer {
            background: transparent !important; overflow: visible !important;
        }
        [data-testid="stChatInput"]::before {
            content: ""; position: absolute; inset: -2px; border-radius: 999px;
            background: conic-gradient(from var(--spin), #a855f7, #ff2ea6, #f0abfc, #a855f7);
            -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
            -webkit-mask-composite: xor; mask-composite: exclude;
            padding: 2px; animation: spinBorder 3.2s linear infinite;
            pointer-events: none; z-index: 0;
        }
        [data-testid="stChatInput"] > * { position: relative; z-index: 1; }
        [data-testid="stChatInput"] [data-baseweb="textarea"],
        [data-testid="stChatInput"] [data-baseweb="base-input"] {

        }
        [data-testid="stChatInput"] textarea::placeholder { color: #8b7798 !important; }
        @property --spin { syntax: "<angle>"; initial-value: 0deg; inherits: false; }
        
        [data-testid="stSidebar"] {
            background:
                radial-gradient(circle at 20% 0%, rgba(236,72,153,.18), transparent 42%),
                radial-gradient(circle at 90% 80%, rgba(168,85,247,.16), transparent 40%),
                rgba(10,4,18,.96) !important;
            border-right: 1px solid rgba(236,72,153,.22) !important;
        }
        [data-testid="stSidebar"] * { color: var(--text); }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { margin-bottom: .35rem; }
        section[data-testid="stSidebar"] > div { padding-top: .6rem; }

        .side-hero {
            position: relative;
            padding: 16px 14px 14px;
            margin: 0 0 14px;
            border-radius: 22px;
            background: linear-gradient(160deg, rgba(236,72,153,.16), rgba(88,28,135,.18) 55%, rgba(0,0,0,.35));
            border: 1px solid rgba(240,171,252,.28);
            overflow: hidden;
        }
        .side-hero::after {
            content: "";
            position: absolute; inset: auto 0 0 0; height: 2px;
            background: linear-gradient(90deg, transparent, #ff2ea6, #a855f7, transparent);
        }
        .side-ava-wrap {
            width: 86px; height: 86px; margin: 0 auto 10px; position: relative;
        }
        .side-ava, .ph {
            width: 86px; height: 86px; border-radius: 50%;
            background-color: #140814; background-size: cover; background-position: center;
            box-shadow: 0 0 0 2px #ff2ea6, 0 0 18px rgba(168,85,247,.45);
        }
        .side-ring {
            position: absolute; inset: -6px; border-radius: 50%;
            background: conic-gradient(from var(--spin), #ff2ea6, transparent 32%, #a855f7, transparent 68%, #ff2ea6);
            -webkit-mask: radial-gradient(farthest-side, transparent calc(100% - 3px), #000 0);
            mask: radial-gradient(farthest-side, transparent calc(100% - 3px), #000 0);
            animation: spinBorder 4s linear infinite;
            pointer-events: none;
        }
        .ph {
            display: grid; place-items: center;
            font-family: M PLUS Rounded 1c, sans-serif; color: #f0abfc; font-weight: 700; font-size: 1.4rem;
        }
        .side-name {
            text-align: center; font-family: Orbitron, sans-serif;
            font-size: 1.28rem; letter-spacing: .06em; color: #fff;
        }
        .side-tag {
            text-align: center; color: #d8b4fe; font-size: .78rem; margin-top: 2px;
        }
        .side-online {
            margin: 8px auto 0; width: fit-content;
            display: flex; align-items: center; gap: 7px;
            padding: 4px 10px; border-radius: 999px;
            background: rgba(16, 185, 129, .12);
            border: 1px solid rgba(52, 211, 153, .35);
            color: #86efac; font-size: .78rem;
        }
        .side-online i {
            width: 8px; height: 8px; border-radius: 50%; background: #34d399;
            box-shadow: 0 0 8px #34d399; animation: pulseDot 1.6s ease-in-out infinite;
        }
        .side-grid {
            display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 12px;
        }
        .tile {
            padding: 10px 10px 11px; border-radius: 16px;
            background: rgba(255,255,255,.03);
            border: 1px solid rgba(240,171,252,.18);
        }
        .tile em {
            display: block; font-style: normal; font-size: .68rem;
            letter-spacing: .12em; color: #c4b5fd; margin-bottom: 4px;
        }
        .tile b { font-size: .86rem; color: #fff; font-weight: 700; }
        .tile.warn { border-color: rgba(251,191,36,.35); }
        .tile.err { border-color: rgba(251,113,133,.4); }
        .side-panel {
            padding: 12px; border-radius: 16px; margin-bottom: 12px;
            background: rgba(8,0,16,.45);
            border: 1px solid rgba(168,85,247,.2);
        }
        .side-panel-h {
            font-family: M PLUS Rounded 1c, sans-serif; font-size: .72rem;
            letter-spacing: .16em; color: #e9d5ff; margin-bottom: 8px;
        }
        .kv {
            display: flex; justify-content: space-between; align-items: center;
            padding: 7px 0; border-bottom: 1px dashed rgba(240,171,252,.12);
            font-size: .84rem;
        }
        .kv:last-child { border-bottom: 0; padding-bottom: 0; }
        .kv span { color: #c4b5fd; }
        .kv b {
            color: #fff; background: rgba(168,85,247,.2);
            border: 1px solid rgba(240,171,252,.25);
            border-radius: 999px; padding: 2px 8px; font-size: .76rem;
        }
        .side-quote {
            margin: 0 0 12px; padding: 10px 12px; border-radius: 14px;
            background: linear-gradient(90deg, rgba(255,46,166,.12), rgba(168,85,247,.08));
            border-left: 3px solid #ff2ea6;
            color: #f5d0fe; font-size: .8rem; line-height: 1.45;
        }

        [data-testid="stSidebar"] .stButton > button {
            background: linear-gradient(180deg, rgba(42,12,48,.9), rgba(12,4,18,.95)) !important;
            color: #f5d0fe !important;
            border: 1px solid rgba(236,72,153,.35) !important;
            border-radius: 14px !important;
            text-align: left !important;
            transition: transform .15s ease, box-shadow .15s ease !important;
        }
        [data-testid="stSidebar"] .stButton > button:hover {
            transform: translateY(-2px) !important; color: #fff !important;
            border-color: #ff2ea6 !important;
            box-shadow: 0 0 16px rgba(236,72,153,.35) !important;
        }
        .stButton > button {
            background: #000 !important; color: #f0abfc !important;
            border: 1px solid rgba(236,72,153,.45) !important; border-radius: 12px !important;
            transition: transform .15s ease, box-shadow .15s ease !important;
        }
        .stButton > button:hover {
            transform: translateY(-2px) !important; color: #fff !important;
            box-shadow: 0 0 14px rgba(236,72,153,.4) !important;
        }
        button[data-testid="baseButton-primary"] {
            min-height: 58px; font-family: M PLUS Rounded 1c, sans-serif !important;
            letter-spacing: .38em !important; font-size: 1.05rem !important;
            border-radius: 999px !important;
            box-shadow: 0 0 24px rgba(236,72,153,.35) !important;
        }

        .aira-foot { text-align: center; color: var(--muted) !important; font-size: .78rem; opacity: .75; margin-top: 18px; }

        .splash {
            position: relative; z-index: 2;
            min-height: 86vh; display: flex; flex-direction: column;
            align-items: center; justify-content: center; text-align: center;
            overflow: hidden;
        }
        .splash-orb {
            position: absolute; border-radius: 50%; filter: blur(8px);
            pointer-events: none; z-index: 0;
        }
        .splash-orb.a {
            width: 280px; height: 280px; top: 8%; left: 8%;
            background: radial-gradient(circle, rgba(168,85,247,.45), transparent 68%);
            animation: orbFloat 7s ease-in-out infinite;
        }
        .splash-orb.b {
            width: 320px; height: 320px; right: 4%; bottom: 10%;
            background: radial-gradient(circle, rgba(255,46,166,.38), transparent 68%);
            animation: orbFloat 8.5s ease-in-out infinite reverse;
        }
        .splash-scanlines {
            position: absolute; inset: 0; pointer-events: none; z-index: 1;
            background: repeating-linear-gradient(
                to bottom,
                rgba(255,255,255,.035),
                rgba(255,255,255,.035) 1px,
                transparent 1px,
                transparent 4px
            );
        }
        .splash-stars {
            position: absolute; inset: 0; z-index: 0; pointer-events: none;
            background-image:
                radial-gradient(1.5px 1.5px at 12% 22%, #f0abfc 50%, transparent 51%),
                radial-gradient(1.5px 1.5px at 78% 18%, #ff2ea6 50%, transparent 51%),
                radial-gradient(1.2px 1.2px at 30% 70%, #c084fc 50%, transparent 51%),
                radial-gradient(1.4px 1.4px at 88% 64%, #fff 50%, transparent 51%),
                radial-gradient(1.2px 1.2px at 55% 40%, #f0abfc 50%, transparent 51%),
                radial-gradient(1.3px 1.3px at 18% 86%, #ff2ea6 50%, transparent 51%);
            animation: twinkle 3.4s ease-in-out infinite;
        }
        .splash-core { position: relative; z-index: 3; width: min(560px, 92vw); }
        .splash-halo {
            width: 230px; height: 230px; margin: 0 auto 8px; position: relative;
            animation: haloIn 1.1s cubic-bezier(.16,1,.3,1) both;
        }
        .splash-halo::before {
            content: ""; position: absolute; inset: 0; border-radius: 50%;
            background: conic-gradient(from var(--spin), #ff2ea6, #a855f7, transparent 40%, #ff2ea6);
            -webkit-mask: radial-gradient(farthest-side, transparent calc(100% - 3px), #000 0);
            mask: radial-gradient(farthest-side, transparent calc(100% - 3px), #000 0);
            animation: spinBorder 3.5s linear infinite;
        }
        .splash-halo::after {
            content: ""; position: absolute; inset: 16px; border-radius: 50%;
            border: 1px dashed rgba(240,171,252,.35);
            animation: spinBorder 18s linear infinite reverse;
        }
        .splash-logo {
            position: absolute; inset: 0; display: grid; place-items: center;
            font-family: M PLUS Rounded 1c, sans-serif; font-weight: 700; line-height: .85;
            font-size: 3.4rem; color: #ffe6fb; letter-spacing: -.05em;
            text-shadow: 0 0 18px rgba(255,46,166,.7);
            animation: logoPop 1.15s cubic-bezier(.16,1,.3,1) both;
        }
        .splash-logo span { color: #ff2ea6; font-size: .42em; }
        .splash-logo-img {
            position: absolute; inset: 28px; border-radius: 50%;
            background: #08030e center/contain no-repeat;
            box-shadow: 0 0 28px rgba(255,46,166,.35);
            animation: logoPop 1.15s cubic-bezier(.16,1,.3,1) both;
            z-index: 2;
        }
        .splash-brand {
            margin-top: 8px; letter-spacing: .62em; font-size: .78rem; color: #e9d5ff;
            animation: rise 0.8s 0.55s both;
        }
        .splash-hello {
            margin: 16px auto 0; max-width: 440px; color: #f3e8ff;
            font-size: 1.12rem; line-height: 1.6; animation: rise 0.8s 0.95s both;
        }
        .boot {
            width: min(420px, 88vw); margin: 22px auto 0; text-align: left;
            font-size: .78rem; color: #d8b4fe; line-height: 1.7;
        }
        .boot div {
            opacity: 0; transform: translateY(8px);
            animation: bootLine .45s ease forwards;
        }
        .boot div:nth-child(1) { animation-delay: .35s; }
        .boot div:nth-child(2) { animation-delay: .7s; }
        .boot div:nth-child(3) { animation-delay: 1.05s; }
        .boot div:nth-child(4) { animation-delay: 1.4s; }
        .boot b { color: #86efac; }
        .splash-hint {
            margin-top: 8px; color: #c4b5fd; font-size: .78rem;
            letter-spacing: .18em; animation: rise .8s 1.7s both;
        }
        .splash-miss {
            margin-top: 8px; color: #f9a8d4; font-size: .72rem; opacity: .8;
        }

        @keyframes spinBorder { to { --spin: 360deg; } }
        @keyframes blink { 50% { opacity: 0; } }
        @keyframes pulseDot { 50% { opacity: .35; transform: scale(.75); } }
        @keyframes dots {
            0%   { content: ""; }
            25%  { content: "."; }
            50%  { content: ".."; }
            75%  { content: "..."; }
        }
        @keyframes barRun {
            0%   { transform: translateX(-120%); }
            100% { transform: translateX(280%); }
        }
        @keyframes orbFloat {
            0%,100% { transform: translate(0,0); }
            50% { transform: translate(18px,-16px); }
        }
        @keyframes twinkle { 50% { opacity: .45; } }
        @keyframes haloIn {
            from { opacity: 0; transform: scale(.55); }
            to { opacity: 1; transform: none; }
        }
        @keyframes logoPop {
            from { opacity: 0; transform: scale(.4); filter: blur(8px); }
            to { opacity: 1; transform: none; filter: none; }
        }
        @keyframes rise {
            from { opacity: 0; transform: translateY(14px); }
            to { opacity: 1; transform: none; }
        }
        @keyframes bootLine { to { opacity: 1; transform: none; } }

        @media (prefers-reduced-motion: reduce) {
            .pcb-glow, [data-testid="stChatInput"]::before,
            .splash-halo::before, .side-ring, .think-bar i, .think-dots::after {
                animation: none !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# PCB
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


def _d(x: float, y: float, spec: str) -> str:
    pts = _pcb_pts(x, y, spec)
    return "M " + " L ".join(f"{px:.0f} {py:.0f}" for px, py in pts)


_PCB_SPECS = [
    (-20, 28, "H 680"), (-20, 42, "H 540"), (-20, 56, "H 760"),
    (-20, 70, "H 420 SE 26 H 160"), (-20, 84, "H 820"), (-20, 98, "H 380"),
    (-20, 112, "H 600 V 32 H 140"), (-20, 126, "H 490"), (-20, 140, "H 700"),
    (-20, 154, "H 330 SE 34 H 200"), (-20, 168, "H 640"), (-20, 182, "H 450"),
    (-20, 196, "H 790"), (-20, 210, "H 290 V 46 H 240"), (-20, 224, "H 570"),
    (-20, 238, "H 440 SE 22 H 80"), (-20, 252, "H 680"), (-20, 266, "H 360"),
    (-20, 280, "H 620 V -36 H 110"), (-20, 294, "H 500"),
    (420, 70, "V 86 SE 36 H 70"), (600, 144, "V 66 SW 28 V 36"),
    (700, 196, "SE 46 H 130 V 32"), (290, 256, "V 76 SE 42 H 90"),
    (110, 336, "H 250 SE 54 H 170 NE 36 H 200"),
    (70, 366, "H 190 SE 74 V 46 H 150"),
    (190, 406, "H 320 NE 32 H 80 SE 46 H 120"),
    (30, 446, "H 170 V 66 H 220 SE 28 H 70"),
    (510, 356, "H 190 V 84 H 150 NE 40 H 60"),
    (690, 326, "SE 64 H 170 V 36 H 80"),
    (850, 296, "H 150 SE 32 H 190"),
    (930, 376, "H 210 V 56 SE 36 H 70"),
    (390, 496, "H 270 SE 50 H 180 V 28"),
    (150, 536, "H 200 NE 36 H 140 SE 64 H 90"),
    (610, 476, "V 76 H 130 SE 32 H 190"),
    (1610, 856, "H -210 NW 44 H -130 SW 32 H -170"),
    (1610, 834, "H -150 NW 64 H -80 SW 26 H -120"),
    (1610, 812, "H -290 NE 36 H -110 NW 46 H -70"),
    (1610, 790, "H -100 SW 56 H -190 NW 30 H -80"),
    (1610, 768, "H -240 NW 28 H -150"),
    (1610, 746, "H -70 NW 84 H -130 SE 36 H -90"),
    (1610, 724, "H -180 SW 40 H -60 NW 54 H -140"),
    (1610, 702, "H -320"),
    (1570, 680, "H -110 NW 50 H -190 V -36 H -70"),
    (1570, 658, "H -250 SE 28 H -80"),
    (1530, 636, "H -80 SW 64 H -170 NE 32 H -60"),
    (1490, 596, "H -150 NW 36 V -46 H -110"),
    (1470, 556, "H -210 SE 44 H -70 NW 26"),
    (1450, 516, "H -90 NE 54 H -160 SW 36 H -50"),
    (1510, 476, "H -230 V 32 H -80"),
    (1550, 436, "H -170 SE 46 H -130"),
    (1590, 396, "H -290 NW 26 H -70"),
    (1590, 356, "H -130 SW 54 H -190"),
    (1570, 316, "H -80 NE 40 H -220 SE 32"),
    (1170, 776, "NW 64 H -150 NE 36 H -80"),
    (1090, 696, "H -120 SW 46 H -70 V 36"),
    (1010, 616, "NE 32 H -140 SE 54 H -60"),
    (970, 816, "H -190 NW 44 V -26 H -80"),
    (870, 756, "SW 36 H -110 NE 64 H -50"),
    (810, 676, "H -80 V 76 H -130 SE 26"),
    (-10, 776, "H 230 SE 36 H 170 V 28 H 80"),
    (-10, 806, "H 310 NE 26 H 130"),
    (-10, 836, "H 170 SE 46 H 250 NW 18 H 70"),
    (-10, 866, "H 400"),
    (70, 716, "H 150 V 46 SE 32 H 110"),
    (190, 676, "SE 54 H 140 V 36 H 60"),
    (350, 736, "H 190 NE 36 H 80 SE 26"),
    (890, 36, "H 210 SE 32 H 150"),
    (970, 66, "H 170 V 40 H 130"),
    (1030, 106, "H 250 NE 22 H 70"),
    (1110, 146, "H 130 SE 46 H 180"),
    (1190, 196, "H 170 V -32 H 110"),
    (1270, 246, "SE 36 H 150 V 26"),
    (890, 176, "H 150 V 64 SE 26 H 70"),
    (750, 86, "H 120 SE 42 H 60"),
]

_PCB_GLOW = [
    ("c", -20, 56, "H 760"),
    ("p", 1610, 856, "H -210 NW 44 H -130 SW 32 H -170"),
    ("c", 110, 336, "H 250 SE 54 H 170 NE 36 H 200"),
    ("p", 390, 496, "H 270 SE 50 H 180 V 28"),
]


def _build_pcb() -> str:
    parts = ['<svg viewBox="0 0 1600 900" preserveAspectRatio="xMidYMid slice">']
    vias: List[Tuple[int, int]] = []
    for i, (x, y, spec) in enumerate(_PCB_SPECS):
        cls = "pcb-tr alt" if i % 3 == 0 else "pcb-tr"
        parts.append(f'<path class="{cls}" d="{_d(x, y, spec)}"/>')
        pts = _pcb_pts(x, y, spec)
        vias.append((int(pts[-1][0]), int(pts[-1][1])))
    for kind, x, y, spec in _PCB_GLOW:
        parts.append(f'<path class="pcb-glow {kind}" d="{_d(x, y, spec)}"/>')
    for vx, vy in vias[::3]:
        if -20 < vx < 1620 and -20 < vy < 920:
            parts.append(f'<circle class="pcb-pad" cx="{vx}" cy="{vy}" r="4.6"/>')
            parts.append(f'<circle class="pcb-hole" cx="{vx}" cy="{vy}" r="1.5"/>')
    parts.append("</svg>")
    return "".join(parts)


_PCB_SVG = _build_pcb()


def render_pcb_layer() -> None:
    st.markdown(f'<div class="pcb-layer" aria-hidden="true">{_PCB_SVG}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Konstanta
# ---------------------------------------------------------------------------

APP_TITLE = "Aira - Asisten AI-Chatbot By Ampera"
APP_TAGLINE = "Asisten AI-Chatbot By Ampera · Chatbot AI pintar siap bantu di perangkatmu"
WELCOME_TEXT = (
    "Hai, aku **Aira**. Asisten AI-Chatbot By Ampera · Chatbot AI pintar siap bantu—mulai dari "
    "error Android, APK bandel, RAM mepet, sampai pertanyaan sehari-hari.\n\n"
    "Tulis aja keluhannya, atau pilih salah satu contoh di sidebar. Percakapan "
    "kita jalan di perangkatmu, bukan di cloud."
)
IDENTITY_REPLY = (
    "Aku **Aira**. Asisten AI-Chatbot Buatan Ampera.ai, santai, dan siap bantu. "
    "Aku dirancang untuk berjalan privat di perangkatmu.\n\n"
    "Bisa aku bantu urusan teknis (terutama Android), penjelasan sistem, "
    "atau pertanyaan umum. Panggil aja Aira kapan pun kamu butuhya...."
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
    "gimana kabarnya", "how are you", "halo halo", "hai hai",
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
_IMG_EXT = (".jpg", ".jpeg", ".png", ".webp")

THINK_STAGES_RAG = [
    ("Mencerna pertanyaan", "membaca input"),
    ("Mengurai konteks", "memetakan makna"),
    ("Menelusuri memori", "scan knowledge"),
    ("Berpikir", "menyusun nalar"),
    ("Menyusun jawaban", "menulis balasan"),
]
THINK_STAGES_FAST = [
    ("Mencerna sapaan", "mengenali pola"),
    ("Berpikir", "memilih nada"),
    ("Menyusun jawaban", "menulis balasan"),
]


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
        return "Kabar ya..? Alahmdulillah... Aira sehat, Aira siap sedia bantu kamu. Ada kendala atau pertanyaan?"
    return f"Halo, selamat {waktu}! Aku Aira, asisten AI-Chatbot Dari Ampera. Mau tanya sesuatu atau mau ngobrol santai"


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
# Gambar
# ---------------------------------------------------------------------------

def _asset_roots() -> List[str]:
    return [_BASE_DIR, os.path.join(_BASE_DIR, "assets"), os.getcwd()]


def _read_image(path: str) -> Dict[str, str]:
    ext = os.path.splitext(path)[1].lower()
    mime = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(ext, "image/jpeg")
    with open(path, "rb") as fh:
        raw = fh.read()
    return {"mime": mime, "b64": base64.b64encode(raw).decode("ascii"), "path": path}


def _scan_image(exact_names: Tuple[str, ...], *needles: str) -> str:
    needles_l = [n.lower() for n in needles]
    for root in _asset_roots():
        if not root or not os.path.isdir(root):
            continue
        for name in exact_names:
            path = os.path.join(root, name)
            if os.path.isfile(path):
                return os.path.abspath(path)
        try:
            for fn in os.listdir(root):
                low = fn.lower()
                if not low.endswith(_IMG_EXT):
                    continue
                if all(n in low for n in needles_l):
                    return os.path.abspath(os.path.join(root, fn))
        except OSError:
            pass
    return ""


def find_profile_file() -> str:
    names = ("aira.jpg", "aira.jpeg", "aira.png", "aira.webp", "Aira.jpg", "Aira.JPG")
    return _scan_image(names, "aira")


def find_logo_file() -> str:
    names = (
        "logo ampera.jpg",
        "logo ampera.jpeg",
        "logo ampera.png",
        "logo ampera.webp",
        "logo_ampera.jpg",
        "logo_ampera.png",
        "logo-ampera.jpg",
        "Logo Ampera.jpg",
        "logoampera.jpg",
        "ampera.jpg",
        "ampera.png",
    )
    path = _scan_image(names, "logo", "ampera")
    return path or _scan_image(names, "ampera")


@st.cache_data(show_spinner=False)
def get_profile_image() -> Dict[str, str]:
    path = find_profile_file()
    return _read_image(path) if path else {"mime": "", "b64": "", "path": ""}


@st.cache_data(show_spinner=False)
def get_logo_image() -> Dict[str, str]:
    path = find_logo_file()
    return _read_image(path) if path else {"mime": "", "b64": "", "path": ""}


def inject_media_css(photo: Dict[str, str], logo: Dict[str, str]) -> None:
    rules = []
    if photo.get("b64"):
        url = f'data:{photo["mime"]};base64,{photo["b64"]}'
        rules.append(f".wa-avatar-aira,.side-ava{{background-image:url('{url}')!important;}}")
    if logo.get("b64"):
        url = f'data:{logo["mime"]};base64,{logo["b64"]}'
        rules.append(f".splash-logo-img,.app-logo.has-img{{background-image:url('{url}')!important;}}")
    if rules:
        st.markdown(f"<style>{''.join(rules)}</style>", unsafe_allow_html=True)


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
            f'<div class="wa-row right"><div class="wa-bubble wa-user">{inner_html}</div>'
            f'<div class="wa-avatar wa-avatar-user">😎</div></div>'
        )
    return (
        f'<div class="wa-row left">{aira_avatar_html(photo)}'
        f'<div class="wa-bubble wa-aira">{inner_html}</div></div>'
    )


def show_wa(role: str, text: str, photo: Dict[str, str]) -> None:
    st.markdown(build_wa_row(role, md_lite(text), photo), unsafe_allow_html=True)


def render_think_html(stage: str, done: List[str], detail: str = "") -> str:
    logs = "".join(f'<div class="done">✓ {html.escape(item)}</div>' for item in done)
    logs += f'<div class="wait">› {html.escape(stage)}<span class="think-dots"></span></div>'
    return (
        '<div class="think">'
        '<div class="think-head"><span class="think-orb"></span>AIRA · PROSES</div>'
        f'<div class="think-now">sedang <b>{html.escape(stage.lower())}</b></div>'
        f'<div class="think-log">{logs}</div>'
        '<div class="think-bar"><i></i></div>'
        "</div>"
    )


def show_think(
    box: Any,
    photo: Dict[str, str],
    stage: str,
    done: List[str],
    hold: float = 0.32,
) -> None:
    box.markdown(
        build_wa_row("assistant", render_think_html(stage, done), photo),
        unsafe_allow_html=True,
    )
    if hold > 0:
        time.sleep(hold)


def stream_reply(box: Any, photo: Dict[str, str], answer: str) -> None:
    """Tampilkan jawaban perlahan, per beberapa kata — tidak nge-lag."""
    text = answer or ""
    tokens = re.findall(r"\S+\s*", text)
    if len(tokens) <= 4:
        box.markdown(build_wa_row("assistant", md_lite(text), photo), unsafe_allow_html=True)
        return

    step = 2 if len(tokens) < 70 else 4
    acc = ""
    for i, tok in enumerate(tokens, 1):
        acc += tok
        if i % step == 0 or i == len(tokens):
            caret = "" if i == len(tokens) else '<span class="type-caret"></span>'
            box.markdown(
                build_wa_row("assistant", md_lite(acc) + caret, photo),
                unsafe_allow_html=True,
            )
            if i != len(tokens):
                time.sleep(0.028 if step == 2 else 0.018)

    box.markdown(build_wa_row("assistant", md_lite(text), photo), unsafe_allow_html=True)


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

def run_rag_pipeline(user_input: str, last_bot_response: str, llm: Any) -> Tuple[str, str, str]:
    resolved, context = user_input, ""
    try:
        resolved = resolve_query(user_input, last_bot_response=last_bot_response) or user_input
    except Exception:
        resolved = user_input
    try:
        context = search_knowledge(resolved) or ""
    except Exception:
        context = ""
    reply = generate_aira_response(
        llm=llm,
        user_input=user_input,
        context=context,
        history=history_for_llm(st.session_state.messages),
    )
    return (reply or "").strip(), resolved, context


def handle_user_message(user_input: str, llm: Any, photo: Dict[str, str]) -> None:
    text = (user_input or "").strip()
    if not text:
        return

    last_bot = get_last_bot_response(st.session_state.messages)
    st.session_state.messages.append({"role": "user", "content": text})
    show_wa("user", text, photo)

    box = st.empty()
    bypass_reply = detect_intent_bypass(text)
    stages = THINK_STAGES_FAST if bypass_reply else THINK_STAGES_RAG
    done: List[str] = []

    # tahap 1–2 dulu, biar kelihatan "jeda berpikir"
    show_think(box, photo, stages[0][0], done, 0.85)
    done.append(stages[0][0])
    show_think(box, photo, stages[1][0], done, 0.85)
    done.append(stages[1][0])

    if bypass_reply:
        answer = bypass_reply
        if len(stages) > 2:
            show_think(box, photo, stages[2][0], done, 0.28)
        st.session_state.last_debug = {
            "bypass": True, "resolved_query": text, "context": "(dilewati — intent sapaan/identitas)"
        }
    else:
        show_think(box, photo, stages[2][0], done, 0.85)
        done.append(stages[2][0])
        show_think(box, photo, stages[3][0], done, 0.85)
        try:
            answer, resolved, context = run_rag_pipeline(text, last_bot, llm)
        except Exception as exc:
            traceback.print_exc()
            answer = f"Ada kendala teknis saat memproses jawaban: `{exc.__class__.__name__}`"
            resolved, context = text, ""
        if not answer:
            answer = "Hmm, Aira belum tau jawabannya. Bisa coba tanyakan dengan kalimat lain?"
        done.append(stages[3][0])
        show_think(box, photo, stages[4][0], done, 0.85)
        st.session_state.last_debug = {"bypass": False, "resolved_query": resolved, "context": context}

    stream_reply(box, photo, answer)
    st.session_state.messages.append({"role": "assistant", "content": answer})


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

def render_sidebar(model_info: Dict[str, Any], photo: Dict[str, str]) -> None:
    kb = get_kb_status()
    mode = model_info.get("mode", "error")

    if mode == "gguf":
        model_tile, model_label = "ok", "GGUF Siap"
    elif mode == "mock":
        model_tile, model_label = "warn", "KB Active"
    else:
        model_tile, model_label = "err", "Offline"

    mem_ok = bool(kb["exists"] and kb["count"] > 0)
    mem_tile = "ok" if mem_ok else "warn"
    mem_label = f"{kb.get('count', 0)} Entri" if mem_ok else "Kosong"
    ava = '<div class="side-ava"></div>' if photo.get("b64") else '<div class="ph">A</div>'

    with st.sidebar:
        st.markdown(
            f"""
            <div class="side-hero">
              <div class="side-ava-wrap">
                {ava}
                <div class="side-ring"></div>
              </div>
              <div class="side-name">Aira</div>
              <div class="side-tag">Asisten AI · Ampera Official</div>
              <div class="side-online"><i></i> online · A.ai</div>
            </div>
            <div class="side-grid">
              <div class="tile {model_tile}"><em>MODEL</em><b>{html.escape(model_label)}</b></div>
              <div class="tile {mem_tile}"><em>MEMORI</em><b>{html.escape(mem_label)}</b></div>
            </div>
            <div class="side-quote">Siap bantu masalah Android, APK, RAM, atau ngobrol santai — privat di perangkatmu.</div>
            <div class="side-panel">
              <div class="side-panel-h">SISTEM</div>
              <div class="kv"><span>Mode</span><b>{html.escape(str(mode))}</b></div>
              <div class="kv"><span>Knowledge</span><b>{kb.get('count', 0)}</b></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if not photo.get("path"):
            st.caption("Taruh `aira.jpg` di folder yang sama dengan `app.py`.")

        if st.button("✦  Obrolan Baru", use_container_width=True, key="btn_reset"):
            reset_conversation()
            st.rerun()

        st.markdown(
            '<div class="side-panel-h" style="margin:14px 0 8px;">PROMPT CEPAT</div>',
            unsafe_allow_html=True,
        )
        for sample in EXAMPLE_PROMPTS:
            if st.button(sample, use_container_width=True, key=f"ex_{sample}"):
                queue_example(sample)
                st.rerun()


def render_header(logo: Dict[str, str]) -> None:
    mark = (
        '<div class="app-logo has-img" title="Ampera Official"></div>'
        if logo.get("b64")
        else '<div class="app-logo">A<span>.ai</span></div>'
    )
    st.markdown(
        f"""
        <div class="app-head">
          {mark}
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
    st.markdown('<p class="aira-foot">Aira · Asisten AI-Chatbot By · Ampera Official</p>', unsafe_allow_html=True)


def render_splash(logo: Dict[str, str]) -> None:
    if logo.get("b64"):
        mark = '<div class="splash-logo-img" title="Ampera Official"></div>'
        miss = ""
    else:
        mark = '<div class="splash-logo">A<span>.ai</span></div>'
        miss = '<div class="splash-miss">Logo belum ketemu. Taruh file <b>logo ampera.jpg</b> di folder app.</div>'

    st.markdown(
        f"""
        <style>
        [data-testid="stSidebar"],
        [data-testid="stSidebarCollapsedControl"],
        [data-testid="stHeader"] {{ display: none !important; }}
        [data-testid="stMainBlockContainer"] {{ max-width: 720px; padding-top: 0 !important; }}
        </style>
        <div class="splash">
          <div class="splash-orb a"></div>
          <div class="splash-orb b"></div>
          <div class="splash-stars"></div>
          <div class="splash-scanlines"></div>
          <div class="splash-core">
            <div class="splash-halo">{mark}</div>
            <div class="splash-brand">AMPERA OFFICIAL</div>
            <div class="boot">
              <div>&gt; boot ampera.Engine .............. <b>OK</b></div>
              <div>&gt; link neural bus ............... <b>OK</b></div>
              <div>&gt; handshake aira.persona ........ <b>GRANTED</b></div>
              <div>&gt; welcome sequence .............. <b>READY</b></div>
            </div>
            <p class="splash-hello">
              Selamat datang.... di salah satu app buatan<br><strong>Ampera Official</strong>
            </p>
            <div class="splash-hint">KETUK UNTUK MASUK</div>
            {miss}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    _l, mid, _r = st.columns([1, 1.2, 1])
    with mid:
        if st.button("MASUK", type="primary", use_container_width=True, key="btn_masuk"):
            st.session_state.entered_app = True
            st.rerun()


def main() -> None:
    set_ui_style()
    render_pcb_layer()
    init_session_state()

    logo = get_logo_image()
    inject_media_css({"mime": "", "b64": "", "path": ""}, logo)

    if not st.session_state.entered_app:
        render_splash(logo)
        return

    ensure_runtime_ready()
    photo = get_profile_image()
    inject_media_css(photo, logo)
    model_info = get_cached_llm()

    render_sidebar(model_info, photo)
    render_header(logo)
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
