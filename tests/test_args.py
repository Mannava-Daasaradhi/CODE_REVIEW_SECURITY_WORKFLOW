import pytest
from unittest.mock import patch
from cli.args import parse_args


def test_file_mode():
    with patch("sys.argv", ["r", "myfile.py"]):
        args = parse_args()
        assert args.file == "myfile.py" and args.mode == "full"


def test_mode_bugs():
    with patch("sys.argv", ["r", "f.py", "--mode", "bugs"]):
        assert parse_args().mode == "bugs"


def test_model_default():
    with patch("sys.argv", ["r", "f.py"]):
        assert parse_args().model == "auto"


def test_severity_default():
    with patch("sys.argv", ["r", "f.py"]):
        assert parse_args().severity == "low"


def test_json_flag():
    with patch("sys.argv", ["r", "f.py", "--json"]):
        assert parse_args().json is True


def test_stream_flag():
    with patch("sys.argv", ["r", "f.py", "--stream"]):
        assert parse_args().stream is True


def test_verify_flag():
    with patch("sys.argv", ["r", "f.py", "--verify"]):
        assert parse_args().verify is True


def test_show_thinking_flag():
    with patch("sys.argv", ["r", "f.py", "--show_thinking"]):
        assert parse_args().show_thinking is True


def test_mutual_exclusion():
    with patch("sys.argv", ["r", "f.py", "--dir", "./src"]):
        with pytest.raises(SystemExit):
            parse_args()


def test_no_input():
    with patch("sys.argv", ["r"]):
        with pytest.raises(SystemExit):
            parse_args()


def test_invalid_mode():
    with patch("sys.argv", ["r", "f.py", "--mode", "invalid"]):
        with pytest.raises(SystemExit):
            parse_args()
