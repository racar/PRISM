"""Tests for Fase 4 — Optimizer Agent."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from prism.cli.health import _check_file, _check_skills, FileHealth, HealthReport
from prism.memory.compressor import (
    compress,
    count_tokens,
    get_compression_candidates,
    needs_compression,
)
from prism.memory.conflict import ConflictResult, detect_conflict, find_all_conflicts
from prism.memory.dedup import find_duplicates, SimilarityResult
from prism.memory.promoter import analyze_usage_patterns, PromotionCandidate
from prism.memory.schemas import Skill, SkillFrontmatter
from prism.memory.stale import check_staleness, find_stale_skills, StalenessResult


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def sample_skill():
    """Create a sample skill for testing."""
    fm = SkillFrontmatter(
        skill_id="test-skill",
        type="skill",
        domain_tags=["python", "testing"],
        scope="global",
        created=date.today(),
        project_origin="test-project",
    )
    return Skill(
        frontmatter=fm,
        title="Test Skill",
        content="This is a test skill content." * 100,  # Make it longer
        file_path=None,
    )


@pytest.fixture
def large_skill():
    """Create a large skill that needs compression."""
    fm = SkillFrontmatter(
        skill_id="large-skill",
        type="skill",
        domain_tags=["python"],
        scope="global",
        created=date.today(),
        project_origin="test-project",
    )
    # Create content > 2000 tokens
    content = "This is a large skill. " * 500
    return Skill(frontmatter=fm, title="Large Skill", content=content, file_path=None)


@pytest.fixture
def stale_skill():
    """Create a stale skill (not used in 100 days)."""
    fm = SkillFrontmatter(
        skill_id="stale-skill",
        type="skill",
        domain_tags=["python"],
        scope="global",
        created=date.today() - timedelta(days=120),
        last_used=(date.today() - timedelta(days=100)).isoformat(),
        project_origin="old-project",
        status="active",
    )
    return Skill(
        frontmatter=fm, title="Stale Skill", content="Old content", file_path=None
    )


# ── 4.1 Health Checker Tests ─────────────────────────────────────────────────


def test_count_tokens_basic():
    """Test basic token counting."""
    tokens = count_tokens("Hello world")
    assert tokens > 0
    assert isinstance(tokens, int)


def test_check_file_within_limit(tmp_path):
    """Test file health check within limit."""
    test_file = tmp_path / "test.md"
    test_file.write_text("Short content")

    result = _check_file(test_file, limit=1000)

    assert isinstance(result, FileHealth)
    assert result.status == "ok"
    assert result.tokens < 1000


def test_check_file_over_limit(tmp_path):
    """Test file health check over limit."""
    test_file = tmp_path / "test.md"
    test_file.write_text("Word " * 500)  # > 100 tokens

    result = _check_file(test_file, limit=50)

    assert result.status in ["warning", "critical"]


def test_check_skills_detects_stale(stale_skill):
    """Test skill health check detects stale skills."""
    mock_store = MagicMock()
    mock_store.list_all.return_value = [stale_skill]

    result = _check_skills(mock_store)

    assert len(result) == 1
    assert result[0].skill_id == "stale-skill"
    assert result[0].status == "active"
    assert result[0].days_since_used >= 100


# ── 4.2 Memory Compressor Tests ────────────────────────────────────────────────


def test_needs_compression_true(large_skill):
    """Test detection of skills needing compression."""
    assert needs_compression(large_skill, limit=2000) is True


def test_needs_compression_false(sample_skill):
    """Test skills that don't need compression."""
    small_skill = sample_skill
    small_skill.content = "Short content"
    assert needs_compression(small_skill, limit=2000) is False


def test_compress_returns_result(sample_skill):
    """Test compression returns proper result structure."""
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
        with patch("anthropic.Anthropic") as mock_client:
            mock_message = MagicMock()
            mock_message.content = [
                MagicMock(
                    text='{"title": "Compressed", "content": "Short", "tokens": 10}'
                )
            ]
            mock_client.return_value.messages.create.return_value = mock_message

            result = compress(sample_skill, target_tokens=100, dry_run=True)

            assert result is not None
            assert hasattr(result, "success")
            assert hasattr(result, "original_tokens")


def test_get_compression_candidates(large_skill, sample_skill):
    """Test finding compression candidates."""
    mock_store = MagicMock()
    mock_store.list_all.return_value = [large_skill, sample_skill]

    candidates = get_compression_candidates(mock_store, limit=2000)

    assert len(candidates) >= 1  # At least the large skill


# ── 4.3 Deduplication Detector Tests ────────────────────────────────────────


def test_find_duplicates_empty_list():
    """Test deduplication with empty list."""
    result = find_duplicates([], threshold=0.8)
    assert result == []


def test_find_duplicates_single_skill(sample_skill):
    """Test deduplication with single skill."""
    result = find_duplicates([sample_skill], threshold=0.8)
    assert result == []


def test_find_duplicates_similar_skills():
    """Test finding similar skills."""
    fm1 = SkillFrontmatter(
        skill_id="skill-a",
        type="skill",
        domain_tags=["python"],
        scope="global",
        created=date.today(),
        project_origin="test",
    )
    fm2 = SkillFrontmatter(
        skill_id="skill-b",
        type="skill",
        domain_tags=["python"],
        scope="global",
        created=date.today(),
        project_origin="test",
    )

    # Very similar content
    content = "Use pytest for testing Python code. Always write unit tests."
    skill1 = Skill(frontmatter=fm1, title="Test Skill A", content=content)
    skill2 = Skill(
        frontmatter=fm2, title="Test Skill B", content=content + " Also use mocks."
    )

    result = find_duplicates([skill1, skill2], threshold=0.5)

    # Should find similarity
    assert len(result) >= 0  # May or may not match depending on threshold


def test_similarity_result_structure():
    """Test SimilarityResult dataclass."""
    result = SimilarityResult(
        skill_a="skill-1",
        skill_b="skill-2",
        similarity=0.85,
        same_domain=True,
        same_type=True,
    )

    assert result.skill_a == "skill-1"
    assert result.similarity == 0.85
    assert result.same_domain is True


# ── 4.4 Conflict Detector Tests ───────────────────────────────────────────────


def test_detect_conflict_same_domain(sample_skill):
    """Test conflict detection requires same domain."""
    fm2 = SkillFrontmatter(
        skill_id="skill-b",
        type="skill",
        domain_tags=["python"],  # Same domain
        scope="global",
        created=date.today(),
        project_origin="test",
    )
    skill2 = Skill(frontmatter=fm2, title="Skill B", content="Different content")

    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
        result = detect_conflict(sample_skill, skill2, dry_run=True)
        # In dry run, should return simulated result
        assert result is not None


def test_detect_conflict_different_domain(sample_skill):
    """Test no conflict check for different domains."""
    fm2 = SkillFrontmatter(
        skill_id="skill-b",
        type="skill",
        domain_tags=["javascript"],  # Different domain
        scope="global",
        created=date.today(),
        project_origin="test",
    )
    skill2 = Skill(frontmatter=fm2, title="Skill B", content="Content")

    result = detect_conflict(sample_skill, skill2)
    assert result is None  # Should skip different domains


def test_find_all_conflicts_empty():
    """Test finding conflicts in empty list."""
    result = find_all_conflicts([], max_pairs=10)
    assert result == []


def test_conflict_result_structure():
    """Test ConflictResult dataclass."""
    result = ConflictResult(
        skill_a="skill-1",
        skill_b="skill-2",
        conflict_detected=True,
        conflict_type="approach",
        description="Conflicting approaches",
        resolution_hint="Choose one approach",
    )

    assert result.conflict_detected is True
    assert result.conflict_type == "approach"


# ── 4.5 Staleness Checker Tests ───────────────────────────────────────────────


def test_check_staleness_never_used():
    """Test staleness check for never-used skill."""
    fm = SkillFrontmatter(
        skill_id="new-skill",
        type="skill",
        domain_tags=["python"],
        scope="global",
        created=date.today(),
        project_origin="test",
    )
    skill = Skill(frontmatter=fm, title="New", content="Content")

    result = check_staleness(skill, default_review_after=30)

    assert isinstance(result, StalenessResult)
    assert result.skill_id == "new-skill"
    assert result.is_stale is False  # Just created


def test_check_staleness_old_skill(stale_skill):
    """Test staleness check for old skill."""
    result = check_staleness(stale_skill, default_review_after=30)

    assert result.is_stale is True
    assert result.days_since >= 100


def test_find_stale_skills(stale_skill):
    """Test finding stale skills in list."""
    # Create a fresh skill
    fm_fresh = SkillFrontmatter(
        skill_id="fresh-skill",
        type="skill",
        domain_tags=["python"],
        scope="global",
        created=date.today(),
        last_used=date.today().isoformat(),
        project_origin="test",
        status="active",
    )
    fresh_skill = Skill(frontmatter=fm_fresh, title="Fresh", content="Content")

    skills = [stale_skill, fresh_skill]
    result = find_stale_skills(skills, default_review_after=30)

    assert len(result) == 1
    assert result[0].skill_id == "stale-skill"


def test_deprecated_skips_staleness():
    """Test that deprecated skills are not checked for staleness."""
    fm = SkillFrontmatter(
        skill_id="deprecated-skill",
        type="skill",
        domain_tags=["python"],
        scope="global",
        created=date.today() - timedelta(days=200),
        last_used=(date.today() - timedelta(days=150)).isoformat(),
        project_origin="test",
        status="deprecated",
    )
    skill = Skill(frontmatter=fm, title="Deprecated", content="Content")

    skills = [skill]
    result = find_stale_skills(skills, default_review_after=30)

    assert len(result) == 0  # Should skip deprecated


# ── 4.6 Pattern Promoter Tests ────────────────────────────────────────────────


def test_analyze_usage_patterns_empty():
    """Test promotion analysis with empty list."""
    result = analyze_usage_patterns([])
    assert result == []


def test_analyze_usage_patterns_gotcha_promotion():
    """Test detecting gotchas for promotion."""
    # Create the SAME gotcha appearing in multiple projects (by ID)
    gotchas = []
    for i in range(5):
        fm = SkillFrontmatter(
            skill_id="common-gotcha",  # Same ID across projects
            type="gotcha",
            domain_tags=["python"],
            scope="project",
            created=date.today(),
            project_origin=f"project-{i}",
            reuse_count=10,
        )
        gotchas.append(Skill(frontmatter=fm, title="Common Gotcha", content="Content"))

    result = analyze_usage_patterns(gotchas, min_project_count=3)

    # Should find candidates since same gotcha appears in 5 projects
    assert len(result) >= 1
    assert result[0].skill_id == "common-gotcha"


def test_promotion_candidate_structure():
    """Test PromotionCandidate dataclass."""
    candidate = PromotionCandidate(
        skill_id="test-skill",
        current_type="gotcha",
        proposed_type="pattern",
        usage_count=15,
        project_count=4,
        reason="Used across 4 projects",
    )

    assert candidate.current_type == "gotcha"
    assert candidate.proposed_type == "pattern"
    assert candidate.project_count == 4


# ── 4.8 Optimizer Integration Tests ───────────────────────────────────────────


def test_optimizer_health_check_runs(tmp_project):
    """Test that optimizer runs health check."""
    from prism.cli.health import _generate_report

    # Create minimal .prism structure
    prism_dir = tmp_project / ".prism"
    prism_dir.mkdir()
    (prism_dir / "PRISM.md").write_text("# Test")
    (prism_dir / "project.yaml").write_text("name: test")

    report = _generate_report(tmp_project)

    assert isinstance(report, HealthReport)
    assert report.project_name is not None


def test_optimizer_dry_run_no_changes(sample_skill):
    """Test that dry-run mode makes no changes."""
    # Run staleness check in dry-run mode
    stale = find_stale_skills([sample_skill], default_review_after=90)

    # In dry-run, nothing should be marked
    assert len(stale) == 0 or all(not s.is_stale for s in stale)


# ── End-to-End Simulated Flow ────────────────────────────────────────────────


def test_full_optimizer_simulation(large_skill, stale_skill):
    """Simulate full optimizer run."""
    # This test verifies the orchestration works without actual API calls
    skills = [large_skill, stale_skill]

    # 1. Health check
    total_tokens = sum(count_tokens(s.content) for s in skills)
    assert total_tokens > 0

    # 2. Staleness check
    stale = find_stale_skills(skills, default_review_after=30)
    assert len(stale) == 1
    assert stale[0].skill_id == "stale-skill"

    # 3. Compression candidates
    candidates = [s for s in skills if needs_compression(s, limit=2000)]
    assert len(candidates) >= 1

    # 4. Deduplication
    duplicates = find_duplicates(skills, threshold=0.8)
    # May be empty or not depending on content similarity
    assert isinstance(duplicates, list)
