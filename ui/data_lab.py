import streamlit as st


def render_data_lab():
    st.header("📊 Data Lab")
    st.write(
        "Start with what actually happened. CampaignLab checks the data "
        "before trusting it."
    )
    st.divider()

    uploaded_file = st.file_uploader("Upload campaign data", type=["csv", "xlsx"])
    st.text_area(
        "What are you trying to understand?",
        placeholder="Optional: Why did CAC rise? Which channel deserves more budget?",
    )

    if uploaded_file:
        st.success(f"Loaded: {uploaded_file.name}")
        st.button("📊 Run Data Health Check", type="primary", use_container_width=True)
    else:
        st.info("Upload CSV or Excel data to begin.")
