import re

def parse_response(raw: str, mode: str) -> dict:
    res = {"bugs": [], "security": [], "summary": ""}
    try:
        if not isinstance(raw, str):
            return res

        sum_m = re.search(r'(?i)SUMMARY:\s*(.*)', raw, re.DOTALL)
        if sum_m:
            res["summary"] = sum_m.group(1).strip()
            
        pre_sum = raw[:sum_m.start()] if sum_m else raw

        bugs_m = re.search(r'(?i)BUGS:\s*(.*?)(?:(?i)SECURITY:|$)', pre_sum, re.DOTALL)
        if bugs_m:
            b_text = bugs_m.group(1)
            if "none found" not in b_text.lower():
                for line in b_text.splitlines():
                    m = re.match(r'^\s*-\s*Line\s*([0-9]+|None)?\s*:\s*(.*)', line, re.IGNORECASE)
                    if m:
                        l_val = m.group(1)
                        l_num = int(l_val) if l_val and l_val.isdigit() else None
                        res["bugs"].append({"line": l_num, "description": m.group(2).strip()})

        sec_m = re.search(r'(?i)SECURITY:\s*(.*?)(?:(?i)BUGS:|$)', pre_sum, re.DOTALL)
        if sec_m:
            s_text = sec_m.group(1)
            if "none found" not in s_text.lower():
                for line in s_text.splitlines():
                    if re.match(r'^\s*-\s*Line', line, re.IGNORECASE): 
                        continue
                    m = re.match(r'^\s*-\s*([A-Za-z0-9_\s\-]+)\s*:\s*(.*)', line)
                    if m:
                        res["security"].append({
                            "type": m.group(1).strip().upper(),
                            "description": m.group(2).strip()
                        })

        return res
    except Exception:
        return {"bugs": [], "security": [], "summary": ""}