"""Keyword selection logic.

This module prioritizes keywords from the n8n payload based on search volume,
difficulty, business relevance, existing page coverage, and duplicate detection.

It MUST NOT:
- Modify files
- Communicate with OpenCode
- Perform Git operations
- Review generated code
- Make AI/LLM calls

It ONLY analyzes and prioritizes keywords.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from seo_agent.core.logging import get_logger

if TYPE_CHECKING:
    from seo_agent.models.api import (
        CompetitorPayload,
        KeywordPayload,
        PagePayload,
        SEOPayload,
    )
    from seo_agent.models.repository import PageInfo

logger = get_logger(__name__)


class KeywordPriority(Enum):
    """Priority level for keywords."""

    CRITICAL = 1  # Must target
    HIGH = 2      # Should target
    MEDIUM = 3    # Nice to have
    LOW = 4       # Consider later


class KeywordSource(Enum):
    """Source of the keyword."""

    SEED = "seed"
    CLUSTER = "cluster"
    SUGGESTED = "suggested"
    COMPETITOR = "competitor"


@dataclass(frozen=True)
class KeywordScore:
    """Scored keyword with priority and reasoning.

    Attributes:
        keyword: Original keyword payload.
        priority: Calculated priority level.
        source: Source of the keyword.
        score: Numerical score (0-100).
        reasoning: Explanation of priority assignment.
        covered_by_existing_page: Whether keyword is already targeted.
        duplicate_of: Keyword this is a duplicate of, if any.
    """

    keyword: KeywordPayload
    priority: KeywordPriority
    source: KeywordSource
    score: float
    reasoning: str
    covered_by_existing_page: bool = False
    duplicate_of: str | None = None


@dataclass(frozen=True)
class KeywordSelectionResult:
    """Result of keyword selection process.

    Attributes:
        selected_keywords: Keywords selected for targeting.
        rejected_keywords: Keywords not selected with reasons.
        duplicates: Groups of duplicate keywords.
        priority_pages_keywords: Keywords mapped to priority pages.
        analyzed_at: Timestamp of analysis.
    """

    selected_keywords: tuple[KeywordScore, ...] = field(default_factory=tuple)
    rejected_keywords: tuple[tuple[KeywordScore, str], ...] = field(default_factory=tuple)
    duplicates: tuple[tuple[str, ...], ...] = field(default_factory=tuple)
    priority_pages_keywords: dict[str, tuple[str, ...]] = field(default_factory=dict)
    analyzed_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def critical_keywords(self) -> tuple[KeywordScore, ...]:
        """Get critical priority keywords."""
        return tuple(k for k in self.selected_keywords if k.priority == KeywordPriority.CRITICAL)

    @property
    def high_priority_keywords(self) -> tuple[KeywordScore, ...]:
        """Get high priority keywords."""
        return tuple(k for k in self.selected_keywords if k.priority == KeywordPriority.HIGH)

    @property
    def total_selected_count(self) -> int:
        """Total number of selected keywords."""
        return len(self.selected_keywords)


class KeywordSelector:
    """Selects and prioritizes keywords from n8n payload.

    This selector consumes the SEO payload from n8n and produces
    a prioritized list of keywords for the task planner.

    It performs analysis only - no file modifications, no AI calls,
    no Git operations, no code review.
    """

    def __init__(
        self,
        max_keywords: int = 50,
        min_search_volume: int = 100,
        max_difficulty: float = 80.0,
    ) -> None:
        """Initialize the keyword selector.

        Args:
            max_keywords: Maximum number of keywords to select.
            min_search_volume: Minimum search volume to consider.
            max_difficulty: Maximum keyword difficulty (0-100).
        """
        self._logger = get_logger(__name__)
        self._max_keywords = max_keywords
        self._min_search_volume = min_search_volume
        self._max_difficulty = max_difficulty

    def select(
        self,
        seo_payload: SEOPayload,
        existing_pages: tuple[PageInfo, ...] | None = None,
    ) -> KeywordSelectionResult:
        """Select and prioritize keywords from n8n payload.

        Args:
            seo_payload: Complete SEO payload from n8n.
            existing_pages: Existing pages for coverage check.

        Returns:
            KeywordSelectionResult with prioritized keywords.
        """
        self._logger.info(
            f"selecting_keywords: seed_count={len(seo_payload.seed_keywords)}, "
            f"cluster_count={len(seo_payload.keyword_clusters)}, "
            f"competitor_count={len(seo_payload.competitors)}"
        )

        # Build existing page coverage map
        existing_coverage = self._build_coverage_map(existing_pages or ())

        # Process all keywords
        all_keywords = self._collect_all_keywords(seo_payload)

        # Score and deduplicate
        scored_keywords = self._score_keywords(all_keywords, existing_coverage)

        # Detect duplicates
        scored_keywords, duplicates = self._detect_duplicates(scored_keywords)

        # Filter and select
        selected, rejected = self._filter_and_select(scored_keywords)

        # Map to priority pages
        priority_mapping = self._map_to_priority_pages(
            selected,
            seo_payload.priority_pages,
        )

        result = KeywordSelectionResult(
            selected_keywords=tuple(selected),
            rejected_keywords=tuple(rejected),
            duplicates=tuple(duplicates),
            priority_pages_keywords=priority_mapping,
        )

        self._logger.info(
            f"keyword_selection_complete: selected={len(selected)}, "
            f"rejected={len(rejected)}, duplicates={len(duplicates)}"
        )

        return result

    def _build_coverage_map(
        self,
        pages: tuple[PageInfo, ...],
    ) -> dict[str, list[str]]:
        """Build a map of keywords covered by existing pages.

        Args:
            pages: Existing pages.

        Returns:
            Dict mapping keywords to page routes.
        """
        coverage: dict[str, list[str]] = {}

        for page in pages:
            if page.metadata and page.metadata.keywords:
                for kw in page.metadata.keywords:
                    term = kw.keyword.term.lower()
                    if term not in coverage:
                        coverage[term] = []
                    coverage[term].append(page.route)

        return coverage

    def _collect_all_keywords(
        self,
        seo_payload: SEOPayload,
    ) -> list[tuple[KeywordPayload, KeywordSource]]:
        """Collect all keywords from payload with sources.

        Args:
            seo_payload: SEO payload from n8n.

        Returns:
            List of (keyword, source) tuples.
        """
        collected: list[tuple[KeywordPayload, KeywordSource]] = []

        # Add seed keywords
        for kw in seo_payload.seed_keywords:
            collected.append((kw, KeywordSource.SEED))

        # Add cluster keywords
        for cluster_name, cluster_keywords in seo_payload.keyword_clusters.items():
            for term in cluster_keywords:
                kw = KeywordPayload(term=term)
                collected.append((kw, KeywordSource.CLUSTER))

        # Add competitor keywords
        for competitor in seo_payload.competitors:
            for strength in competitor.strengths:
                kw = KeywordPayload(term=strength)
                collected.append((kw, KeywordSource.COMPETITOR))

        return collected

    def _score_keywords(
        self,
        keywords: list[tuple[KeywordPayload, KeywordSource]],
        existing_coverage: dict[str, list[str]],
    ) -> list[KeywordScore]:
        """Score and prioritize keywords.

        Args:
            keywords: Keywords with sources.
            existing_coverage: Map of covered keywords.

        Returns:
            List of scored keywords.
        """
        scored: list[KeywordScore] = []

        for keyword, source in keywords:
            score = self._calculate_score(keyword, source, existing_coverage)
            priority = self._determine_priority(score, keyword, source)
            reasoning = self._generate_reasoning(keyword, score, priority, existing_coverage)

            covered = keyword.term.lower() in existing_coverage

            scored.append(KeywordScore(
                keyword=keyword,
                priority=priority,
                source=source,
                score=score,
                reasoning=reasoning,
                covered_by_existing_page=covered,
            ))

        return scored

    def _calculate_score(
        self,
        keyword: KeywordPayload,
        source: KeywordSource,
        existing_coverage: dict[str, list[str]],
    ) -> float:
        """Calculate numerical score for a keyword.

        Args:
            keyword: Keyword to score.
            source: Source of the keyword.
            existing_coverage: Existing coverage map.

        Returns:
            Score from 0-100.
        """
        score = 0.0

        # Search volume contribution (0-40 points)
        if keyword.search_volume is not None:
            if keyword.search_volume >= 10000:
                score += 40
            elif keyword.search_volume >= 1000:
                score += 30
            elif keyword.search_volume >= 500:
                score += 20
            elif keyword.search_volume >= 100:
                score += 10

        # Difficulty contribution (0-30 points, lower is better)
        if keyword.difficulty is not None:
            if keyword.difficulty <= 30:
                score += 30
            elif keyword.difficulty <= 50:
                score += 20
            elif keyword.difficulty <= 70:
                score += 10

        # Source contribution (0-20 points)
        match source:
            case KeywordSource.SEED:
                score += 20
            case KeywordSource.CLUSTER:
                score += 15
            case KeywordSource.COMPETITOR:
                score += 10
            case KeywordSource.SUGGESTED:
                score += 5

        # Primary keyword bonus
        if keyword.type == "primary":
            score += 10

        return min(score, 100.0)

    def _determine_priority(
        self,
        score: float,
        keyword: KeywordPayload,
        source: KeywordSource,
    ) -> KeywordPriority:
        """Determine priority level from score.

        Args:
            score: Calculated score.
            keyword: Keyword being prioritized.
            source: Source of the keyword.

        Returns:
            Priority level.
        """
        # Critical: High score + seed + primary
        if score >= 70 and source == KeywordSource.SEED and keyword.type == "primary":
            return KeywordPriority.CRITICAL

        # High: High score or seed keyword
        if score >= 60 or source == KeywordSource.SEED:
            return KeywordPriority.HIGH

        # Medium: Moderate score
        if score >= 40:
            return KeywordPriority.MEDIUM

        return KeywordPriority.LOW

    def _generate_reasoning(
        self,
        keyword: KeywordPayload,
        score: float,
        priority: KeywordPriority,
        existing_coverage: dict[str, list[str]],
    ) -> str:
        """Generate reasoning for keyword priority.

        Args:
            keyword: Keyword being analyzed.
            score: Calculated score.
            priority: Assigned priority.
            existing_coverage: Coverage map.

        Returns:
            Human-readable reasoning.
        """
        parts = [f"Score: {score:.1f}/100"]

        if keyword.search_volume:
            parts.append(f"Volume: {keyword.search_volume}/mo")
        if keyword.difficulty is not None:
            parts.append(f"Difficulty: {keyword.difficulty:.1f}%")
        if keyword.type == "primary":
            parts.append("Primary keyword")
        if keyword.intent:
            parts.append(f"Intent: {keyword.intent}")

        term = keyword.term.lower()
        if term in existing_coverage:
            parts.append(f"Already covered by: {', '.join(existing_coverage[term])}")

        return " | ".join(parts)

    def _detect_duplicates(
        self,
        keywords: list[KeywordScore],
    ) -> tuple[list[KeywordScore], list[tuple[str, ...]]]:
        """Detect duplicate keywords.

        Args:
            keywords: Scored keywords.

        Returns:
            Tuple of (deduplicated keywords, duplicate groups).
        """
        seen: dict[str, int] = {}  # term -> index
        duplicates: list[tuple[str, ...]] = []
        result: list[KeywordScore] = []

        for kw_score in keywords:
            term = kw_score.keyword.term.lower().strip()

            # Normalize: remove common variations
            normalized = self._normalize_keyword(term)

            if normalized in seen:
                # Mark as duplicate
                existing_idx = seen[normalized]
                result[existing_idx] = KeywordScore(
                    keyword=result[existing_idx].keyword,
                    priority=result[existing_idx].priority,
                    source=result[existing_idx].source,
                    score=result[existing_idx].score,
                    reasoning=result[existing_idx].reasoning,
                    covered_by_existing_page=result[existing_idx].covered_by_existing_page,
                    duplicate_of=kw_score.keyword.term,
                )
                duplicates.append((result[existing_idx].keyword.term, kw_score.keyword.term))
            else:
                seen[normalized] = len(result)
                result.append(kw_score)

        return result, duplicates

    def _normalize_keyword(self, term: str) -> str:
        """Normalize keyword for duplicate detection.

        Args:
            term: Keyword term.

        Returns:
            Normalized term.
        """
        # Remove common stop words and punctuation
        normalized = term.lower()
        for char in ".,!?-":
            normalized = normalized.replace(char, "")
        return " ".join(normalized.split())

    def _filter_and_select(
        self,
        keywords: list[KeywordScore],
    ) -> tuple[list[KeywordScore], list[tuple[KeywordScore, str]]]:
        """Filter and select final keyword list.

        Args:
            keywords: Scored keywords.

        Returns:
            Tuple of (selected keywords, rejected keywords with reasons).
        """
        # Sort by priority then score
        sorted_keywords = sorted(
            keywords,
            key=lambda k: (k.priority.value, -k.score),
        )

        selected: list[KeywordScore] = []
        rejected: list[tuple[KeywordScore, str]] = []

        for kw_score in sorted_keywords:
            # Check if already covered
            if kw_score.covered_by_existing_page:
                if kw_score.priority == KeywordPriority.CRITICAL:
                    # Still select critical keywords even if covered
                    if len(selected) < self._max_keywords:
                        selected.append(kw_score)
                else:
                    rejected.append((kw_score, "Already covered by existing page"))
                continue

            # Check search volume threshold
            if kw_score.keyword.search_volume is not None:
                if kw_score.keyword.search_volume < self._min_search_volume:
                    if kw_score.priority != KeywordPriority.CRITICAL:
                        rejected.append((kw_score, f"Below minimum search volume ({self._min_search_volume})"))
                        continue

            # Check difficulty threshold
            if kw_score.keyword.difficulty is not None:
                if kw_score.keyword.difficulty > self._max_difficulty:
                    if kw_score.priority != KeywordPriority.CRITICAL:
                        rejected.append((kw_score, f"Difficulty too high ({kw_score.keyword.difficulty:.1f}%)"))
                        continue

            # Check max limit
            if len(selected) >= self._max_keywords:
                rejected.append((kw_score, f"Maximum keywords reached ({self._max_keywords})"))
                continue

            selected.append(kw_score)

        return selected, rejected

    def _map_to_priority_pages(
        self,
        keywords: list[KeywordScore],
        priority_pages: list[str],
    ) -> dict[str, tuple[str, ...]]:
        """Map keywords to priority pages.

        Args:
            keywords: Selected keywords.
            priority_pages: Priority page URLs.

        Returns:
            Dict mapping page URLs to keyword terms.
        """
        mapping: dict[str, list[str]] = {url: [] for url in priority_pages}

        # Distribute keywords across priority pages
        for i, kw_score in enumerate(keywords):
            if i < len(priority_pages):
                page_url = priority_pages[i % len(priority_pages)]
                mapping[page_url].append(kw_score.keyword.term)

        return {k: tuple(v) for k, v in mapping.items()}