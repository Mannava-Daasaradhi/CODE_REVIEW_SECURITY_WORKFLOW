import json
from colorama import init, Fore, Style

init(autoreset=True)

SEV_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}

def _build_report(f: dict, fn: str, min_s: str, show_t: bool, c: bool) -> str:
    res = Style.RESET_ALL if c else ""
    def cstr(txt, col): return f"{col}{txt}{res}" if c else str(txt)
    
    sc = f.get("score", 0)
    s_col = Fore.GREEN if sc >= 70 else Fore.YELLOW if sc >= 40 else Fore.RED
    
    lines = [
        "══════════════════════════════════════════════",
        f" CODE REVIEW REPORT: {fn}   SCORE: {cstr(f'{sc}/100', s_col)}",
        "══════════════════════════════════════════════"
    ]
    
    if show_t and f.get("thinking"):
        lines.extend([
            "──────────────────────────────────────────────",
            " 🧠 THINKING",
            f"  {f['thinking']}"
        ])

    m_idx = SEV_ORDER.get(min_s.lower(), 0)
    def filt(items):
        return [i for i in items if SEV_ORDER.get(i.get("severity", "unknown").lower(), 99) >= m_idx]

    def get_col(sev):
        s = sev.lower()
        if s == "critical": return Fore.RED + Style.BRIGHT
        if s == "high": return Fore.RED
        if s == "medium": return Fore.YELLOW
        return Fore.WHITE

    def add_items(items, title, is_bug=True):
        lines.append(f" {title}  ({len(items)} found)")
        for i in items:
            sev = i.get("severity", "default").upper()
            col = get_col(sev)
            conf = i.get("confidence", 0)
            filled = round(conf / 10)
            bar = "█" * filled + "░" * (10 - filled)
            hdr = f"Line {i.get('line')}" if is_bug else i.get("type")
            
            lines.extend([
                f"  [{cstr(sev, col)}] {hdr}: {i.get('description')}",
                f"               Confidence: {bar} {conf}%",
                f"               Fix: {i.get('fix', '')}"
            ])

    add_items(filt(f.get("bugs", [])), "🐛 BUGS", is_bug=True)
    lines.append("──────────────────────────────────────────────")
    
    add_items(filt(f.get("security", [])), "🔒 SECURITY", is_bug=False)
    lines.extend([
        "──────────────────────────────────────────────",
        " 📋 SUMMARY",
        f"  {f.get('summary', '')}",
        f" 📊 SCORE: {cstr(f'{sc}/100', s_col)}",
        "══════════════════════════════════════════════"
    ])
    
    return "\n".join(lines)

def print_report(findings: dict, filename: str, min_severity: str = "low", show_thinking: bool = False) -> None:
    print(_build_report(findings, filename, min_severity, show_thinking, c=True))

def print_json(findings: dict, filename: str) -> None:
    print(json.dumps({"filename": filename, "findings": findings}, indent=2))

def save_report(findings: dict, filename: str, output_path: str) -> None:
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(_build_report(findings, filename, "low", False, c=False) + "\n")