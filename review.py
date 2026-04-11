import sys
import requests
from colorama import Fore, Style

from cli.args import parse_args
from cli.reader import read_file
from cli.prompter import build_prompt
from cli.ollama_client import query_ollama
from cli.parser import parse_response
from cli.reporter import print_report, save_report

def main():
    try:
        args = parse_args()
        file_data = read_file(args.file)
        prompt = build_prompt(file_data["code"], file_data["language"], args.mode)
        raw = query_ollama(prompt, args.model)
        findings = parse_response(raw, args.mode)
        print_report(findings, file_data["filename"])
        if args.output:
            save_report(findings, file_data["filename"], args.output)

    except FileNotFoundError as e:
        print(f"{Fore.RED}File Error:{Style.RESET_ALL} Could not locate the file. {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"{Fore.RED}Value Error:{Style.RESET_ALL} Invalid parameter or data format. {e}", file=sys.stderr)
        sys.exit(1)
    except (ConnectionError, requests.exceptions.ConnectionError) as e:
        print(f"{Fore.RED}Connection Error:{Style.RESET_ALL} Failed to connect to Ollama. Is it running? {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()