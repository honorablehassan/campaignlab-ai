import streamlit as st

st.set_page_config(
    page_title="CampaignLab AI",
    page_icon="🧪",
    layout="wide"
)

st.title("🧪 CampaignLab AI")
st.subheader("AI-powered marketing strategy & experimentation lab")

product = st.text_input(
    "Describe your product or brand",
    placeholder="e.g. A premium protein coffee for busy professionals"
)

audience = st.text_input(
    "Target audience",
    placeholder="e.g. Health-conscious professionals aged 25–40"
)

objective = st.selectbox(
    "Business objective",
    ["Increase Sales", "Generate Leads", "Build Awareness", "Drive App Installs"]
)

budget = st.slider(
    "Marketing budget ($)",
    min_value=1000,
    max_value=100000,
    value=25000,
    step=1000
)

if st.button("Generate Strategy"):
    st.success("CampaignLab is ready. AI strategy generation is coming next.")