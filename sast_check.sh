#!/bin/bash
# ============================================================
# sast_check.sh — Run Bandit SAST scan on app/
# Run this after Antigravity completes each module.
# If it fails → use _context/security_audit_handoff.md
# ============================================================
#
# USAGE:
#   ./sast_check.sh                    # scan all of app/
#   ./sast_check.sh app/graders        # scan one module
#   ./sast_check.sh --strict           # fail on MEDIUM+ (default: HIGH only)
#
# INSTALL (inside your venv):
#   pip install bandit
#
# OUTPUT:
#   Terminal: color-coded summary
#   logs/sast_bandit.json: full machine-readable report
#   logs/sast_bandit.txt:  human-readable report

set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

TARGET="${1:-app}"
STRICT=false
[[ "$*" == *"--strict"* ]] && STRICT=true
[[ "$TARGET" == "--strict" ]] && TARGET="app"

mkdir -p logs

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  SAST Security Scan — Bandit                  ${NC}"
echo -e "${BLUE}================================================${NC}"
echo -e "Target: ${TARGET}"
echo -e "Strict mode: ${STRICT}"
echo ""

# --- Check bandit is available ---
if ! command -v bandit &> /dev/null; then
  echo -e "${RED}Error: bandit not found.${NC}"
  echo "Install: pip install bandit"
  exit 1
fi

# --- Run Bandit ---
if [ "$STRICT" = true ]; then
  SEVERITY_LEVEL="medium"
  CONFIDENCE_LEVEL="medium"
  echo -e "${YELLOW}Strict mode: failing on MEDIUM severity + MEDIUM confidence${NC}"
else
  SEVERITY_LEVEL="high"
  CONFIDENCE_LEVEL="high"
  echo -e "Standard mode: failing on HIGH severity + HIGH confidence"
fi

echo ""

bandit \
  -r "$TARGET" \
  -f json \
  -o logs/sast_bandit.json \
  --severity-level "$SEVERITY_LEVEL" \
  --confidence-level "$CONFIDENCE_LEVEL" \
  --exclude ".venv,venv,tests" \
  2>/dev/null || true

bandit \
  -r "$TARGET" \
  -f txt \
  -o logs/sast_bandit.txt \
  --severity-level "$SEVERITY_LEVEL" \
  --confidence-level "$CONFIDENCE_LEVEL" \
  --exclude ".venv,venv,tests" \
  2>&1 | tail -40

# --- Parse results ---
if command -v python3 &> /dev/null; then
  python3 - << 'PYEOF'
import json, sys
from pathlib import Path

report_path = Path("logs/sast_bandit.json")
if not report_path.exists():
    print("No report generated.")
    sys.exit(0)

with open(report_path) as f:
    report = json.load(f)

results = report.get("results", [])

highs   = [r for r in results if r["issue_severity"] == "HIGH"]
mediums = [r for r in results if r["issue_severity"] == "MEDIUM"]
lows    = [r for r in results if r["issue_severity"] == "LOW"]

print(f"\n{'='*48}")
print(f"  SAST Summary")
print(f"{'='*48}")
print(f"  HIGH severity:   {len(highs)}")
print(f"  MEDIUM severity: {len(mediums)}")
print(f"  LOW severity:    {len(lows)}")
print(f"{'='*48}")

if highs:
    print("\n  HIGH severity findings (fix before next module):")
    for r in highs:
        print(f"  ✗ {r['filename']}:{r['line_number']} — {r['test_id']}: {r['issue_text'][:80]}")

if len(highs) > 0:
    print(f"\n  RESULT: FAIL — {len(highs)} HIGH severity issue(s) found")
    print(f"  Next step: fill _context/security_audit_handoff.md and escalate to Claude")
    sys.exit(1)
else:
    print(f"\n  RESULT: PASS — no HIGH severity issues found")
    if mediums:
        print(f"  Note: {len(mediums)} MEDIUM issue(s) found — review before Phase 5 ends")
    print(f"  Full report: logs/sast_bandit.txt")
PYEOF
fi

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
  echo -e "${GREEN}SAST check passed. Safe to continue to next module.${NC}"
else
  echo -e "${RED}SAST check failed. Do not proceed.${NC}"
  echo -e "${RED}Fill _context/security_audit_handoff.md and send to Claude.${NC}"
  exit 1
fi
