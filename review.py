import sys
from colorama import Fore, Style
from cli.args import parse_args
from cli.reader import read_file
from cli.prompter import build_prompt, build_verification_prompt
from cli.ollama_client import query_ollama, list_models
from cli.parser import parse_response, parse_verification
from cli.reporter import print_report, print_json, save_report
from cli.router import select_model
from cli.scanner import scan_directory
from cli.differ import get_diff_files

def main():
    try:
        args = parse_args()
        model = select_model(args.mode, list_models()) if args.model == "auto" else args.model

        if args.dir:
            results = scan_directory(args.dir, model, args.mode, args.stream)
            print("══════════════════════════════════════════════")
            print(f" SCAN COMPLETE: {len(results)} files reviewed")
            print("══════════════════════════════════════════════")
            for result in results:
                score = result["findings"].get("score", 50)
                color = Fore.GREEN if score >= 70 else (Fore.YELLOW if score >= 40 else Fore.RED)
                print(f" {result['filename']}: {color}SCORE {score}/100{Style.RESET_ALL}")
            print("══════════════════════════════════════════════")
            sys.exit(0)

        files = get_diff_files() if args.diff else [{"filename": args.file, "language": None, "content": None}]

        for item in files:
            if args.diff:
                code = item["diff_content"]
                language = item["language"]
                filename = item["filename"]
            else:
                result = read_file(args.file)
                code, language = result["code"], result["language"]
                filename = args.file

            prompt = build_prompt(code, language, args.mode, filename=filename)
            raw = query_ollama(prompt, model, stream=args.stream)
            findings = parse_response(raw, args.mode)

            if args.verify:
                vp = build_verification_prompt(code, findings, language)
                vraw = query_ollama(vp, model, stream=False)
                findings = parse_verification(vraw, findings)

            if args.json:
                print_json(findings, filename)
            else:
                print_report(findings, filename, min_severity=args.severity, show_thinking=args.show_thinking)

            if args.output:
                save_report(findings, filename, args.output)

    except FileNotFoundError as e: print(f"Error: File not found: {e}", file=sys.stderr); sys.exit(1)
    except ValueError as e: print(f"Error: {e}", file=sys.stderr); sys.exit(1)
    except ConnectionError as e: print(f"Error: {e}", file=sys.stderr); sys.exit(1)
    except RuntimeError as e: print(f"Error: {e}", file=sys.stderr); sys.exit(1)
    except OSError as e: print(f"Error saving report: {e}", file=sys.stderr); sys.exit(1)

if __name__ == "__main__":
    main()