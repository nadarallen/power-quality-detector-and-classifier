"""
tools/clean_emojis.py
=====================
Removes all emojis across app.py, docs, mobile_app, and markdown files.
"""

import os
import re

replacements = {
    'page_icon="⚡"': 'page_icon=None',
    '⚡ IEEE 9-Bus': 'IEEE 9-Bus',
    '🔬 Phase 5:': '[Phase 5]',
    '📊 Dataset Explorer': '[Datasets] Explorer',
    '⚔️ Model Comparison': '[Models] Comparison',
    '🔍 Feature Analysis': '[Features] Analysis',
    '🧠 Waveform Model': '[Interpretation] Waveform Model',
    '🛡️ Quarantined': '[Provenance] Quarantined',
    '🏆 Best Overall': '[Rank 1] Best Overall',
    '🥈 Best Waveform': '[Rank 2] Best Waveform',
    '🥉 Best Classical': '[Rank 3] Best Classical',
    '🔴 Critical': '[Critical]',
    '🟡 Moderate': '[Moderate]',
    '🟢 Redundant': '[Redundant]',
    '⚡': '',
    '👉': '',
    '✅': '[OK]',
    '⚠️': '[WARN]',
    '⚠': '[WARN]',
    '❌': '[FAIL]',
    '📱': '[Mobile]',
    '🎨': '[Theme]',
    '🚀': '[Launch]',
    '✓': '[OK]',
    '✗': '[FAIL]',
    '⚡': '',
}

def clean_file(path):
    if not os.path.exists(path):
        return
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    orig = content
    for old, new in replacements.items():
        content = content.replace(old, new)
    if content != orig:
        with open(path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(content)
        print(f"Cleaned: {path}")

# Target files
clean_file('app.py')
clean_file('README.md')
clean_file('web/index.html')
clean_file('web/app.js')
clean_file('web/styles.css')
for root, dirs, files in os.walk('docs'):
    for f in files:
        if f.endswith('.md'):
            clean_file(os.path.join(root, f))
for root, dirs, files in os.walk('mobile_app'):
    for f in files:
        if f.endswith(('.md', '.js', '.jsx')):
            clean_file(os.path.join(root, f))
