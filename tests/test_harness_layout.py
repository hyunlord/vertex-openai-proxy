from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_harness_layout_files_exist() -> None:
    expected_paths = [
        "harness/__init__.py",
        "harness/types.py",
        "harness/checks/__init__.py",
        "harness/reporting.py",
        "harness/checks/cross_llm.py",
    ]

    missing = [path for path in expected_paths if not (PROJECT_ROOT / path).exists()]
    assert missing == []


def test_maintainer_only_scaffolding_is_not_shipped_in_public_repo() -> None:
    unexpected_paths = [
        ".vertex-proxy",
        "docs/plans",
    ]

    present = [path for path in unexpected_paths if (PROJECT_ROOT / path).exists()]
    assert present == []
