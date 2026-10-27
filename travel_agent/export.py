"""Export a finished plan: Markdown -> PDF bytes, and itinerary -> iCalendar (.ics).

Pure-Python, free/local. PDF reuses `markdown` + `xhtml2pdf`; emoji/box-drawing/symbol chars are
transliterated so the base PDF fonts render them cleanly.
"""

import re
from datetime import date, datetime, timedelta

_EMOJI = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF\U00002B00-\U00002BFF\uFE0F\u200d]",
    flags=re.UNICODE,
)
_TRANSLIT = {
    "─": "-", "│": "|", "┌": "+", "┐": "+", "└": "+", "┘": "+", "├": "+", "┤": "+", "┬": "+", "┴": "+",
    "┼": "+", "▼": "v", "▲": "^", "►": ">", "◄": "<", "▶": ">", "◀": "<", "→": ">", "←": "<", "↔": "<>",
    "⇄": "<>", "≤": "<=", "≥": ">=", "·": "-", "•": "-", "₹": "Rs ", "—": "-", "–": "-",
    "’": "'", "‘": "'", "“": '"', "”": '"',
}

_CSS = """
body { font-family: Helvetica, Arial, sans-serif; font-size: 10pt; color: #1c2333; line-height: 1.45; }
h1 { font-size: 18pt; color: #4b3fd1; } h2 { font-size: 13pt; color: #1d4ed8; margin-top: 14px; }
h3 { font-size: 11pt; color: #1f7a4d; } table { border-collapse: collapse; width: 100%; }
th { background: #4b3fd1; color: #fff; font-size: 8.5pt; padding: 4px 6px; text-align: left; }
td { border: 1px solid #dde2ec; font-size: 8.5pt; padding: 4px 6px; }
code { font-family: Courier, monospace; background: #f1f3f9; }
"""


def plan_to_pdf(markdown_text: str, title: str = "Travel Plan") -> bytes:
    import io

    import markdown as md
    from xhtml2pdf import pisa

    text = _EMOJI.sub("", markdown_text or "").translate(str.maketrans(_TRANSLIT))
    body = md.markdown(text, extensions=["tables", "fenced_code", "sane_lists"])
    html = f"<!doctype html><html><head><meta charset='utf-8'><style>{_CSS}</style></head><body>{body}</body></html>"
    buf = io.BytesIO()
    pisa.CreatePDF(html, dest=buf, encoding="utf-8")
    return buf.getvalue()


def _ics_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def itinerary_to_ics(trip: dict, itinerary_md: str) -> str:
    """Build an iCalendar with one all-day event per day (from start_date + num_days). Falls back to a single
    trip-long event when the number of days is unknown."""
    dest = (trip or {}).get("destination") or "Trip"
    days = (trip or {}).get("num_days") or 0
    try:
        start = datetime.fromisoformat(trip["start_date"]).date() if trip.get("start_date") else date.today()
    except (ValueError, TypeError, KeyError):
        start = date.today()

    # Pull per-day titles from markdown day headings, if present.
    day_titles = re.findall(r"(?im)^\s*#*\s*day\s*\d+[^\n]*", itinerary_md or "")

    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//TripMate AI//EN", "CALSCALE:GREGORIAN"]
    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    def event(d: date, summary: str, desc: str, uid: str):
        nxt = d + timedelta(days=1)
        return [
            "BEGIN:VEVENT", f"UID:{uid}@tripmate", f"DTSTAMP:{stamp}",
            f"DTSTART;VALUE=DATE:{d.strftime('%Y%m%d')}", f"DTEND;VALUE=DATE:{nxt.strftime('%Y%m%d')}",
            f"SUMMARY:{_ics_escape(summary)}", f"DESCRIPTION:{_ics_escape(desc)}", "END:VEVENT",
        ]

    if days and days > 0:
        for i in range(days):
            title = day_titles[i] if i < len(day_titles) else f"Day {i + 1}"
            lines += event(start + timedelta(days=i), f"{dest} — {title.strip('# ').strip()}",
                           f"TripMate AI plan for {dest}", f"{dest}-{i}")
    else:
        lines += event(start, f"Trip to {dest}", f"TripMate AI plan for {dest}", f"{dest}-trip")
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)
