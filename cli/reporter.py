import sys
import colorama
from colorama import Fore, Style

colorama.init(autoreset=True)

def _build_report(findings: dict, filename: str, color: bool = False) -> str:
    def c(text: str, color_code: str) -> str:
        return f"{color_code}{text}{Style.RESET_ALL}" if color else text

    thick = " ══════════════════════════════════════"
    thin  = " ──────────────────────────────────────"

    lines = [
        c(thick, Fore.CYAN),
        c(f"  CODE REVIEW REPORT: {filename}", Style.BRIGHT),
        c(thick, Fore.CYAN)
    ]

    bugs = findings.get("bugs", [])
    lines.append(c(f"  🐛 BUGS  ({len(bugs)} found)", Fore.RED + Style.BRIGHT))
    if not bugs:
        lines.append("    None found")
    for b in bugs:
        lines.append(f"    Line {b.get('line', '?')} : {b.get('description', '')}")

    lines.append(c(thin, Fore.CYAN))

    sec = findings.get("security", [])
    lines.append(c(f"  🔒 SECURITY  ({len(sec)} found)", Fore.YELLOW + Style.BRIGHT))
    if not sec:
        lines.append("    None found")
    for s in sec:
        lines.append(f"    {s.get('type', 'UNKNOWN')} : {s.get('description', '')}")

    lines.append(c(thin, Fore.CYAN))

    summary = findings.get("summary", "")
    lines.append(c("  📋 SUMMARY", Fore.GREEN + Style.BRIGHT))
    if not summary:
        lines.append("    None found")
    else:
        lines.append(f"    {summary}")

    lines.append(c(thick, Fore.CYAN))
    return "\n".join(lines)


def print_report(findings: dict, filename: str) -> None:
    print(_build_report(findings, filename, color=True))


def save_report(findings: dict, filename: str, output_path: str) -> None:
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(_build_report(findings, filename, color=False) + "\n")
    except OSError as e:
        print(f"Error saving report to {output_path}: {e}", file=sys.stderr)
        raise