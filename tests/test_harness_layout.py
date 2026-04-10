from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_harness_layout_files_exist() -> None:
    expected_paths = [
        ".vertex-proxy/config.json",
        ".vertex-proxy/hooks.json",
        ".vertex-proxy/agents/planner.md",
        ".vertex-proxy/agents/coder.md",
        ".vertex-proxy/agents/verifier.md",
        ".vertex-proxy/agents/challenger.md",
        "harness/__init__.py",
        "harness/types.py",
        "harness/checks/__init__.py",
    ]

    missing = [path for path in expected_paths if not (PROJECT_ROOT / path).exists()]
    assert missing == []
