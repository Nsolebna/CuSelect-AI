"""Public, evidence-aware introduction to CuSelect-AI research."""

import streamlit as st


def render_public_research():
    st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] {
        background: #0c1517;
        color: #eef7f5;
    }
    [data-testid="stHeader"] {
        background: #0c1517;
    }
    [data-testid="stSidebar"] {
        display: none;
    }
    .block-container {
        max-width: 1120px;
        padding-top: 2rem;
    }
    .research-kicker {
        color: #6bd7ca;
        text-transform: uppercase;
        letter-spacing: .16em;
        font-size: .76rem;
        font-weight: 700;
    }
    .research-lead {
        color: #b4c9c9;
        font-size: 1.15rem;
        line-height: 1.7;
    }
    .research-panel {
        padding: 1.5rem;
        border: 1px solid #294246;
        background: #132023;
        border-radius: 16px;
        margin: 0.8rem 0;
    }
    .research-panel h3 {
        color: #f1f8f7;
        margin-top: 0;
    }
    .research-panel p {
        color: #bccdcc;
        line-height: 1.7;
    }
    </style>
    """, unsafe_allow_html=True)

    head_left, head_right = st.columns([4, 1])

    with head_left:
        st.markdown("### ◈ CuSelect-AI")

    with head_right:
        if st.button("← Home", width="stretch"):
            st.session_state["public_page"] = "home"
            st.rerun()

    st.divider()

    st.markdown(
        '<p class="research-kicker">Our scientific approach</p>',
        unsafe_allow_html=True
    )
    st.title("From evidence to better experiments.")
    st.markdown(
        '<p class="research-lead">'
        'CuSelect-AI explores how scientific literature, '
        'AI-assisted catalyst hypotheses, critical review, '
        'and computational evidence can inform research into '
        'electrochemical CO₂ reduction.'
        '</p>',
        unsafe_allow_html=True
    )

    st.write("")
    st.subheader("The research challenge")
    st.write(
        "Catalyst design requires connecting observations across "
        "published experiments, synthesis methods, reaction conditions, "
        "surface structures, and mechanistic hypotheses. "
        "AI-generated proposals must be evaluated against this evidence, "
        "not treated as established scientific results."
    )

    st.write("")
    st.subheader("Our research workflow")

    stages = [
        ("01 · Evidence",
         "Review source material, verified claims, and experimental "
         "measurements. Preserve provenance and distinguish observations "
         "from interpretations."),
        ("02 · Catalyst design",
         "Develop hypotheses about catalyst architectures and "
         "electrochemical behavior."),
        ("03 · Scientific Critic",
         "Identify unsupported assumptions, confounding variables, "
         "mechanistic gaps, and missing validation."),
        ("04 · Revision",
         "Respond to scientific criticism and propose experimentally "
         "testable next steps."),
    ]

    for title, description in stages:
        st.markdown(
            f'<div class="research-panel"><h3>{title}</h3>'
            f'<p>{description}</p></div>',
            unsafe_allow_html=True
        )

    st.write("")
    st.subheader("Research demonstration: Ag/Cu catalyst design")

    left, right = st.columns([3, 2], gap="large")

    with left:
        st.markdown("#### Patterned Ag-island Cu foil")
        st.write(
            "The historical research case investigates whether the "
            "spatial distribution of Ag islands on Cu can influence "
            "the local CO environment and hypotheses about "
            "ethylene formation."
        )
        st.write(
            "The recorded workflow includes a catalyst proposal, "
            "six Critic findings, six revision responses, and "
            "three proposed experiments."
        )

    with right:
        st.warning("Research status: Revise before advancing")
        st.caption(
            "The historical Critic report does not document "
            "evaluated-v2 instruction provenance."
        )

    st.divider()
    st.subheader("Scientific transparency")

    st.write(
        "The available atomistic structures and computational "
        "records are preliminary evidence. They do not validate "
        "the proposed Ag-island geometry at experimental scale, "
        "predict Faradaic efficiency, or establish an improvement "
        "in ethylene selectivity."
    )

    st.info(
        "CuSelect-AI is a research prototype. AI-generated hypotheses "
        "and proposed experiments require independent human "
        "scientific assessment."
    )

    st.write("")
    if st.button(
        "Sign in to explore the research workspace",
        type="primary"
    ):
        st.login()
