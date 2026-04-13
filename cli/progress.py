import sys

def show_progress(current: int, total: int, filename: str) -> None:
    if total <= 0:
        return

    pct = int((current / total) * 100)
    filled = round((current / total) * 20)
    bar = "█" * filled + "░" * (20 - filled)

    output = f"Reviewing {current}/{total}: {filename}  [{bar}] {pct}%"
    # Overwrite the same line; pad with spaces to clear any leftover characters
    print(f"{output:<80}", file=sys.stderr, end="\r", flush=True)

    if current == total:
        print(" " * 80, file=sys.stderr, end="\r", flush=True)
        print("", file=sys.stderr)