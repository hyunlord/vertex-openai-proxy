from __future__ import annotations

from harness.types import ScoreSection, ScoreSummary


def grade_for_score(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 60:
        return "C"
    return "F"


def summarize_scores(sections: list[ScoreSection]) -> ScoreSummary:
    total_score = sum(section.score for section in sections)
    max_score = sum(section.max_score for section in sections)
    return ScoreSummary(
        sections=sections,
        total_score=total_score,
        max_score=max_score,
        grade=grade_for_score(total_score),
    )
