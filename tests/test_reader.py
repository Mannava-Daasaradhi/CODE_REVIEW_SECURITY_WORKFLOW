import pytest
from cli.reader import read_file


# ── language detection (via read_file return dict) ────────────────────────────

def test_detects_python(tmp_path):
    f = tmp_path / "script.py"
    f.write_text("x = 1\n", encoding="utf-8")
    assert read_file(str(f))["language"] == "python"


def test_detects_javascript(tmp_path):
    f = tmp_path / "app.js"
    f.write_text("const x = 1;\n", encoding="utf-8")
    assert read_file(str(f))["language"] == "javascript"


def test_detects_java(tmp_path):
    f = tmp_path / "Main.java"
    f.write_text("public class Main {}\n", encoding="utf-8")
    assert read_file(str(f))["language"] == "java"


def test_detects_go(tmp_path):
    f = tmp_path / "main.go"
    f.write_text("package main\n", encoding="utf-8")
    assert read_file(str(f))["language"] == "go"


def test_unknown_extension(tmp_path):
    f = tmp_path / "file.xyz"
    f.write_text("data\n", encoding="utf-8")
    assert read_file(str(f))["language"] == "unknown"


def test_case_insensitive_extension(tmp_path):
    f = tmp_path / "SCRIPT.PY"
    f.write_text("x = 1\n", encoding="utf-8")
    assert read_file(str(f))["language"] == "python"


# ── return shape ──────────────────────────────────────────────────────────────

def test_returns_required_keys(tmp_path):
    f = tmp_path / "sample.py"
    f.write_text("def foo():\n    pass\n", encoding="utf-8")
    result = read_file(str(f))
    assert all(k in result for k in ["code", "language", "filename", "lines"])


def test_code_content_correct(tmp_path):
    f = tmp_path / "sample.py"
    f.write_text("def foo():\n    pass\n", encoding="utf-8")
    assert "def foo" in read_file(str(f))["code"]


def test_line_count_correct(tmp_path):
    f = tmp_path / "sample.py"
    f.write_text("a = 1\nb = 2\nc = 3\n", encoding="utf-8")
    assert read_file(str(f))["lines"] == 3


def test_filename_correct(tmp_path):
    f = tmp_path / "mymodule.py"
    f.write_text("x = 1\n", encoding="utf-8")
    assert read_file(str(f))["filename"] == "mymodule.py"


# ── error handling ────────────────────────────────────────────────────────────

def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_file(str(tmp_path / "nonexistent.py"))


def test_empty_file_raises(tmp_path):
    f = tmp_path / "empty.py"
    f.write_text("", encoding="utf-8")
    with pytest.raises(ValueError):
        read_file(str(f))
