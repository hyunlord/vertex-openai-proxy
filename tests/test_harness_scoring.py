from harness.scorer import grade_for_score, summarize_scores
from harness.types import CheckResult, ScoreSection


def test_grade_mapping() -> None:
    assert grade_for_score(92) == "A"
    assert grade_for_score(80) == "B"
    assert grade_for_score(61) == "C"
    assert grade_for_score(40) == "F"


def test_score_summary_aggregates_sections() -> None:
    summary = summarize_scores(
        [
            ScoreSection(
                name="mechanical",
                score=28,
                max_score=30,
                passed=True,
                checks=[CheckResult(name="pytest", passed=True, weight=10)],
            ),
            ScoreSection(
                name="protocol",
                score=35,
                max_score=40,
                passed=True,
                checks=[CheckResult(name="chat", passed=True, weight=10)],
            ),
        ]
    )

    assert summary.total_score == 63
    assert summary.max_score == 70
    assert summary.grade == "C"
    assert summary.passed is True


def test_score_summary_marks_failed_sections() -> None:
    summary = summarize_scores(
        [
            ScoreSection(name="mechanical", score=30, max_score=30, passed=True),
            ScoreSection(name="cross_llm", score=0, max_score=20, passed=False),
        ]
    )

    assert summary.total_score == 30
    assert summary.grade == "F"
    assert summary.passed is False
