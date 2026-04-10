from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class VerificationSpec:
    task: str
    must_pass: list[str] = field(default_factory=list)
    must_not_change: list[str] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class CheckResult:
    name: str
    passed: bool
    summary: str = ""
    weight: int = 0


@dataclass(slots=True)
class ScoreSection:
    name: str
    score: int
    max_score: int
    passed: bool
    checks: list[CheckResult] = field(default_factory=list)


@dataclass(slots=True)
class ScoreSummary:
    sections: list[ScoreSection]
    total_score: int
    max_score: int
    grade: str

    @property
    def passed(self) -> bool:
        return all(section.passed for section in self.sections)
