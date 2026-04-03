"""
user_data.py — Persistent storage for watchlist and trade journal.
All data stored as JSON files in the data/ directory.
"""
import json
import uuid
from pathlib import Path
from datetime import datetime

WATCHLIST_FILE = Path(__file__).parent / "watchlist.json"
JOURNAL_FILE   = Path(__file__).parent / "trade_journal.json"


def _read(path: Path) -> list:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []


def _write(path: Path, data: list) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ── Watchlist ──────────────────────────────────────────────────────────────────

def load_watchlist() -> list[str]:
    """Returns list of ticker strings."""
    return _read(WATCHLIST_FILE)


def save_watchlist(tickers: list[str]) -> None:
    _write(WATCHLIST_FILE, [t.upper() for t in tickers])


def add_to_watchlist(ticker: str) -> list[str]:
    tickers = load_watchlist()
    t = ticker.upper()
    if t not in tickers:
        tickers.append(t)
        save_watchlist(tickers)
    return tickers


def remove_from_watchlist(ticker: str) -> list[str]:
    tickers = [t for t in load_watchlist() if t != ticker.upper()]
    save_watchlist(tickers)
    return tickers


# ── Trade Journal ──────────────────────────────────────────────────────────────

def load_journal() -> list[dict]:
    """Returns list of saved trade dicts, newest first."""
    entries = _read(JOURNAL_FILE)
    return sorted(entries, key=lambda x: x.get("timestamp", ""), reverse=True)


def save_trade(trade: dict) -> None:
    """Appends a trade to the journal."""
    entries = _read(JOURNAL_FILE)
    if "id" not in trade:
        trade["id"] = uuid.uuid4().hex[:8]
    if "timestamp" not in trade:
        trade["timestamp"] = datetime.now().isoformat(timespec="seconds")
    if "status" not in trade:
        trade["status"] = "saved"
    entries.append(trade)
    _write(JOURNAL_FILE, entries)


def delete_trade(trade_id: str) -> None:
    entries = [e for e in _read(JOURNAL_FILE) if e.get("id") != trade_id]
    _write(JOURNAL_FILE, entries)


def journal_summary() -> dict:
    """Returns quick stats for sidebar display."""
    today = datetime.now().strftime("%Y-%m-%d")
    entries = load_journal()
    today_entries = [e for e in entries if e.get("timestamp", "").startswith(today)]
    go_count  = sum(1 for e in entries if e.get("verdict") == "GO")
    total     = len(entries)
    avg_rr    = sum(e.get("rr_ratio", 0) for e in entries) / total if total else 0
    best      = max((e.get("rr_ratio", 0) for e in entries), default=0)
    return {
        "total":         total,
        "today_count":   len(today_entries),
        "go_count":      go_count,
        "nogo_count":    total - go_count,
        "go_pct":        round(go_count / total * 100) if total else 0,
        "avg_rr":        round(avg_rr, 2),
        "best_rr":       round(best, 2),
    }
