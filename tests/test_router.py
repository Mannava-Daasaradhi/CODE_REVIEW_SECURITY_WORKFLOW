from cli.router import select_model


def test_prefers_qwen_coder_for_bugs():
    assert select_model("bugs", ["qwen3-coder:30b", "llama3"]) == "qwen3-coder:30b"


def test_prefers_deepseek_for_security():
    assert select_model("security", ["deepseek-r1:14b", "llama3"]) == "deepseek-r1:14b"


def test_fallback_to_first():
    assert select_model("bugs", ["somemodel:7b"]) == "somemodel:7b"


def test_empty_available():
    assert select_model("bugs", []) == "codellama"


def test_startswith_not_exact():
    assert select_model("bugs", ["deepseek-coder:6.7b"]) == "deepseek-coder:6.7b"
