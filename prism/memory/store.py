from __future__ import annotations

import hashlib
import io
import pickle
import re
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import frontmatter as fm

from prism.memory.schemas import Skill, SkillFrontmatter, SearchResult

DB_DEFAULT = Path.home() / ".prism" / "memory" / "index.db"
_MODEL_NAME = "all-MiniLM-L6-v2"

_DDL = """
CREATE VIRTUAL TABLE IF NOT EXISTS skills_fts USING fts5(
    skill_id, title, content, domain_tags, type, status, stack_context
);
CREATE TABLE IF NOT EXISTS skill_embeddings (
    skill_id     TEXT PRIMARY KEY,
    embedding    BLOB,
    model        TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    generated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS skills_meta (
    skill_id     TEXT PRIMARY KEY,
    file_path    TEXT,
    created      TEXT,
    last_used    TEXT,
    reuse_count  INTEGER DEFAULT 0,
    status       TEXT DEFAULT 'active',
    review_after INTEGER,
    verified_by  TEXT
);
"""

_META_INSERT = """
INSERT OR REPLACE INTO skills_meta
(skill_id, file_path, created, last_used, reuse_count, status, review_after, verified_by)
VALUES (?,?,?,?,?,?,?,?)
"""

_MODEL_CACHE: dict = {}


def _load_model():
    try:
        from sentence_transformers import SentenceTransformer
        if _MODEL_NAME not in _MODEL_CACHE:
            _MODEL_CACHE[_MODEL_NAME] = SentenceTransformer(_MODEL_NAME)
        return _MODEL_CACHE[_MODEL_NAME]
    except ImportError:
        return None


def _content_hash(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


def _extract_title(content: str) -> str:
    for line in content.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def _sanitize_query(query: str) -> str:
    return re.sub(r"[^\w\s]", " ", query).strip()


def load_skill_from_file(path: Path) -> Optional[Skill]:
    if not path.exists():
        return None
    post = fm.load(str(path))
    try:
        meta = SkillFrontmatter.model_validate(post.metadata)
    except Exception:
        return None
    return Skill(
        frontmatter=meta,
        title=_extract_title(post.content),
        content=post.content,
        file_path=path,
    )


def save_skill_to_file(skill: Skill, memory_dir: Path) -> Path:
    subdir = memory_dir / skill.frontmatter.subdir()
    subdir.mkdir(parents=True, exist_ok=True)
    path = subdir / f"{skill.frontmatter.skill_id}.md"
    post = fm.Post(skill.content, **skill.frontmatter.model_dump(mode="json"))
    with open(path, "w") as f:
        f.write(fm.dumps(post))
    return path


class SkillStore:
    def __init__(self, db_path: Path = DB_DEFAULT, embeddings_enabled: bool = False):
        self._db_path = db_path
        self._embeddings_enabled = embeddings_enabled
        self._conn: Optional[sqlite3.Connection] = None

    def __enter__(self) -> SkillStore:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._db_path)
        self._conn.row_factory = sqlite3.Row
        for stmt in _DDL.strip().split(";"):
            if stmt.strip():
                self._conn.execute(stmt)
        self._conn.commit()
        return self

    def __exit__(self, *_) -> None:
        if self._conn:
            self._conn.close()

    def upsert(self, skill: Skill) -> None:
        _fts_upsert(self._conn, skill)
        _meta_upsert(self._conn, skill)
        if self._embeddings_enabled:
            _embedding_upsert(self._conn, skill)
        self._conn.commit()

    def delete(self, skill_id: str) -> None:
        for table in ("skills_fts", "skills_meta", "skill_embeddings"):
            self._conn.execute(f"DELETE FROM {table} WHERE skill_id = ?", (skill_id,))
        self._conn.commit()

    def get(self, skill_id: str) -> Optional[Skill]:
        row = self._conn.execute(
            "SELECT file_path FROM skills_meta WHERE skill_id = ?", (skill_id,)
        ).fetchone()
        if not row or not row["file_path"]:
            return None
        return load_skill_from_file(Path(row["file_path"]))

    def list_all(self, status: str = "active") -> list[Skill]:
        rows = self._conn.execute(
            "SELECT skill_id FROM skills_meta WHERE status = ?", (status,)
        ).fetchall()
        return [s for sid in rows if (s := self.get(sid["skill_id"]))]

    def search(self, query: str, top_k: int = 10) -> list[SearchResult]:
        hits = _fts_search(self._conn, query, limit=50)
        if not hits:
            return []
        if self._embeddings_enabled:
            return _hybrid_rerank(self._conn, hits, query, top_k)
        return [SearchResult(skill=s, score=sc, fts_score=sc) for s, sc in hits[:top_k] if s]

    def clear(self) -> None:
        for table in ("skills_fts", "skills_meta", "skill_embeddings"):
            self._conn.execute(f"DELETE FROM {table}")
        self._conn.commit()

    def count(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM skills_meta").fetchone()[0]


def _fts_upsert(conn: sqlite3.Connection, skill: Skill) -> None:
    fm_data = skill.frontmatter
    conn.execute("DELETE FROM skills_fts WHERE skill_id = ?", (fm_data.skill_id,))
    conn.execute(
        "INSERT INTO skills_fts(skill_id,title,content,domain_tags,type,status,stack_context) VALUES(?,?,?,?,?,?,?)",
        (fm_data.skill_id, skill.title, skill.content,
         " ".join(fm_data.domain_tags), fm_data.type, fm_data.status,
         " ".join(fm_data.stack_context)),
    )


def _meta_upsert(conn: sqlite3.Connection, skill: Skill) -> None:
    fm_data = skill.frontmatter
    values = (
        fm_data.skill_id, str(skill.file_path) if skill.file_path else None,
        str(fm_data.created), str(fm_data.last_used) if fm_data.last_used else None,
        fm_data.reuse_count, fm_data.status, fm_data.review_after, fm_data.verified_by,
    )
    conn.execute(_META_INSERT, values)


def _embedding_upsert(conn: sqlite3.Connection, skill: Skill) -> None:
    model = _load_model()
    if model is None:
        return
    text = f"{skill.title} {skill.content}"
    chash = _content_hash(text)
    existing = conn.execute(
        "SELECT content_hash FROM skill_embeddings WHERE skill_id = ?",
        (skill.frontmatter.skill_id,),
    ).fetchone()
    if existing and existing["content_hash"] == chash:
        return
    emb = model.encode(text)
    blob = pickle.dumps(emb)
    conn.execute(
        "INSERT OR REPLACE INTO skill_embeddings(skill_id,embedding,model,content_hash,generated_at) VALUES(?,?,?,?,?)",
        (skill.frontmatter.skill_id, blob, _MODEL_NAME, chash, datetime.utcnow().isoformat()),
    )


def _fts_search(conn: sqlite3.Connection, query: str, limit: int = 50) -> list[tuple[Skill, float]]:
    safe_query = _sanitize_query(query)
    if not safe_query:
        return []
    try:
        rows = conn.execute(
            "SELECT skill_id, bm25(skills_fts) as score FROM skills_fts WHERE skills_fts MATCH ? ORDER BY score LIMIT ?",
            (safe_query, limit),
        ).fetchall()
    except sqlite3.OperationalError:
        return []
    results = []
    for row in rows:
        skill = _load_by_id(conn, row["skill_id"])
        if skill:
            results.append((skill, abs(row["score"])))
    return results


def _load_by_id(conn: sqlite3.Connection, skill_id: str) -> Optional[Skill]:
    row = conn.execute(
        "SELECT file_path FROM skills_meta WHERE skill_id = ?", (skill_id,)
    ).fetchone()
    if not row or not row["file_path"]:
        return None
    return load_skill_from_file(Path(row["file_path"]))


def _get_cached_embedding(conn: sqlite3.Connection, skill_id: str):
    row = conn.execute(
        "SELECT embedding FROM skill_embeddings WHERE skill_id = ?", (skill_id,)
    ).fetchone()
    if row and row["embedding"]:
        return pickle.loads(row["embedding"])
    return None


def _cosine_sim(a, b) -> float:
    import numpy as np
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    return float(np.dot(a, b) / denom) if denom > 1e-9 else 0.0


def _hybrid_rerank(
    conn: sqlite3.Connection,
    candidates: list[tuple[Skill, float]],
    query: str,
    top_k: int,
) -> list[SearchResult]:
    model = _load_model()
    if model is None:
        return [SearchResult(skill=s, score=sc, fts_score=sc) for s, sc in candidates[:top_k]]
    import numpy as np
    query_emb = model.encode(query)
    fts_max = max(sc for _, sc in candidates) or 1.0
    scored: list[SearchResult] = []
    for skill, fts_sc in candidates:
        cached = _get_cached_embedding(conn, skill.frontmatter.skill_id)
        emb = cached if cached is not None else model.encode(f"{skill.title} {skill.content}")
        sem = _cosine_sim(query_emb, emb)
        reuse = min(skill.frontmatter.reuse_count / 10.0, 1.0)
        score = (fts_sc / fts_max) * 0.4 + sem * 0.4 + reuse * 0.2
        scored.append(SearchResult(skill=skill, score=score, fts_score=fts_sc, semantic_score=sem))
    scored.sort(key=lambda r: r.score, reverse=True)
    return scored[:top_k]
