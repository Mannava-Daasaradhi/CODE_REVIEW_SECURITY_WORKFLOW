import argparse

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="ollama-reviewer",
        description=(
            "A local, offline CLI code reviewer powered by Ollama. "
            "Analyzes provided source code files for bugs, security vulnerabilities, "
            "or performs a full comprehensive review without sending data to the cloud."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        "file",
        type=str,
        help="Path to the code file to be reviewed"
    )

    parser.add_argument(
        "--mode",
        type=str,
        choices=["bugs", "security", "full"],
        default="full",
        help="Focus area for the review"
    )

    parser.add_argument(
        "--model",
        type=str,
        default="codellama",
        help="Ollama model name to use for generation"
    )

    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="File path to save the review report (prints to stdout if omitted)"
    )

    return parser.parse_args()