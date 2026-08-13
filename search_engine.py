from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional
from rank_bm25 import BM25Okapi
# Tambahkan definisi variabel ini di search_engine.py
DEFAULT_KB_PATH = "path/to/your/knowledge_base.json"  # atau lokasi file KB kamu

_knowledge_data: List[Dict[str, Any]] = []
_bm25_index: Optional[BM25Okapi] = None

def load_knowledge_base(filepath: str = "knowledge.json") -> List[Dict[str, Any]]:
    """Memuat file knowledge.json dan membuat indeks pencarian BM25."""
    global _knowledge_data, _bm25_index
    if not os.path.exists(filepath):
        return []
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            _knowledge_data = json.load(f)
            
        corpus = [
            f"{item.get('title', '')} {item.get('content', '')} {' '.join(item.get('keywords', []))}".lower().split()
            for item in _knowledge_data
        ]
        if corpus:
            _bm25_index = BM25Okapi(corpus)
    except Exception:
        _knowledge_data = []
        _bm25_index = None
        
    return _knowledge_data

# Alias nama fungsi agar sesuai dengan yang dicari app.py
load_knowledge = load_knowledge_base

def search_knowledge(query: str, top_k: int = 3, **kwargs) -> str:
    """Mencari informasi paling relevan dari knowledge base."""
    global _knowledge_data, _bm25_index
    if not _knowledge_data or _bm25_index is None:
        load_knowledge_base()
        
    if not _knowledge_data or _bm25_index is None:
        return ""

    tokenized_query = query.lower().split()
    scores = _bm25_index.get_scores(tokenized_query)
    
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
    
    results = []
    for idx in top_indices:
        if scores[idx] > 0:
            item = _knowledge_data[idx]
            title = item.get("title", "Informasi")
            content = item.get("content", "")
            results.append(f"[{title}]: {content}")
            
    return "\n".join(results)

def search_knowledge_detailed(query: str, **kwargs):
    """Fungsi pembantu agar kompatibel dengan pemanggilan app.py."""
    return search_knowledge(query)

def resolve_query(query: str, *args, **kwargs) -> str:
    """Fungsi pemroses kueri."""
    return query
