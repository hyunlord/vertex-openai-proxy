from harness.checks.mechanical import format_command_summary, run_mechanical_check


def test_run_mechanical_check_captures_success() -> None:
    result = run_mechanical_check("echo", ["python3", "-c", "print('ok')"])

    assert result.name == "echo"
    assert result.passed is True
    assert "exit_code=0" in result.summary
    assert "ok" in result.summary


def test_run_mechanical_check_captures_failure() -> None:
    result = run_mechanical_check("fail", ["python3", "-c", "raise SystemExit(2)"])

    assert result.passed is False
    assert "exit_code=2" in result.summary


def test_format_command_summary_is_stable() -> None:
    summary = format_command_summary(1, "a\nb\nc\nd", "x\ny\nz\nw", 12.3)

    assert "elapsed_ms=12.3" in summary
    assert "stdout=['a', 'b', 'c']" in summary
    assert "stderr=['x', 'y', 'z']" in summary
