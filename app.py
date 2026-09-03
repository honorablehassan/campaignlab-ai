import streamlit as st
from config import PAGE_ICON, PAGE_TITLE
from core.client import get_openai_client
from core.errors import CampaignLabError
from state import initialize_state
from ui.brand import brand_header
from ui.evidence_lab import render_analytics_directory, render_evidence_lab
from ui.home import render_home
from ui.mmm_lab import render_mmm_lab
from ui.about import render_about
from ui.strategy_lab import render_strategy_lab
from ui.theme import apply_campaignlab_theme, render_top_nav
from ui.system_health import render_system_health
from utils.safe_ui import render_with_error_boundary

st.set_page_config(page_title=PAGE_TITLE,page_icon=PAGE_ICON,layout="wide",initial_sidebar_state="collapsed")
initialize_state(); apply_campaignlab_theme()
try: client=get_openai_client()
except CampaignLabError as exc:
    client=None; st.error(str(exc))
brand_header(); st.divider()
page=st.query_params.get("page","home"); valid={"home","strategy","evidence","mmm","directory","about","health"}
if page not in valid: page="home"
render_top_nav(page); st.divider()
if page=="home": render_with_error_boundary("home",render_home)
elif page=="strategy":
    if client is None: st.info("Connect the OpenAI API key to use Strategy Lab.")
    else: render_with_error_boundary("strategy_lab",render_strategy_lab,client)
elif page=="evidence": render_with_error_boundary("evidence_lab",render_evidence_lab,client)
elif page=="mmm": render_with_error_boundary("mmm_lab",render_mmm_lab)
elif page=="directory": render_with_error_boundary("analytics_directory",render_analytics_directory)
elif page=="about": render_with_error_boundary("about",render_about)
else: render_with_error_boundary("system_health",render_system_health)
