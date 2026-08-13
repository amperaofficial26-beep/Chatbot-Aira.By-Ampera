```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
search_engine.py
================
Mesin pencari memori (Retriever) untuk chatbot Aira.

Alur singkat:
    user_input  ->  resolve_query()  ->  search_knowledge()  ->  context string
                                         (BM25 + bonus keyword/title)

Dependensi:
    pip install rank_bm25
"""

from __future__ import annotations

import json
import os
import re
import sys
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


# ---------------------------------------------------------------------------
# Konstanta path & konfigurasi default
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_KB_PATH = os.path.join(BASE_DIR, "knowledge.json")

# Ambang default sesuai spesifikasi.
DEFAULT_TOP_K = 2
DEFAULT_MIN_SCORE = 1.5

# Query dianggap pendek jika jumlah katanya di bawah nilai ini.
SHORT_QUERY_MAX_WORDS = 4

# Kata rujukan: sinyal bahwa user sedang menunjuk konteks sebelumnya.
# "nya" sebagai kata mandiri maupun akhiran (masalahnya, caranya) ikut dideteksi.
REFERENCE_WORDS = {
    "nya",
    "itu",
    "ini",
    "tersebut",
    "benerin",
    "beneran",
    "perbaiki",
    "perbaikin",
    "perbaikan",
    "gini",
    "gitu",
    "begini",
    "begitu",
    "tadi",
    "barusan",
    "lanjut",
    "lanjutin",
    "terus",
    "maksudnya",
    "yg",
    "yang",
    "doang",
    "dong",
    "sih",
    "deh",
}

# Stopword ringkas (ID + EN) untuk tokenisasi BM25 dan ekstraksi kata kunci.
# Sengaja tidak memuat istilah domain (android, ram, apk, error, game, os).
STOPWORDS = {
    "ada", "adalah", "agar", "akan", "aku", "anda", "apa", "apakah", "atau",
    "bagai", "bagaimana", "bagi", "bahwa", "baik", "banyak", "baru", "beberapa",
    "belum", "benar", "bisa", "boleh", "buat", "bukan", "cara", "cuma", "dahulu",
    "dalam", "dan", "dapat", "dari", "demikian", "dengan", "di", "dia", "dong",
    "dua", "duluan", "gak", "ga", "gk", "hai", "halo", "hanya", "harus", "hingga",
    "ia", "ingin", "ini", "itu", "iya", "jadi", "jangan", "jika", "juga", "kalau",
    "kali", "kami", "kamu", "karena", "ke", "kita", "kok", "kurang", "lagi",
    "lalu", "lama", "lebih", "lu", "maka", "malah", "masih", "mau", "memang",
    "mengapa", "mereka", "merupakan", "mesti", "mohon", "mungkin", "nah",
    "namun", "nih", "nya", "oleh", "pada", "paling", "para", "per", "pernah",
    "pun", "saat", "saja", "salah", "sama", "sampai", "sangat", "saya", "sebab",
    "sebagai", "sebelum", "sebuah", "secara", "sedang", "sekarang", "sekitar",
    "selalu", "selama", "seluruh", "semua", "sendiri", "seperti", "sering",
    "serta", "sesudah", "setelah", "setiap", "sih", "sudah", "supaya", "tadi",
    "tak", "tanpa", "tapi", "telah", "tentang", "tentu", "terhadap", "tersebut",
    "terus", "tetapi", "tidak", "toh", "tolong", "untuk", "wah", "wahai",
    "waktunya", "ya", "yaitu", "yakni", "yang", "yg",
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in", "is",
    "it", "of", "on", "or", "that", "the", "this", "to", "was", "were", "with",
    "please", "how", "what", "when", "where", "who", "why",
}

# Pesan standar jika tidak ada memori yang lolos threshold.
NO_MEMORY_MSG = "Tidak ada memori spesifik"


# ---------------------------------------------------------------------------
# Utilitas teks
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)
_WORD_RE = re.compile(r"\S+")


def tokenize(text: str, remove_stopwords: bool = True) -> List[str]:
    """Pecah teks menjadi token alfanumerik huruf kecil.

    Angka versi (android12, ram4) tetap dipertahankan. Tanda baca dibuang.
    """
    if not text:
        return []

    tokens = [m.group(0).lower() for m in _TOKEN_RE.finditer(text)]
    if remove_stopwords:
        tokens = [t for t in tokens if t not in STOPWORDS and len(t) > 1]
    else:
        tokens = [t for t in tokens if t]
    return tokens


def _word_count(text: str) -> int:
    """Hitung jumlah kata kasar berdasarkan spasi (bukan token BM25)."""
    if not text or not text.strip():
        return 0
    return len(_WORD_RE.findall(text.strip()))


def _contains_reference(text: str) -> bool:
    """True jika kueri memuat kata rujukan atau akhiran -nya (selain kata pendek)."""
    raw_tokens = [m.group(0).lower() for m in _TOKEN_RE.finditer(text or "")]
    for tok in raw_tokens:
        if tok in REFERENCE_WORDS:
            return True
        # Akhiran posesif/rujukan: "masalahnya", "installernya", "caranya".
        if len(tok) > 3 and tok.endswith("nya"):
            return True
    return False


def _unique_keep_order(items: Iterable[str]) -> List[str]:
    """Deduplikasi token sambil menjaga urutan kemunculan pertama."""
    seen = set()
    out: List[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


# ---------------------------------------------------------------------------
# Loading knowledge base
# ---------------------------------------------------------------------------

def load_knowledge(path: str = DEFAULT_KB_PATH) -> List[Dict[str, Any]]:
    """Muat `knowledge.json` dan validasi struktur minimum setiap entri.

    Setiap objek diharapkan punya: id, category, title, keywords, content.
    Entri yang rusak dilewati, bukan membuat seluruh retriever gagal.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"knowledge.json tidak ditemukan di: {path}"
        )

    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, list):
        raise ValueError("knowledge.json harus berupa array of objects.")

    cleaned: List[Dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        if not item.get("content"):
            continue
        cleaned.append(
            {
                "id": str(item.get("id", "")),
                "category": str(item.get("category", "")),
                "title": str(item.get("title", "")),
                "keywords": [
                    str(k) for k in item.get("keywords", []) if str(k).strip()
                ],
                "content": str(item.get("content", "")),
            }
        )
    return cleaned


def _compose_document(item: Dict[str, Any]) -> str:
    """Gabungkan title, keywords, dan content jadi satu dokumen pencarian.

    Title dan keywords diulang agar BM25 memberi bobot lebih pada metadata
    (trik hybrid sederhana tanpa dependensi extra).
    """
    title = item.get("title", "")
    keywords = " ".join(item.get("keywords", []))
    content = item.get("content", "")
    # title x3 + keywords x2 + content x1
    return f"{title} {title} {title} {keywords} {keywords} {content}"


# ---------------------------------------------------------------------------
# Engine BM25 (diinisialisasi sekali, lalu di-cache)
# ---------------------------------------------------------------------------

class AiraBM25Engine:
    """Pembungkus BM25Okapi + indeks bonus keyword/title."""

    def __init__(self, knowledge: Sequence[Dict[str, Any]]):
        # Impor di dalam kelas agar pesan error lebih jelas jika lib belum ada.
        try:
            from rank_bm25 import BM25Okapi
        except ImportError as exc:
            raise ImportError(
                "Library rank_bm25 belum terpasang. Jalankan: pip install rank_bm25"
            ) from exc

        self.knowledge: List[Dict[str, Any]] = list(knowledge)
        self.documents: List[str] = [_compose_document(it) for it in self.knowledge]
        self.tokenized_corpus: List[List[str]] = [
            tokenize(doc, remove_stopwords=True) for doc in self.documents
        ]
        self.bm25 = BM25Okapi(self.tokenized_corpus)

        # Kosakata knowledge base untuk query expansion yang lebih terarah.
        self.vocab = set()
        self.keyword_vocab = set()
        self.title_tokens: List[set] = []
        self.keyword_tokens: List[set] = []

        for item in self.knowledge:
            t_tok = set(tokenize(item["title"], remove_stopwords=True))
            k_tok = set()
            for kw in item["keywords"]:
                k_tok.update(tokenize(kw, remove_stopwords=True))
            c_tok = set(tokenize(item["content"], remove_stopwords=True))

            self.title_tokens.append(t_tok)
            self.keyword_tokens.append(k_tok)
            self.vocab.update(t_tok | k_tok | c_tok)
            self.keyword_vocab.update(k_tok)

    def hybrid_scores(self, query_tokens: Sequence[str]) -> List[float]:
        """Skor hybrid = BM25 + bonus jika token mengenai title/keywords."""
        if not query_tokens:
            return [0.0] * len(self.knowledge)

        bm25_scores = self.bm25.get_scores(list(query_tokens))
        hybrid: List[float] = []
        q_set = set(query_tokens)

        for idx, base in enumerate(bm25_scores):
            bonus = 0.0
            title_hits = q_set & self.title_tokens[idx]
            keyword_hits = q_set & self.keyword_tokens[idx]
            # Bonus kecil agar tidak menenggelamkan sinyal BM25,
            # tapi cukup untuk menaikkan entri yang benar-benar on-topic.
            bonus += 1.25 * len(title_hits)
            bonus += 0.85 * len(keyword_hits)
            hybrid.append(float(base) + bonus)
        return hybrid


_ENGINE: Optional[AiraBM25Engine] = None
_ENGINE_PATH: Optional[str] = None


def get_engine(path: str = DEFAULT_KB_PATH, reload: bool = False) -> AiraBM25Engine:
    """Ambil singleton engine agar file JSON dan indeks BM25 tidak dibangun ulang."""
    global _ENGINE, _ENGINE_PATH
    if _ENGINE is None or reload or _ENGINE_PATH != os.path.abspath(path):
        knowledge = load_knowledge(path)
        if not knowledge:
            raise ValueError("knowledge.json kosong atau tidak berisi entri valid.")
        _ENGINE = AiraBM25Engine(knowledge)
        _ENGINE_PATH = os.path.abspath(path)
    return _ENGINE


# ---------------------------------------------------------------------------
# Query expansion & context stacking
# ---------------------------------------------------------------------------

def _extract_important_keywords(
    text: str,
    engine: Optional[AiraBM25Engine] = None,
    max_terms: int = 10,
) -> List[str]:
    """Ambil kata kunci penting dari respons bot sebelumnya.

    Prioritas:
      1. Token yang muncul di field keywords knowledge base
      2. Token yang ada di kosakata knowledge base
      3. Token panjang non-stopword lainnya
    """
    tokens = tokenize(text, remove_stopwords=True)
    if not tokens:
        return []

    scored: List[Tuple[int, int, str]] = []
    seen = set()
    for pos, tok in enumerate(tokens):
        if tok in seen or len(tok) < 3:
            continue
        seen.add(tok)

        weight = 1
        if engine is not None:
            if tok in engine.keyword_vocab:
                weight += 3
            if tok in engine.vocab:
                weight += 2
        # Kata lebih panjang biasanya lebih informatif (package, installer, storage).
        if len(tok) >= 6:
            weight += 1
        scored.append((weight, -pos, tok))  # -pos: utamakan yang muncul lebih awal

    scored.sort(reverse=True)
    return [tok for _, __, tok in scored[:max_terms]]


def resolve_query(user_input: str, last_bot_response: str = "") -> str:
    """Perluas kueri pendek / kueri rujukan dengan konteks percakapan sebelumnya.

    Aturan:
      - Jika `user_input` < 4 kata, ATAU
      - mengandung kata rujukan (nya, itu, ini, tersebut, benerin, akhiran -nya),
        maka kata kunci penting dari `last_bot_response` ditambahkan ke kueri.

    Tujuannya agar pertanyaan seperti "benerin itu" atau "terus ram nya?"
    tidak kehilangan arah saat dihitung skor BM25.
    """
    query = (user_input or "").strip()
    last = (last_bot_response or "").strip()

    if not query and not last:
        return ""

    # Tanpa input user, pakai sisa konteks bot (jarang, tapi aman).
    if not query:
        try:
            engine = get_engine()
        except Exception:
            engine = None
        extras = _extract_important_keywords(last, engine=engine)
        return " ".join(extras)

    is_short = _word_count(query) < SHORT_QUERY_MAX_WORDS
    has_ref = _contains_reference(query)

    if (is_short or has_ref) and last:
        try:
            engine = get_engine()
        except Exception:
            engine = None
        extras = _extract_important_keywords(last, engine=engine)
        # Jangan menduplikasi kata yang sudah ada di kueri user.
        existing = set(tokenize(query, remove_stopwords=False))
        extras = [t for t in extras if t not in existing]
        if extras:
            return f"{query} {' '.join(extras)}".strip()

    return query


# ---------------------------------------------------------------------------
# Formatting context untuk SLM
# ---------------------------------------------------------------------------

def _format_context(hits: Sequence[Tuple[Dict[str, Any], float]]) -> str:
    """Gabungkan content hasil teratas menjadi satu blok konteks yang rapi."""
    blocks: List[str] = []
    for rank, (item, score) in enumerate(hits, start=1):
        header = (
            f"[{rank}] {item.get('title', 'Tanpa Judul')} "
            f"(id={item.get('id', '-')}, "
            f"kategori={item.get('category', '-')}, "
            f"skor={score:.3f})"
        )
        body = (item.get("content") or "").strip()
        blocks.append(f"{header}\n{body}")
    return "\n\n---\n\n".join(blocks)


# ---------------------------------------------------------------------------
# Hybrid / BM25 search
# ---------------------------------------------------------------------------

def search_knowledge(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    min_score: float = DEFAULT_MIN_SCORE,
    last_bot_response: str = "",
    kb_path: str = DEFAULT_KB_PATH,
) -> str:
    """Cari entri knowledge base yang paling relevan, lalu kembalikan context.

    Langkah:
      1. Resolve / expand kueri (context stacking).
      2. Tokenisasi kueri hasil resolve.
      3. Hitung skor hybrid BM25 terhadap title + keywords + content.
      4. Buang hasil di bawah `min_score`.
      5. Gabungkan `content` teratas menjadi string konteks untuk SLM.

    Jika tidak ada yang lolos threshold, kembalikan
    ``"Tidak ada memori spesifik"``.
    """
    if top_k <= 0:
        return NO_MEMORY_MSG

    try:
        engine = get_engine(kb_path)
    except (FileNotFoundError, ValueError, ImportError) as exc:
        # Retriever tidak boleh meledakkan chatbot; kembalikan sinyal kosong.
        sys.stderr.write(f"[search_engine] gagal memuat engine: {exc}\n")
        return NO_MEMORY_MSG

    resolved = resolve_query(query, last_bot_response=last_bot_response)
    query_tokens = tokenize(resolved, remove_stopwords=True)

    if not query_tokens:
        return NO_MEMORY_MSG

    scores = engine.hybrid_scores(query_tokens)
    ranked = sorted(
        enumerate(scores),
        key=lambda pair: pair[1],
        reverse=True,
    )

    # Noise filtering: ambil hanya yang lolos ambang, maksimal top_k.
    hits: List[Tuple[Dict[str, Any], float]] = []
    for idx, score in ranked:
        if score < min_score:
            continue
        hits.append((engine.knowledge[idx], float(score)))
        if len(hits) >= top_k:
            break

    if not hits:
        return NO_MEMORY_MSG

    return _format_context(hits)


def search_knowledge_detailed(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    min_score: float = DEFAULT_MIN_SCORE,
    last_bot_response: str = "",
    kb_path: str = DEFAULT_KB_PATH,
) -> Dict[str, Any]:
    """Varian debug: mengembalikan dict berisi kueri ter-resolve, skor, dan context.

    Berguna untuk pengujian mandiri; chatbot cukup memakai `search_knowledge()`.
    """
    resolved = resolve_query(query, last_bot_response=last_bot_response)
    context = search_knowledge(
        query,
        top_k=top_k,
        min_score=min_score,
        last_bot_response=last_bot_response,
        kb_path=kb_path,
    )
    engine = get_engine(kb_path)
    tokens = tokenize(resolved, remove_stopwords=True)
    scores = engine.hybrid_scores(tokens) if tokens else []
    ranked = sorted(
        (
            {
                "id": engine.knowledge[i]["id"],
                "title": engine.knowledge[i]["title"],
                "score": round(float(s), 4),
            }
            for i, s in enumerate(scores)
        ),
        key=lambda x: x["score"],
        reverse=True,
    )
    return {
        "original_query": query,
        "resolved_query": resolved,
        "tokens": tokens,
        "context": context,
        "top_preview": ranked[:5],
    }


# ---------------------------------------------------------------------------
# Pengujian mandiri
# ---------------------------------------------------------------------------

def _print_case(title: str, payload: Dict[str, Any]) -> None:
    """Helper tampilan rapi untuk blok __main__."""
    line = "=" * 72
    print(f"\n{line}\n{title}\n{line}")
    print(f"Query asli     : {payload['original_query']}")
    print(f"Query resolve  : {payload['resolved_query']}")
    print(f"Token BM25     : {payload['tokens']}")
    print("Skor teratas   :")
    for row in payload["top_preview"]:
        print(f"  - {row['score']:7.3f}  {row['id']:16}  {row['title']}")
    print("\n[CONTEXT YANG DISUAPKAN KE SLM]")
    print(payload["context"])


if __name__ == "__main__":
    # Pastikan knowledge.json bisa dimuat sebelum tes pencarian.
    try:
        kb = load_knowledge()
        print(f"Knowledge base termuat: {len(kb)} entri dari {DEFAULT_KB_PATH}")
        get_engine()  # bangun indeks BM25 sekali di awal
    except Exception as err:
        print(f"Gagal inisialisasi: {err}")
        sys.exit(1)

    # 1) Pertanyaan identitas — harus mengenai kategori identity.
    _print_case(
        "TEST 1  |  identitas langsung",
        search_knowledge_detailed("siapa kamu"),
    )

    # 2) Troubleshooting teknis — Package Installer.
    _print_case(
        "TEST 2  |  error Package Installer",
        search_knowledge_detailed(
            "apk gagal install package installer parse error"
        ),
    )

    # 3) Context stacking: kueri pendek + kata rujukan.
    last = (
        "Error Package Installer di Android biasanya muncul sebagai "
        "App not installed atau There was a problem parsing the package. "
        "Penyebab umum file APK rusak atau izin unknown sources belum aktif."
    )
    _print_case(
        "TEST 3  |  kueri pendek + rujukan ('benerin itu')",
        search_knowledge_detailed("benerin itu", last_bot_response=last),
    )

    # 4) Kueri sangat pendek tanpa rujukan eksplisit.
    _print_case(
        "TEST 4  |  kueri pendek 'ram penuh'",
        search_knowledge_detailed("ram penuh"),
    )

    # 5) Query noise — diharapkan tidak lolos threshold.
    _print_case(
        "TEST 5  |  query tidak relevan",
        search_knowledge_detailed("asdfqwer zxcvbnm qwertyuiop"),
    )

    # 6) Pemanggilan fungsi publik persis seperti yang dipakai chatbot.
    print("\n" + "=" * 72)
    print("TEST 6  |  pemanggilan search_knowledge() murni")
    print("=" * 72)
    ctx = search_knowledge(
        "itu apaan sih",
        last_bot_response="Sistem operasi adalah perangkat lunak inti yang mengelola hardware.",
    )
    print(ctx)
````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
search_engine.py
================
Mesin pencari memori (Retriever) untuk chatbot Aira.

Alur singkat:
    user_input  ->  resolve_query()  ->  search_knowledge()  ->  context string
                                         (BM25 + bonus keyword/title)

Dependensi:
    pip install rank_bm25
"""

from __future__ import annotations

import json
import os
import re
import sys
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


# ---------------------------------------------------------------------------
# Konstanta path & konfigurasi default
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_KB_PATH = os.path.join(BASE_DIR, "knowledge.json")

# Ambang default sesuai spesifikasi.
DEFAULT_TOP_K = 2
DEFAULT_MIN_SCORE = 1.5

# Query dianggap pendek jika jumlah katanya di bawah nilai ini.
SHORT_QUERY_MAX_WORDS = 4

# Kata rujukan: sinyal bahwa user sedang menunjuk konteks sebelumnya.
# "nya" sebagai kata mandiri maupun akhiran (masalahnya, caranya) ikut dideteksi.
REFERENCE_WORDS = {
    "nya",
    "itu",
    "ini",
    "tersebut",
    "benerin",
    "beneran",
    "perbaiki",
    "perbaikin",
    "perbaikan",
    "gini",
    "gitu",
    "begini",
    "begitu",
    "tadi",
    "barusan",
    "lanjut",
    "lanjutin",
    "terus",
    "maksudnya",
    "yg",
    "yang",
    "doang",
    "dong",
    "sih",
    "deh",
}

# Stopword ringkas (ID + EN) untuk tokenisasi BM25 dan ekstraksi kata kunci.
# Sengaja tidak memuat istilah domain (android, ram, apk, error, game, os).
STOPWORDS = {
    "ada", "adalah", "agar", "akan", "aku", "anda", "apa", "apakah", "atau",
    "bagai", "bagaimana", "bagi", "bahwa", "baik", "banyak", "baru", "beberapa",
    "belum", "benar", "bisa", "boleh", "buat", "bukan", "cara", "cuma", "dahulu",
    "dalam", "dan", "dapat", "dari", "demikian", "dengan", "di", "dia", "dong",
    "dua", "duluan", "gak", "ga", "gk", "hai", "halo", "hanya", "harus", "hingga",
    "ia", "ingin", "ini", "itu", "iya", "jadi", "jangan", "jika", "juga", "kalau",
    "kali", "kami", "kamu", "karena", "ke", "kita", "kok", "kurang", "lagi",
    "lalu", "lama", "lebih", "lu", "maka", "malah", "masih", "mau", "memang",
    "mengapa", "mereka", "merupakan", "mesti", "mohon", "mungkin", "nah",
    "namun", "nih", "nya", "oleh", "pada", "paling", "para", "per", "pernah",
    "pun", "saat", "saja", "salah", "sama", "sampai", "sangat", "saya", "sebab",
    "sebagai", "sebelum", "sebuah", "secara", "sedang", "sekarang", "sekitar",
    "selalu", "selama", "seluruh", "semua", "sendiri", "seperti", "sering",
    "serta", "sesudah", "setelah", "setiap", "sih", "sudah", "supaya", "tadi",
    "tak", "tanpa", "tapi", "telah", "tentang", "tentu", "terhadap", "tersebut",
    "terus", "tetapi", "tidak", "toh", "tolong", "untuk", "wah", "wahai",
    "waktunya", "ya", "yaitu", "yakni", "yang", "yg",
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in", "is",
    "it", "of", "on", "or", "that", "the", "this", "to", "was", "were", "with",
    "please", "how", "what", "when", "where", "who", "why",
}

# Pesan standar jika tidak ada memori yang lolos threshold.
NO_MEMORY_MSG = "Tidak ada memori spesifik"


# ---------------------------------------------------------------------------
# Utilitas teks
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)
_WORD_RE = re.compile(r"\S+")


def tokenize(text: str, remove_stopwords: bool = True) -> List[str]:
    """Pecah teks menjadi token alfanumerik huruf kecil.

    Angka versi (android12, ram4) tetap dipertahankan. Tanda baca dibuang.
    """
    if not text:
        return []

    tokens = [m.group(0).lower() for m in _TOKEN_RE.finditer(text)]
    if remove_stopwords:
        tokens = [t for t in tokens if t not in STOPWORDS and len(t) > 1]
    else:
        tokens = [t for t in tokens if t]
    return tokens


def _word_count(text: str) -> int:
    """Hitung jumlah kata kasar berdasarkan spasi (bukan token BM25)."""
    if not text or not text.strip():
        return 0
    return len(_WORD_RE.findall(text.strip()))


def _contains_reference(text: str) -> bool:
    """True jika kueri memuat kata rujukan atau akhiran -nya (selain kata pendek)."""
    raw_tokens = [m.group(0).lower() for m in _TOKEN_RE.finditer(text or "")]
    for tok in raw_tokens:
        if tok in REFERENCE_WORDS:
            return True
        # Akhiran posesif/rujukan: "masalahnya", "installernya", "caranya".
        if len(tok) > 3 and tok.endswith("nya"):
            return True
    return False


def _unique_keep_order(items: Iterable[str]) -> List[str]:
    """Deduplikasi token sambil menjaga urutan kemunculan pertama."""
    seen = set()
    out: List[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


# ---------------------------------------------------------------------------
# Loading knowledge base
# ---------------------------------------------------------------------------

def load_knowledge(path: str = DEFAULT_KB_PATH) -> List[Dict[str, Any]]:
    """Muat `knowledge.json` dan validasi struktur minimum setiap entri.

    Setiap objek diharapkan punya: id, category, title, keywords, content.
    Entri yang rusak dilewati, bukan membuat seluruh retriever gagal.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"knowledge.json tidak ditemukan di: {path}"
        )

    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, list):
        raise ValueError("knowledge.json harus berupa array of objects.")

    cleaned: List[Dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        if not item.get("content"):
            continue
        cleaned.append(
            {
                "id": str(item.get("id", "")),
                "category": str(item.get("category", "")),
                "title": str(item.get("title", "")),
                "keywords": [
                    str(k) for k in item.get("keywords", []) if str(k).strip()
                ],
                "content": str(item.get("content", "")),
            }
        )
    return cleaned


def _compose_document(item: Dict[str, Any]) -> str:
    """Gabungkan title, keywords, dan content jadi satu dokumen pencarian.

    Title dan keywords diulang agar BM25 memberi bobot lebih pada metadata
    (trik hybrid sederhana tanpa dependensi extra).
    """
    title = item.get("title", "")
    keywords = " ".join(item.get("keywords", []))
    content = item.get("content", "")
    # title x3 + keywords x2 + content x1
    return f"{title} {title} {title} {keywords} {keywords} {content}"


# ---------------------------------------------------------------------------
# Engine BM25 (diinisialisasi sekali, lalu di-cache)
# ---------------------------------------------------------------------------

class AiraBM25Engine:
    """Pembungkus BM25Okapi + indeks bonus keyword/title."""

    def __init__(self, knowledge: Sequence[Dict[str, Any]]):
        # Impor di dalam kelas agar pesan error lebih jelas jika lib belum ada.
        try:
            from rank_bm25 import BM25Okapi
        except ImportError as exc:
            raise ImportError(
                "Library rank_bm25 belum terpasang. Jalankan: pip install rank_bm25"
            ) from exc

        self.knowledge: List[Dict[str, Any]] = list(knowledge)
        self.documents: List[str] = [_compose_document(it) for it in self.knowledge]
        self.tokenized_corpus: List[List[str]] = [
            tokenize(doc, remove_stopwords=True) for doc in self.documents
        ]
        self.bm25 = BM25Okapi(self.tokenized_corpus)

        # Kosakata knowledge base untuk query expansion yang lebih terarah.
        self.vocab = set()
        self.keyword_vocab = set()
        self.title_tokens: List[set] = []
        self.keyword_tokens: List[set] = []

        for item in self.knowledge:
            t_tok = set(tokenize(item["title"], remove_stopwords=True))
            k_tok = set()
            for kw in item["keywords"]:
                k_tok.update(tokenize(kw, remove_stopwords=True))
            c_tok = set(tokenize(item["content"], remove_stopwords=True))

            self.title_tokens.append(t_tok)
            self.keyword_tokens.append(k_tok)
            self.vocab.update(t_tok | k_tok | c_tok)
            self.keyword_vocab.update(k_tok)

    def hybrid_scores(self, query_tokens: Sequence[str]) -> List[float]:
        """Skor hybrid = BM25 + bonus jika token mengenai title/keywords."""
        if not query_tokens:
            return [0.0] * len(self.knowledge)

        bm25_scores = self.bm25.get_scores(list(query_tokens))
        hybrid: List[float] = []
        q_set = set(query_tokens)

        for idx, base in enumerate(bm25_scores):
            bonus = 0.0
            title_hits = q_set & self.title_tokens[idx]
            keyword_hits = q_set & self.keyword_tokens[idx]
            # Bonus kecil agar tidak menenggelamkan sinyal BM25,
            # tapi cukup untuk menaikkan entri yang benar-benar on-topic.
            bonus += 1.25 * len(title_hits)
            bonus += 0.85 * len(keyword_hits)
            hybrid.append(float(base) + bonus)
        return hybrid


_ENGINE: Optional[AiraBM25Engine] = None
_ENGINE_PATH: Optional[str] = None


def get_engine(path: str = DEFAULT_KB_PATH, reload: bool = False) -> AiraBM25Engine:
    """Ambil singleton engine agar file JSON dan indeks BM25 tidak dibangun ulang."""
    global _ENGINE, _ENGINE_PATH
    if _ENGINE is None or reload or _ENGINE_PATH != os.path.abspath(path):
        knowledge = load_knowledge(path)
        if not knowledge:
            raise ValueError("knowledge.json kosong atau tidak berisi entri valid.")
        _ENGINE = AiraBM25Engine(knowledge)
        _ENGINE_PATH = os.path.abspath(path)
    return _ENGINE


# ---------------------------------------------------------------------------
# Query expansion & context stacking
# ---------------------------------------------------------------------------

def _extract_important_keywords(
    text: str,
    engine: Optional[AiraBM25Engine] = None,
    max_terms: int = 10,
) -> List[str]:
    """Ambil kata kunci penting dari respons bot sebelumnya.

    Prioritas:
      1. Token yang muncul di field keywords knowledge base
      2. Token yang ada di kosakata knowledge base
      3. Token panjang non-stopword lainnya
    """
    tokens = tokenize(text, remove_stopwords=True)
    if not tokens:
        return []

    scored: List[Tuple[int, int, str]] = []
    seen = set()
    for pos, tok in enumerate(tokens):
        if tok in seen or len(tok) < 3:
            continue
        seen.add(tok)

        weight = 1
        if engine is not None:
            if tok in engine.keyword_vocab:
                weight += 3
            if tok in engine.vocab:
                weight += 2
        # Kata lebih panjang biasanya lebih informatif (package, installer, storage).
        if len(tok) >= 6:
            weight += 1
        scored.append((weight, -pos, tok))  # -pos: utamakan yang muncul lebih awal

    scored.sort(reverse=True)
    return [tok for _, __, tok in scored[:max_terms]]


def resolve_query(user_input: str, last_bot_response: str = "") -> str:
    """Perluas kueri pendek / kueri rujukan dengan konteks percakapan sebelumnya.

    Aturan:
      - Jika `user_input` < 4 kata, ATAU
      - mengandung kata rujukan (nya, itu, ini, tersebut, benerin, akhiran -nya),
        maka kata kunci penting dari `last_bot_response` ditambahkan ke kueri.

    Tujuannya agar pertanyaan seperti "benerin itu" atau "terus ram nya?"
    tidak kehilangan arah saat dihitung skor BM25.
    """
    query = (user_input or "").strip()
    last = (last_bot_response or "").strip()

    if not query and not last:
        return ""

    # Tanpa input user, pakai sisa konteks bot (jarang, tapi aman).
    if not query:
        try:
            engine = get_engine()
        except Exception:
            engine = None
        extras = _extract_important_keywords(last, engine=engine)
        return " ".join(extras)

    is_short = _word_count(query) < SHORT_QUERY_MAX_WORDS
    has_ref = _contains_reference(query)

    if (is_short or has_ref) and last:
        try:
            engine = get_engine()
        except Exception:
            engine = None
        extras = _extract_important_keywords(last, engine=engine)
        # Jangan menduplikasi kata yang sudah ada di kueri user.
        existing = set(tokenize(query, remove_stopwords=False))
        extras = [t for t in extras if t not in existing]
        if extras:
            return f"{query} {' '.join(extras)}".strip()

    return query


# ---------------------------------------------------------------------------
# Formatting context untuk SLM
# ---------------------------------------------------------------------------

def _format_context(hits: Sequence[Tuple[Dict[str, Any], float]]) -> str:
    """Gabungkan content hasil teratas menjadi satu blok konteks yang rapi."""
    blocks: List[str] = []
    for rank, (item, score) in enumerate(hits, start=1):
        header = (
            f"[{rank}] {item.get('title', 'Tanpa Judul')} "
            f"(id={item.get('id', '-')}, "
            f"kategori={item.get('category', '-')}, "
            f"skor={score:.3f})"
        )
        body = (item.get("content") or "").strip()
        blocks.append(f"{header}\n{body}")
    return "\n\n---\n\n".join(blocks)


# ---------------------------------------------------------------------------
# Hybrid / BM25 search
# ---------------------------------------------------------------------------

def search_knowledge(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    min_score: float = DEFAULT_MIN_SCORE,
    last_bot_response: str = "",
    kb_path: str = DEFAULT_KB_PATH,
) -> str:
    """Cari entri knowledge base yang paling relevan, lalu kembalikan context.

    Langkah:
      1. Resolve / expand kueri (context stacking).
      2. Tokenisasi kueri hasil resolve.
      3. Hitung skor hybrid BM25 terhadap title + keywords + content.
      4. Buang hasil di bawah `min_score`.
      5. Gabungkan `content` teratas menjadi string konteks untuk SLM.

    Jika tidak ada yang lolos threshold, kembalikan
    ``"Tidak ada memori spesifik"``.
    """
    if top_k <= 0:
        return NO_MEMORY_MSG

    try:
        engine = get_engine(kb_path)
    except (FileNotFoundError, ValueError, ImportError) as exc:
        # Retriever tidak boleh meledakkan chatbot; kembalikan sinyal kosong.
        sys.stderr.write(f"[search_engine] gagal memuat engine: {exc}\n")
        return NO_MEMORY_MSG

    resolved = resolve_query(query, last_bot_response=last_bot_response)
    query_tokens = tokenize(resolved, remove_stopwords=True)

    if not query_tokens:
        return NO_MEMORY_MSG

    scores = engine.hybrid_scores(query_tokens)
    ranked = sorted(
        enumerate(scores),
        key=lambda pair: pair[1],
        reverse=True,
    )

    # Noise filtering: ambil hanya yang lolos ambang, maksimal top_k.
    hits: List[Tuple[Dict[str, Any], float]] = []
    for idx, score in ranked:
        if score < min_score:
            continue
        hits.append((engine.knowledge[idx], float(score)))
        if len(hits) >= top_k:
            break

    if not hits:
        return NO_MEMORY_MSG

    return _format_context(hits)


def search_knowledge_detailed(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    min_score: float = DEFAULT_MIN_SCORE,
    last_bot_response: str = "",
    kb_path: str = DEFAULT_KB_PATH,
) -> Dict[str, Any]:
    """Varian debug: mengembalikan dict berisi kueri ter-resolve, skor, dan context.

    Berguna untuk pengujian mandiri; chatbot cukup memakai `search_knowledge()`.
    """
    resolved = resolve_query(query, last_bot_response=last_bot_response)
    context = search_knowledge(
        query,
        top_k=top_k,
        min_score=min_score,
        last_bot_response=last_bot_response,
        kb_path=kb_path,
    )
    engine = get_engine(kb_path)
    tokens = tokenize(resolved, remove_stopwords=True)
    scores = engine.hybrid_scores(tokens) if tokens else []
    ranked = sorted(
        (
            {
                "id": engine.knowledge[i]["id"],
                "title": engine.knowledge[i]["title"],
                "score": round(float(s), 4),
            }
            for i, s in enumerate(scores)
        ),
        key=lambda x: x["score"],
        reverse=True,
    )
    return {
        "original_query": query,
        "resolved_query": resolved,
        "tokens": tokens,
        "context": context,
        "top_preview": ranked[:5],
    }


# ---------------------------------------------------------------------------
# Pengujian mandiri
# ---------------------------------------------------------------------------

def _print_case(title: str, payload: Dict[str, Any]) -> None:
    """Helper tampilan rapi untuk blok __main__."""
    line = "=" * 72
    print(f"\n{line}\n{title}\n{line}")
    print(f"Query asli     : {payload['original_query']}")
    print(f"Query resolve  : {payload['resolved_query']}")
    print(f"Token BM25     : {payload['tokens']}")
    print("Skor teratas   :")
    for row in payload["top_preview"]:
        print(f"  - {row['score']:7.3f}  {row['id']:16}  {row['title']}")
    print("\n[CONTEXT YANG DISUAPKAN KE SLM]")
    print(payload["context"])


if __name__ == "__main__":
    # Pastikan knowledge.json bisa dimuat sebelum tes pencarian.
    try:
        kb = load_knowledge()
        print(f"Knowledge base termuat: {len(kb)} entri dari {DEFAULT_KB_PATH}")
        get_engine()  # bangun indeks BM25 sekali di awal
    except Exception as err:
        print(f"Gagal inisialisasi: {err}")
        sys.exit(1)

    # 1) Pertanyaan identitas — harus mengenai kategori identity.
    _print_case(
        "TEST 1  |  identitas langsung",
        search_knowledge_detailed("siapa kamu"),
    )

    # 2) Troubleshooting teknis — Package Installer.
    _print_case(
        "TEST 2  |  error Package Installer",
        search_knowledge_detailed(
            "apk gagal install package installer parse error"
        ),
    )

    # 3) Context stacking: kueri pendek + kata rujukan.
    last = (
        "Error Package Installer di Android biasanya muncul sebagai "
        "App not installed atau There was a problem parsing the package. "
        "Penyebab umum file APK rusak atau izin unknown sources belum aktif."
    )
    _print_case(
        "TEST 3  |  kueri pendek + rujukan ('benerin itu')",
        search_knowledge_detailed("benerin itu", last_bot_response=last),
    )

    # 4) Kueri sangat pendek tanpa rujukan eksplisit.
    _print_case(
        "TEST 4  |  kueri pendek 'ram penuh'",
        search_knowledge_detailed("ram penuh"),
    )

    # 5) Query noise — diharapkan tidak lolos threshold.
    _print_case(
        "TEST 5  |  query tidak relevan",
        search_knowledge_detailed("asdfqwer zxcvbnm qwertyuiop"),
    )

    # 6) Pemanggilan fungsi publik persis seperti yang dipakai chatbot.
    print("\n" + "=" * 72)
    print("TEST 6  |  pemanggilan search_knowledge() murni")
    print("=" * 72)
    ctx = search_knowledge(
        "itu apaan sih",
        last_bot_response="Sistem operasi adalah perangkat lunak inti yang mengelola hardware.",
    )
    print(ctx)
```