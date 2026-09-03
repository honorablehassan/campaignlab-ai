import streamlit as st


def render_experiment_lab():
    st.header("🧪 Experiment Lab")
    st.write(
        "When the answer isn't clear, don't manufacture certainty. "
        "Design the cheapest credible way to learn."
    )
    st.divider()

    handoff = st.session_state.get("experiment_handoff")
    if handoff:
        st.success(f"Context received from Strategy Lab: {handoff['strategy_name']}")
        with st.expander("See imported Strategy Lab context"):
            st.markdown(f"**Objective:** {handoff['objective']}")
            st.markdown(f"**Budget:** {handoff['budget']} {handoff['currency']}")
            if handoff["audience"]:
                st.markdown(f"**Audience:** {handoff['audience']}")
            st.markdown("**CampaignLab's suggested test:**")
            st.write(handoff["suggested_experiment"])

    st.text_area(
        "What decision are you uncertain about?",
        placeholder="e.g. Should we offer 20% off or free shipping to maximize first-order conversion?",
        key="experiment_decision_input",
    )
    st.text_input(
        "Primary business outcome",
        placeholder="e.g. Conversion rate, funded accounts, CAC, revenue per visitor",
        key="experiment_outcome_input",
    )
    st.text_area(
        "What do you already know?",
        placeholder="Existing results, traffic, audience, business context...",
        key="experiment_known_input",
        height=180,
    )
    st.text_area(
        "Constraints",
        placeholder="e.g. Must finish within 3 weeks, limited traffic...",
        key="experiment_constraints_input",
    )

    if st.button("🧪 Design Experiment", type="primary", use_container_width=True):
        st.info(
            "The Strategy Lab handoff is now wired. "
            "The statistical Experiment Engine is the next build."
        )
