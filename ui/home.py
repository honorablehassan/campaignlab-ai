import streamlit as st
from ui.brand import intelligence_label, lab_mark, utility_mark, brand_mark


def render_home():
    intelligence_label("Decision system")
    st.markdown("## From messy questions to decisions you can defend.")
    st.caption("Bring an idea, a decision, or a dataset. CampaignLab helps you figure out what to do, what the evidence supports, and what still needs to be tested.")

    st.markdown(f'''
        <a class="cl-special-card" href="?page=mmm" target="_self">
          <div class="cl-special-badge">LAB SPECIAL · BETA</div>
          <div class="cl-special-row">
            <div class="cl-card-icon special">{brand_mark("md")}</div>
            <div><div class="cl-home-eyebrow">MARKETING MIX MODEL</div><div class="cl-special-title">Decide where the next dollar should go.</div>
            <div class="cl-home-copy">Bring the media and sales data you actually have. CampaignLab builds the analytical view, checks whether the mix is learnable, and turns the result into a guarded budget decision.</div>
            <div class="cl-home-cta">Open Marketing Mix Model →</div></div>
          </div>
        </a>
        <div class="cl-home-grid">
          <a class="cl-home-card strategy" href="?page=strategy" target="_self">
            <div class="cl-card-icon">{lab_mark("strategy", "md")}</div>
            <div class="cl-home-eyebrow">STRATEGY LAB</div><div class="cl-home-title">Find the strongest move.</div>
            <div class="cl-home-copy">Turn messy context into a clear recommendation. Compare alternatives, pressure-test assumptions, and see what could change the call.</div>
            <div class="cl-home-cta">Open Strategy Lab →</div>
          </a>
          <a class="cl-home-card evidence" href="?page=evidence" target="_self">
            <div class="cl-card-icon">{lab_mark("evidence", "md")}</div>
            <div class="cl-home-eyebrow">EVIDENCE LAB</div><div class="cl-home-title">Put the claim on trial.</div>
            <div class="cl-home-copy">Bring a question, experiment, or dataset. CampaignLab finds the strongest analytical path and shows what the evidence can actually support.</div>
            <div class="cl-home-cta">Open Evidence Lab →</div>
          </a>
          <a class="cl-home-card support" href="?page=about" target="_self">
            <div class="cl-card-icon">{utility_mark("about", "md")}</div>
            <div class="cl-home-eyebrow">BEHIND THE LAB</div><div class="cl-home-title">Why this lab exists.</div>
            <div class="cl-home-copy">A note from Hassan on curiosity, skepticism, and why better decisions are the point of the whole thing.</div>
            <div class="cl-home-cta">Read the note →</div>
          </a>
        </div>''', unsafe_allow_html=True)

    left,right=st.columns(2)
    with left:
        st.markdown(f'<div class="cl-card-icon">{utility_mark("directory", "md")}</div>', unsafe_allow_html=True)
        st.markdown("### Analytics Directory")
        st.write("See what CampaignLab can analyze and why each method fits, in plain English. Technical detail is there when you want it.")
        st.markdown('[Explore the analytical engine →](?page=directory)')
    with right:
        st.markdown(f'<div class="cl-card-icon">{utility_mark("health", "md")}</div>', unsafe_allow_html=True)
        st.markdown("### System Health")
        st.write("Latency, tool calls, token usage, cost and errors. The engineering layer stays visible without cluttering the decision flow.")
        st.markdown('[Open technical telemetry →](?page=health)')
    st.divider()
    st.markdown("**CampaignLab rule:** calculate what can be calculated, challenge what is assumed, and test what remains uncertain.")
