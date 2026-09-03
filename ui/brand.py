from __future__ import annotations
import streamlit as st

TUBE_SVG = '''<svg class="cl-mark" viewBox="0 0 48 48" aria-hidden="true"><path d="M18 6h12"/><path d="M21 6v15L12.8 34.3A5 5 0 0 0 17 42h14a5 5 0 0 0 4.2-7.7L27 21V6"/><path class="liquid" d="M16.5 33h15l3.2 5.1A2.2 2.2 0 0 1 32.8 41H15.2a2.2 2.2 0 0 1-1.9-2.9z"/></svg>'''

STRATEGY_SVG = '''<svg class="cl-lab-svg strategy" viewBox="0 0 64 64" aria-hidden="true"><path class="glass" d="M24 7h16M27 7v15L16 43.5A8 8 0 0 0 23 56h18a8 8 0 0 0 7-12.5L37 22V7"/><path class="fill" d="M19.5 42h25l4.3 7.4A4.5 4.5 0 0 1 44.9 56H19.1a4.5 4.5 0 0 1-3.9-6.6z"/><circle class="node" cx="27" cy="39" r="2.3"/><circle class="node" cx="38" cy="46" r="2.3"/><circle class="node" cx="29" cy="51" r="2.3"/><path class="thought" d="M28.8 39.8l7.3 5M36.1 47.2l-5 2.8M29.3 41.2l.2 7.4"/></svg>'''

EVIDENCE_SVG = '''<svg class="cl-lab-svg evidence" viewBox="0 0 64 64" aria-hidden="true"><path class="glass" d="M24 7h16M27 7v15L16 43.5A8 8 0 0 0 23 56h18a8 8 0 0 0 7-12.5L37 22V7"/><path class="fill" d="M19.5 42h25l4.3 7.4A4.5 4.5 0 0 1 44.9 56H19.1a4.5 4.5 0 0 1-3.9-6.6z"/><path class="stats" d="M23 50v-5M29 50v-9M35 50v-6M41 50v-12"/><path class="stats-line" d="M22 42.5l7-4 6 1 7-6"/><circle class="dot" cx="22" cy="42.5" r="1.4"/><circle class="dot" cx="29" cy="38.5" r="1.4"/><circle class="dot" cx="35" cy="39.5" r="1.4"/><circle class="dot" cx="42" cy="33.5" r="1.4"/></svg>'''

DIRECTORY_SVG = '''<svg class="cl-utility-svg" viewBox="0 0 48 48" aria-hidden="true"><rect x="7" y="9" width="34" height="30" rx="5"/><path d="M15 17h18M15 24h18M15 31h11"/><circle class="accent" cx="34" cy="31" r="3"/></svg>'''
HEALTH_SVG = '''<svg class="cl-utility-svg" viewBox="0 0 48 48" aria-hidden="true"><rect x="6" y="8" width="36" height="32" rx="6"/><path d="M11 26h7l4-9 5 16 4-9 3 2h4"/></svg>'''
ABOUT_SVG = '''<svg class="cl-utility-svg" viewBox="0 0 48 48" aria-hidden="true"><path d="M11 8h26a4 4 0 0 1 4 4v24a4 4 0 0 1-4 4H11a4 4 0 0 1-4-4V12a4 4 0 0 1 4-4z"/><path d="M14 17h20M14 23h20M14 29h13"/><path class="accent" d="M31 33c3-4 6-5 9-3"/></svg>'''

def brand_mark(size: str = "md") -> str:
    return f'<span class="cl-brand-mark {size}">{TUBE_SVG}</span>'

def lab_mark(lab: str, size: str = "md") -> str:
    svg = STRATEGY_SVG if lab == "strategy" else EVIDENCE_SVG
    return f'<span class="cl-lab-mark {lab} {size}">{svg}</span>'

def utility_mark(kind: str, size: str = "md") -> str:
    svg = {"directory": DIRECTORY_SVG, "health": HEALTH_SVG, "about": ABOUT_SVG}.get(kind, DIRECTORY_SVG)
    return f'<span class="cl-utility-mark {kind} {size}">{svg}</span>'

def brand_header() -> None:
    st.markdown(f'''<div class="cl-brand-header"><div class="cl-brand-line">{brand_mark("lg")}<div><div class="cl-wordmark">CampaignLab</div><div class="cl-tagline">where ideas face reality.</div></div></div></div>''', unsafe_allow_html=True)

def intelligence_label(text: str) -> None:
    st.markdown(f'<div class="cl-intel-label">{brand_mark("xs")}<span>{text}</span></div>', unsafe_allow_html=True)
