import pytest
from cli.parser import parse_response, parse_verification


def test_parse_bugs(sample_raw_response):
    r = parse_response(sample_raw_response, "full")
    assert len(r["bugs"]) == 1
    assert r["bugs"][0]["severity"] == "CRITICAL"
    assert r["bugs"][0]["confidence"] == 90
    assert r["bugs"][0]["line"] == 4


def test_parse_security_none(sample_raw_response):
    r = parse_response(sample_raw_response, "full")
    assert r["security"] == []


def test_parse_summary(sample_raw_response):
    assert parse_response(sample_raw_response, "full")["summary"] == "Test summary"


def test_parse_score(sample_raw_response):
    assert parse_response(sample_raw_response, "full")["score"] == 42


def test_parse_thinking(sample_raw_response):
    assert parse_response(sample_raw_response, "full")["thinking"] == "Test reasoning"


def test_score_clamped():
    raw = "BUGS:\nNone\nSECURITY:\nNone\nSUMMARY:\nok\nSCORE: 150"
    assert parse_response(raw, "full")["score"] == 100


def test_never_raises():
    r = parse_response("", "full")
    assert all(k in r for k in ["bugs", "security", "summary", "score", "thinking"])


def test_verification_removes_false_positive(sample_findings):
    result = parse_verification(sample_findings, "FALSE_POSITIVE: not real")
    assert result["bugs"] == []


def test_verification_reduces_uncertain(sample_findings):
    sample_findings["bugs"][0]["confidence"] = 80
    result = parse_verification(sample_findings, "UNCERTAIN: maybe")
    assert result["bugs"][0]["confidence"] == 60


def test_verification_confirmed_unchanged(sample_findings):
    sample_findings["bugs"][0]["confidence"] = 80
    result = parse_verification(sample_findings, "CONFIRMED: real")
    assert result["bugs"][0]["confidence"] == 80
