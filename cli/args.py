import argparse
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Offline local code reviewer powered by Ollama. Analyze bugs, security, or full review.",
        epilog=(
            "Examples:\n"
            "  reviewer script.py --mode bugs --model llama3\n"
            "  reviewer --dir ./src --severity high --json\n"
            "  reviewer --diff --stream --show_thinking"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("file", nargs="?", type=str, default=None, 
                        help="File to review (required unless --dir or --diff is used)")
    parser.add_argument("--mode", choices=["bugs", "security", "full"], default="full", 
                        help="Review mode focus (default: full)")
    parser.add_argument("--model", type=str, default="auto", 
                        help="Ollama model name to use (default: auto)")
    parser.add_argument("--output", type=str, default=None, 
                        help="File path to save the review report (default: None)")
    parser.add_argument("--severity", choices=["critical", "high", "medium", "low"], default="low", 
                        help="Minimum issue severity to report (default: low)")
    parser.add_argument("--json", action="store_true", 
                        help="Output the review results in JSON format")
    parser.add_argument("--dir", type=str, default=None, 
                        help="Directory to scan and review recursively")
    parser.add_argument("--diff", action="store_true", 
                        help="Review uncommitted changes in the current git repository")
    parser.add_argument("--stream", action="store_true", 
                        help="Stream LLM tokens to stderr in real-time (stdout stays clean for --json)")
    parser.add_argument("--verify", action="store_true", 
                        help="Run a second self-consistency pass to audit findings for false positives")
    parser.add_argument("--show_thinking", action="store_true", 
                        help="Show the LLM's chain of thought or reasoning process")
    args = parser.parse_args()
    count = sum([bool(args.file), bool(args.dir), args.diff])
    if count > 1:
        parser.error("--dir, --diff, and file are mutually exclusive. Pick one.")
    if count == 0:
        parser.error("Provide a file path, --dir <directory>, or --diff.")
    return args