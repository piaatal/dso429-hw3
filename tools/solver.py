"""Deterministic solver for the DSO 429 hourly quiz.

Each family computes an exact value from the question text, then matches it
against the four options. Returns None when nothing matches confidently --
callers treat that as "unknown" rather than guessing silently.
"""
import re
from datetime import date, timedelta

MONTHS = {
    m: i
    for i, m in enumerate(
        [
            "january", "february", "march", "april", "may", "june",
            "july", "august", "september", "october", "november", "december",
        ],
        1,
    )
}


def num(s):
    """First number in a string, ignoring $ , % and trailing words."""
    m = re.search(r"-?\d[\d,]*(?:\.\d+)?", str(s))
    return float(m.group().replace(",", "")) if m else None


def nums(seg):
    return [float(t.replace(",", "")) for t in re.findall(r"\d[\d,]*(?:\.\d+)?", seg)]


def parse_date(s):
    m = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", s)
    if not m or m.group(2).lower() not in MONTHS:
        return None
    return date(int(m.group(3)), MONTHS[m.group(2).lower()], int(m.group(1)))


# --- families: each returns a number, a date, or None ------------------------

def f_discount(q):
    m = re.search(r"listed at \$?([\d,.]+) is discounted by ([\d.]+)%", q)
    return num(m.group(1)) * (1 - num(m.group(2)) / 100) if m else None


def f_unit_revenue(q):
    m = re.search(r"sells ([\d,]+) units at \$?([\d,.]+) each", q)
    return num(m.group(1)) * num(m.group(2)) if m else None


def f_currency(q):
    m = re.search(r"invoice for \$?([\d,.]+) is converted to \w+ at ([\d.]+)", q)
    return num(m.group(1)) * num(m.group(2)) if m else None


def f_weighted_avg(q):
    m = re.search(
        r"had ([\d,]+) orders averaging \$?([\d,.]+).*?"
        r"had ([\d,]+) orders averaging \$?([\d,.]+)",
        q,
    )
    if not m:
        return None
    n1, a1, n2, a2 = (num(m.group(i)) for i in (1, 2, 3, 4))
    return (n1 * a1 + n2 * a2) / (n1 + n2) if (n1 + n2) else None


def f_gross_margin(q):
    m = re.search(r"\$?([\d,.]+) in revenue against \$?([\d,.]+) in cost", q)
    if not m:
        return None
    rev, cogs = num(m.group(1)), num(m.group(2))
    return (rev - cogs) / rev * 100 if rev else None


def f_compound(q):
    m = re.search(
        r"investment of \$?([\d,.]+) grows at ([\d.]+)% compounded annually."
        r"\s*What is its value after ([\d,]+) years",
        q,
    )
    if not m:
        return None
    p, r, n = (num(m.group(i)) for i in (1, 2, 3))
    return p * (1 + r / 100) ** n


def f_breakeven(q):
    m = re.search(
        r"Fixed costs are \$?([\d,.]+)\. Each unit sells for \$?([\d,.]+) "
        r"with a variable cost of \$?([\d,.]+)",
        q,
    )
    if not m:
        return None
    f, p, v = (num(m.group(i)) for i in (1, 2, 3))
    return round(f / (p - v)) if p != v else None


def f_probability(q):
    pairs = re.findall(r"(\d[\d,]*)\s+(\w+)\s+tickets", q)
    asked = re.search(r"probability it is a[n]?\s+(\w+)\s+ticket", q)
    if not pairs or not asked:
        return None
    total = sum(float(c.replace(",", "")) for c, _ in pairs)
    want = {k.lower(): float(c.replace(",", "")) for c, k in pairs}.get(
        asked.group(1).lower()
    )
    return want / total * 100 if want is not None and total else None


def f_pct_change(q):
    m = re.search(r"moved from \$?([\d,.]+) to \$?([\d,.]+)", q)
    if not m:
        return None
    a, b = num(m.group(1)), num(m.group(2))
    return (b - a) / a * 100 if a else None


def f_ratio_split(q):
    m = re.search(r"\$?([\d,.]+) marketing budget is split .*?ratio (\d+):(\d+)", q)
    if not m:
        return None
    total, a, b = num(m.group(1)), num(m.group(2)), num(m.group(3))
    share = a if "first channel" in q else b if "second channel" in q else None
    return total * share / (a + b) if share is not None and (a + b) else None


def f_sequence(q):
    m = re.search(r"runs ([^.]+)\.\s*If the pattern continues", q)
    if not m:
        return None
    seq = nums(m.group(1))
    if len(seq) < 3:
        return None
    diffs = [seq[i + 1] - seq[i] for i in range(len(seq) - 1)]
    if all(abs(d - diffs[0]) < 1e-9 for d in diffs):
        return seq[-1] + diffs[0]
    if all(abs(s) > 1e-12 for s in seq[:-1]):
        ratios = [seq[i + 1] / seq[i] for i in range(len(seq) - 1)]
        if all(abs(r - ratios[0]) < 1e-9 for r in ratios):
            return seq[-1] * ratios[0]
    return None


def f_settlement_date(q):
    m = re.search(
        r"signed on (\d{1,2}\s+[A-Za-z]+\s+\d{4}) has an? ([\d,]+)-day settlement", q
    )
    if not m:
        return None
    d = parse_date(m.group(1))
    return d + timedelta(days=int(num(m.group(2)))) if d else None


FAMILIES = [
    ("discount", f_discount),
    ("unit_revenue", f_unit_revenue),
    ("currency", f_currency),
    ("weighted_avg", f_weighted_avg),
    ("gross_margin", f_gross_margin),
    ("compound_interest", f_compound),
    ("breakeven_units", f_breakeven),
    ("probability", f_probability),
    ("pct_change", f_pct_change),
    ("ratio_split", f_ratio_split),
    ("sequence", f_sequence),
    ("settlement_date", f_settlement_date),
]

LETTERS = ["A", "B", "C", "D"]


def match_option(value, options):
    """Pick the option matching `value`. Returns a letter, or None if unsure."""
    if isinstance(value, date):
        parsed = [parse_date(o) for o in options]
        hits = [LETTERS[i] for i, p in enumerate(parsed) if p == value]
        return hits[0] if len(hits) == 1 else None

    scored = []
    for i, o in enumerate(options):
        p = num(o)
        if p is not None:
            scored.append((abs(p - value), LETTERS[i]))
    if not scored:
        return None
    scored.sort()
    best, runner = scored[0], (scored[1] if len(scored) > 1 else None)
    scale = max(abs(value), 1.0)
    if best[0] / scale > 0.01:          # best candidate isn't actually close
        return None
    if runner and runner[0] <= best[0] * 5:  # two options nearly as close
        return None
    return best[1]


def solve(question, options):
    """-> (letter, family) or (None, None)."""
    for name, fn in FAMILIES:
        try:
            value = fn(question)
        except (ValueError, ZeroDivisionError, TypeError, AttributeError):
            continue
        if value is None:
            continue
        letter = match_option(value, options)
        if letter:
            return letter, name
    return None, None
