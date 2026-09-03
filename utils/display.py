import html

import streamlit as st


def rating_icon(rating):
    icons = {
        "Strong": "🟢 Strong",
        "Moderate": "🟡 Moderate",
        "Weak": "🔴 Weak",
    }
    return icons.get(rating, rating)


_CALLOUT_STYLES = {
    "info": {
        "background": "rgba(0, 120, 212, 0.15)",
        "border": "rgba(80, 170, 255, 0.45)",
    },
    "success": {
        "background": "rgba(30, 160, 90, 0.14)",
        "border": "rgba(80, 200, 130, 0.45)",
    },
    "warning": {
        "background": "rgba(210, 160, 0, 0.14)",
        "border": "rgba(230, 185, 40, 0.50)",
    },
}


def render_callout(text, tone="info"):
    if text is None:
        text = ""

    style = _CALLOUT_STYLES.get(
        tone,
        _CALLOUT_STYLES["info"]
    )

    escaped = html.escape(str(text)).replace(
        "\n",
        "<br>"
    )

    callout_html = f"""
    <div style="
        box-sizing: border-box;
        width: 100%;
        max-width: 100%;
        padding: 0.9rem 1rem;
        margin: 0.25rem 0 1rem 0;
        border: 1px solid {style['border']};
        border-radius: 0.55rem;
        background: {style['background']};
        color: inherit;
        font-family: inherit;
        font-size: 1rem;
        font-style: normal;
        font-weight: 400;
        line-height: 1.55;
        white-space: normal;
        overflow-wrap: anywhere;
    ">
        {escaped}
    </div>
    """

    st.html(callout_html)
