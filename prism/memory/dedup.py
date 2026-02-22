"""Deduplication Detector — TF-IDF based skill similarity detection."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from math import log, sqrt
from typing import Optional

from prism.memory.schemas import Skill


@dataclass
class SimilarityResult:
    skill_a: str
    skill_b: str
    similarity: float
    same_domain: bool
    same_type: bool


def _tokenize(text: str) -> list[str]:
    """Simple tokenization: lowercase, alphanumeric only."""
    text = text.lower()
    tokens = re.findall(r"\b[a-z][a-z0-9_]*\b", text)
    return tokens


def _compute_tf(tokens: list[str]) -> dict[str, float]:
    """Compute term frequency."""
    token_counts = Counter(tokens)
    total_tokens = len(tokens)
    if total_tokens == 0:
        return {}
    return {term: count / total_tokens for term, count in token_counts.items()}


def _compute_idf(documents: list[list[str]]) -> dict[str, float]:
    """Compute inverse document frequency."""
    num_docs = len(documents)
    if num_docs == 0:
        return {}

    # Count how many documents contain each term
    term_doc_counts = Counter()
    all_terms = set()

    for doc in documents:
        unique_terms = set(doc)
        all_terms.update(unique_terms)
        for term in unique_terms:
            term_doc_counts[term] += 1

    # IDF = log(N / df) where df is document frequency
    idf = {}
    for term in all_terms:
        df = term_doc_counts[term]
        idf[term] = log(num_docs / df) if df > 0 else 0.0

    return idf


def _compute_tfidf_vector(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    """Compute TF-IDF vector for a document."""
    tf = _compute_tf(tokens)
    tfidf = {}
    for term, tf_value in tf.items():
        tfidf[term] = tf_value * idf.get(term, 0.0)
    return tfidf


def _cosine_similarity(vec_a: dict[str, float], vec_b: dict[str, float]) -> float:
    """Compute cosine similarity between two vectors."""
    # Get all unique terms
    all_terms = set(vec_a.keys()) | set(vec_b.keys())

    # Compute dot product
    dot_product = sum(vec_a.get(term, 0.0) * vec_b.get(term, 0.0) for term in all_terms)

    # Compute magnitudes
    mag_a = sqrt(sum(v**2 for v in vec_a.values()))
    mag_b = sqrt(sum(v**2 for v in vec_b.values()))

    if mag_a == 0 or mag_b == 0:
        return 0.0

    return dot_product / (mag_a * mag_b)


def find_duplicates(
    skills: list[Skill], threshold: float = 0.8, group_by_domain: bool = True
) -> list[SimilarityResult]:
    """Find potentially duplicate skills using TF-IDF similarity.

    Args:
        skills: List of skills to check
        threshold: Minimum similarity score (0.0-1.0) to consider duplicates
        group_by_domain: If True, only compare skills with shared domain_tags

    Returns:
        List of SimilarityResult for pairs exceeding threshold
    """
    if len(skills) < 2:
        return []

    # Prepare documents (combine title + content for each skill)
    documents = []
    for skill in skills:
        text = f"{skill.title}\n{skill.content}"
        documents.append(_tokenize(text))

    # Compute IDF across all documents
    idf = _compute_idf(documents)

    # Compute TF-IDF vectors
    vectors = [_compute_tfidf_vector(doc, idf) for doc in documents]

    # Find similar pairs
    duplicates = []
    n = len(skills)

    for i in range(n):
        for j in range(i + 1, n):
            skill_a = skills[i]
            skill_b = skills[j]

            # Check domain/type grouping
            same_domain = bool(
                set(skill_a.frontmatter.domain_tags)
                & set(skill_b.frontmatter.domain_tags)
            )
            same_type = skill_a.frontmatter.type == skill_b.frontmatter.type

            if group_by_domain and not same_domain:
                continue

            # Compute similarity
            similarity = _cosine_similarity(vectors[i], vectors[j])

            if similarity >= threshold:
                duplicates.append(
                    SimilarityResult(
                        skill_a=skill_a.frontmatter.skill_id,
                        skill_b=skill_b.frontmatter.skill_id,
                        similarity=similarity,
                        same_domain=same_domain,
                        same_type=same_type,
                    )
                )

    # Sort by similarity descending
    duplicates.sort(key=lambda x: x.similarity, reverse=True)

    return duplicates


def get_duplicates_for_skill(
    skill: Skill, all_skills: list[Skill], threshold: float = 0.8
) -> list[SimilarityResult]:
    """Find duplicates for a specific skill."""
    results = find_duplicates(
        [skill] + [s for s in all_skills if s != skill], threshold
    )
    return [r for r in results if skill.frontmatter.skill_id in (r.skill_a, r.skill_b)]


def format_similarity_report(results: list[SimilarityResult]) -> str:
    """Format similarity results for human-readable output."""
    if not results:
        return "No duplicate skills detected."

    lines = ["Potential duplicates detected:", ""]

    for i, result in enumerate(results[:10], 1):  # Show top 10
        lines.append(f"{i}. {result.skill_a} ↔ {result.skill_b}")
        lines.append(f"   Similarity: {result.similarity:.1%}")
        lines.append(f"   Same domain: {'Yes' if result.same_domain else 'No'}")
        lines.append(f"   Same type: {'Yes' if result.same_type else 'No'}")
        lines.append("")

    if len(results) > 10:
        lines.append(f"... and {len(results) - 10} more pairs")

    return "\n".join(lines)
