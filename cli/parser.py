import re


def _sec(raw: str, name: str) -> str:
    m = re.search(rf"{name}:\s*(.*?)(?=\b(?:THINKING|BUGS|SECURITY|SUMMARY|SCORE):\s*|$)", raw, re.I | re.S)
    return m.group(1).strip() if m else ""


def _parse_list(text: str, is_bug: bool) -> list:
    items = []
    if not text or "none found" in text.lower():
        return items
    for chunk in re.split(r'(?m)^-\s+', text):
        chunk = chunk.strip()
        if not chunk or "none found" in chunk.lower():
            continue
        try:
            sev_m = re.search(r'\[(.*?)\]', chunk)
            sev = sev_m.group(1).upper() if sev_m and sev_m.group(1).upper() in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'] else 'UNKNOWN'

            conf_m = re.search(r'Confidence:\s*(\d+)', chunk, re.I)
            conf = int(conf_m.group(1)) if conf_m else 50

            fix_m = re.search(r'Fix:\s*(.*)', chunk, re.I | re.S)
            fix = fix_m.group(1).strip() if fix_m else ""

            desc = chunk
            if sev_m:
                desc = desc[sev_m.end():]
            elif not is_bug:
                tm = re.match(r'^[^:]+:', desc)
                if tm:
                    desc = desc[tm.end():]

            desc = re.sub(r'(?i)Confidence:.*', '', desc, flags=re.S)
            desc = re.sub(r'(?i)Fix:.*', '', desc, flags=re.S).strip()

            if is_bug:
                lm = re.search(r'^Line\s*(\d+)', chunk, re.I)
                items.append({
                    "line": int(lm.group(1)) if lm else None,
                    "description": desc,
                    "severity": sev,
                    "confidence": conf,
                    "fix": fix,
                })
            else:
                tm = re.match(r'^([^:]+):', chunk)
                items.append({
                    "type": tm.group(1).strip() if tm else "Unknown",
                    "description": desc,
                    "severity": sev,
                    "confidence": conf,
                    "fix": fix,
                })
        except Exception:
            pass
    return items


def parse_response(raw: str, mode: str) -> dict:
    res = {"bugs": [], "security": [], "summary": "", "score": 50, "thinking": ""}
    try:
        res["thinking"] = _sec(raw, "THINKING")
        res["summary"] = _sec(raw, "SUMMARY")
        res["bugs"] = _parse_list(_sec(raw, "BUGS"), True)
        res["security"] = _parse_list(_sec(raw, "SECURITY"), False)

        score_str = _sec(raw, "SCORE")
        sm = re.search(r'\d+', score_str)
        res["score"] = max(0, min(100, int(sm.group()))) if sm else 50
    except Exception:
        pass
    return res


def parse_verification(findings: dict, raw: str) -> dict:
    """
    Args:
        findings: dict with "bugs" and "security" lists (from parse_response)
        raw: the LLM verification response string
    Returns:
        modified findings dict — FALSE_POSITIVE items removed, UNCERTAIN confidence -20
    """
    try:
        statuses = [s.upper() for s in re.findall(r'(FALSE_POSITIVE|UNCERTAIN|CONFIRMED)', raw, re.I)]
        it = iter(statuses)

        for key in ['bugs', 'security']:
            new_list = []
            for item in findings.get(key, []):
                st = next(it, 'CONFIRMED')
                if st == 'FALSE_POSITIVE':
                    continue
                if st == 'UNCERTAIN':
                    item['confidence'] = max(0, item.get('confidence', 50) - 20)
                new_list.append(item)
            findings[key] = new_list
    except Exception:
        pass
    return findings
