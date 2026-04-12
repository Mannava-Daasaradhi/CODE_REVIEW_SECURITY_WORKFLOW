import json
import pytest
from cli.reporter import print_report, print_json, save_report


def test_print_report_contains_filename(capsys, sample_findings):
    print_report(sample_findings, "myfile.py")
    assert "myfile.py" in capsys.readouterr().out


def test_print_report_contains_score(capsys, sample_findings):
    print_report(sample_findings, "myfile.py")
    assert "42/100" in capsys.readouterr().out


def test_print_report_severity_filter_critical(capsys, sample_findings):
    sample_findings["bugs"] = [
        {"line": 1, "severity": "HIGH", "confidence": 80,
         "fix": "fix it", "description": "Infinite loop"}
    ]
    print_report(sample_findings, "f.py", min_severity="critical")
    assert "Infinite loop" not in capsys.readouterr().out


def test_print_report_show_thinking_false(capsys, sample_findings):
    print_report(sample_findings, "f.py", show_thinking=False)
    assert "Test thinking" not in capsys.readouterr().out


def test_print_report_show_thinking_true(capsys, sample_findings):
    print_report(sample_findings, "f.py", show_thinking=True)
    assert "Test thinking" in capsys.readouterr().out


def test_print_json_valid(capsys, sample_findings):
    print_json(sample_findings, "f.py")
    data = json.loads(capsys.readouterr().out)
    assert "filename" in data


def test_save_report_creates_file(tmp_path, sample_findings):
    out = tmp_path / "report.txt"
    save_report(sample_findings, "f.py", str(out))
    assert out.exists() and "42/100" in out.read_text(encoding="utf-8")


def test_save_report_no_color_codes(tmp_path, sample_findings):
    out = tmp_path / "report.txt"
    save_report(sample_findings, "f.py", str(out))
    assert "\x1b[" not in out.read_text(encoding="utf-8")
