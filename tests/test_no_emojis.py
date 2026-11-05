"""
tests/test_no_emojis.py
=======================
Automated test suite asserting complete absence of emojis across:
- web/index.html
- web/app.js
- web/styles.css
- python files and ui strings
"""

import os
import re
import pytest

# Pattern covering all emoji unicode ranges and decorative emoji pictographs
EMOJI_PATTERN = re.compile(
    r"[\U0001F000-\U0001FAFF]"   # Extended pictographic / symbols & pictographs
    r"|[\U00002702-\U000027B0]"  # Dingbats
    r"|[\U0001F600-\U0001F64F]"  # Emoticons
    r"|[\U0001F300-\U0001F5FF]"  # Misc Symbols and Pictographs
    r"|[\U0001F680-\U0001F6FF]"  # Transport and Map
    r"|[\U0001F1E0-\U0001F1FF]"  # Flags
    r"|[\u2600-\u26ff]"          # Miscellaneous symbols (e.g. ⚡, ⚠, etc.)
    r"|[\u2700-\u27bf]"          # Dingbats (e.g. ✓, ✗)
)

# Whitelist allowed mathematical and electrical symbols
ALLOWED_SPECIAL_CHARS = {
    '°',   # Degree symbol (0°, 120°)
    'µ',   # Micro (µs, µF)
    'Ω',   # Ohm
    '·',   # Middle dot
    '–',   # En-dash
    '—',   # Em-dash
    '±',   # Plus-minus
    '≤',   # Less-equal
    '≥',   # Greater-equal
    'π',   # Pi
    'Δ',   # Delta
    '√',   # Sqrt
    '→',   # Arrow
    '←',   # Left arrow
    '•',   # Bullet
    '●',   # Indicator dot
    '┊',   # Dotted divider
}


def test_no_emojis_in_frontend():
    """Verify web/index.html, web/app.js, and web/styles.css contain zero emojis."""
    web_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web")
    target_files = ["index.html", "app.js", "styles.css"]
    violations = []

    for fname in target_files:
        fpath = os.path.join(web_dir, fname)
        if not os.path.exists(fpath):
            continue
        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
            for line_no, line in enumerate(f, 1):
                # Filter out allowed mathematical / electrical units first
                clean_line = "".join(ch for ch in line if ch not in ALLOWED_SPECIAL_CHARS)
                matches = EMOJI_PATTERN.findall(clean_line)
                if matches:
                    violations.append(f"{fname}:{line_no}: Found emojis {matches} in: {line.strip()[:60]}")

    assert not violations, "Found emojis in frontend source files:\n" + "\n".join(violations)


def test_no_emojis_in_app_py():
    """Verify app.py contains zero emojis."""
    app_py = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app.py")
    if not os.path.exists(app_py):
        return
    violations = []
    with open(app_py, "r", encoding="utf-8", errors="ignore") as f:
        for line_no, line in enumerate(f, 1):
            clean_line = "".join(ch for ch in line if ch not in ALLOWED_SPECIAL_CHARS)
            matches = EMOJI_PATTERN.findall(clean_line)
            if matches:
                violations.append(f"app.py:{line_no}: Found emojis {matches} in: {line.strip()[:60]}")

    assert not violations, "Found emojis in app.py:\n" + "\n".join(violations)

