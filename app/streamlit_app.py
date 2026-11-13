
"""CuSelect-AI — scientific catalyst discovery homepage."""

from pathlib import Path
import base64
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]

PORTRAIT = ROOT / "assets/cuselect_hero_portrait.png"
FALLBACK = ROOT / "assets/cuselect_hero.png"
HERO = PORTRAIT if PORTRAIT.exists() else FALLBACK

st.set_page_config(
    page_title="CuSelect-AI | Scientific Catalyst Discovery",
    page_icon="⚛️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');

:root {
    --bg: #0c1716;
    --surface: #122522;
    --accent: #62d5c8;
    --text: #f5f8f7;
    --muted: #b2c6c1;
}

/* Background */
html, body, .stApp,
[data-testid="stAppViewContainer"],
[data-testid="stHeader"] {
    background: var(--bg) !important;
    color: var(--text) !important;
}

/* Hide Streamlit's duplicate navigation */
[data-testid="stSidebar"],
[data-testid="stSidebarCollapsedControl"],
[data-testid="stExpandSidebarButton"] {
    display: none !important;
}

/* Page margins */
[data-testid="stMainBlockContainer"],
.block-container {
    width: calc(100% - 6vw) !important;
    max-width: 1520px !important;
    margin: 0 auto !important;
    padding: 0.6rem 0 1rem !important;
}

/* Typography */
html, body, p, button {
    font-family: 'Inter', sans-serif !important;
}

h1, h2, h3, h4 {
    font-family: 'Outfit', sans-serif !important;
}

/* Logo */
.cs-brand {
    display: flex;
    align-items: center;
    gap: 12px;
    white-space: nowrap;
}

.cs-brand-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    line-height: 1;
}

.cs-brand-icon svg {
    width: 60px;
    height: 60px;
}

.cs-brand-name {
    color: var(--text);
    font-family: 'Outfit', sans-serif;
    font-size: clamp(23px, 2vw, 30px);
    font-weight: 700;
    letter-spacing: -0.045em;
}

.cs-brand-ai {
    color: var(--accent);
}

/* Top navigation */
[data-testid="stPageLink"] a {
    text-decoration: none !important;
}

[data-testid="stPageLink"] p,
[data-testid="stPageLink"] span {
    color: #e8f2f0 !important;
    font-size: 22px !important;
    font-weight: 600 !important;
}

[data-testid="stPageLink"] a:hover p,
[data-testid="stPageLink"] a:hover span {
    color: #62D5C8 !important;
}

/* Hero */
.st-key-cs_hero {
    padding: clamp(20px, 3vh, 38px) 0;
}

.st-key-cs_hero [data-testid="stHorizontalBlock"] {
    align-items: center !important;
    gap: clamp(28px, 4vw, 76px) !important;
}

.cs-eyebrow {
    color: var(--accent);
    font-size: 24px;
    font-weight: 700;
    letter-spacing: 0.15em;
    line-height: 1.5;
    margin-bottom: 1.1rem;
}

.cs-title {
    font-family: 'Outfit', sans-serif;
    color: #F5F8F7;
    font-size: clamp(58px, 4.5vw, 70px) !important;
    font-weight: 800;
    letter-spacing: -0.045em;
    line-height: 1.08 !important;
    margin: 0 0 1.5rem;
    max-width: 950px;
}

.cs-description {
    color: var(--muted);
    font-size: clamp(20px, 1.08vw, 18px);
    line-height: 1.6;
    max-width: 640px;
    margin: 0 0 1.2rem;
}

.cs-note {
    color: #91aba5;
    font-size: 18px;
    margin-top: 0.6rem;
}

/* Portrait on the RIGHT */
.cs-image-wrap {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
}

.cs-portrait {
    display: block;
    height: min(75dvh, 750px);
    width: auto;
    max-width: 100%;
    object-fit: contain;
    border-radius: 18px;
    border: 1px solid #284c46;
    box-shadow: 0 18px 60px rgba(0,0,0,0.2);
}

/* Main action */
.stButton > button[kind="primary"] {
    background: var(--accent) !important;
    color: #0c1716 !important;
    border: none !important;
    border-radius: 9px !important;
    min-height: 48px !important;
    font-size: 16px !important;
    font-weight: 650 !important;
    padding: 0.5rem 1.4rem !important;
}

/* Workflow cards */
.cs-section-title {
    font-family: 'Outfit', sans-serif;
    color: var(--text);
    font-size: clamp(22px, 2vw, 29px);
    font-weight: 650;
    letter-spacing: -0.03em;
    margin-bottom: 0.75rem;
}

.cs-card {
    background: var(--surface);
    border: 1px solid #274941;
    border-radius: 14px;
    padding: 1rem 1.2rem;
    min-height: 110px;
}

.cs-card-title {
    color: var(--text);
    font-family: 'Outfit', sans-serif;
    font-size: 21px;
    font-weight: 650;
    margin-bottom: 0.35rem;
}

.cs-card-icon {
    color: var(--accent);
}

.cs-card-desc {
    color: var(--muted);
    font-size: 14px;
    line-height: 1.5;
}

.cs-footer {
    color: #91aba5;
    font-size: 17px;
    margin-top: 0.5rem;
}

/* Small laptop screens */
@media (min-width: 901px) and (max-height: 760px) {
    .st-key-cs_hero {
        padding: 12px 0;
    }

    .cs-portrait {
        height: 43dvh;
    }

    .cs-title {
        font-size: clamp(36px, 3.2vw, 54px);
    }

    .cs-card {
        min-height: 95px;
    }
}

/* Smaller screens can scroll naturally */
@media (max-width: 900px) {
    [data-testid="stMainBlockContainer"],
    .block-container {
        width: calc(100% - 32px) !important;
    }

    .cs-title {
        font-size: clamp(36px, 6vw, 52px);
    }

    .cs-portrait {
        height: auto;
        max-height: 520px;
    }

    .cs-card {
        min-height: 0;
    }
}

/* HEADER ALIGNMENT REFINEMENT */
[data-testid="stMainBlockContainer"],
.block-container {
    padding-top: 2.1rem !important;
    padding-bottom: 0.75rem !important;
}

.cs-brand {
    display: flex;
    align-items: center;
    gap: 11px;
    min-height: 52px;
    white-space: nowrap;
}

.cs-brand-icon {
    color: #62d5c8;
    font-size: 60px;
}

.cs-brand-name {
    color: #f5f8f7;
    font-size: clamp(40px, 3.5vw, 50px);
    font-weight: 700;
}

.cs-brand-ai {
    color: #62d5c8;
}

[data-testid="stPageLink"] a {
    min-height: 42px;
    display: flex;
    align-items: center;
}

.st-key-cs_hero {
    padding-top: 1.1rem !important;
    padding-bottom: 0.65rem !important;
}

</style>
""", unsafe_allow_html=True)


# HEADER — CuSelect-AI with research navigation

brand, discover, validate, decide, settings = (
    st.columns(
        [2.4, 1.15, 1.15, 1.0, 1.15],
        gap="small",
        vertical_alignment="center",
    )
)

with brand:
    st.markdown(
        '<div class="cs-brand">'
        '<span class="cs-brand-icon">'
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'viewBox="0 0 80 80" width="52" height="52" '
        'fill="none" stroke="#62D5C8" stroke-width="4" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M40 5 L70 22.5 L70 57.5 L40 75 '
        'L10 57.5 L10 22.5 Z"/>'
        '<path d="M28 48 L40 29 L53 47" stroke-width="2.8"/>'
        '<circle cx="28" cy="48" r="5.5" fill="#62D5C8"/>'
        '<circle cx="40" cy="29" r="5.5" fill="#62D5C8"/>'
        '<circle cx="53" cy="47" r="5.5" fill="#62D5C8"/>'
        '</svg>'
        '</span>'
        '<span class="cs-brand-name">'
        'CuSelect<span class="cs-brand-ai">-AI</span>'
        '</span></div>',
        unsafe_allow_html=True,
    )

with discover:
    st.page_link(
        "pages/1_Multi_Agent_Design.py",
        label="Discover",
    )

with validate:
    st.page_link(
        "pages/4_DFT_Analysis.py",
        label="Validate",
    )

with decide:
    st.page_link(
        "pages/3_Research_Cycle_Dashboard.py",
        label="Decide",
    )


with settings:
    st.page_link(
        "pages/6_Settings.py",
        label="Settings",
    )


# HERO: TEXT LEFT, IMAGE RIGHT
with st.container(key="cs_hero"):
    left, right = st.columns(
        [1.12, 0.88],
        gap="large",
        vertical_alignment="center",
    )

    with left:
        st.markdown(
            '<div class="cs-eyebrow">'
            'SCIENTIFIC AI FOR ELECTROCHEMISTRY'
            '</div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            '<h1 class="cs-title">'
            'Discover, validate and decide '
            'on better catalysts.'
            '</h1>',
            unsafe_allow_html=True,
        )

        st.markdown(
            '<p class="cs-description">'
            'An evidence-grounded scientific AI platform '
            'for Cu-based CO₂ electroreduction, integrating '
            'multi-agent reasoning, literature intelligence '
            'and computational validation.'
            '</p>',
            unsafe_allow_html=True,
        )

        if st.button("Start discovery →", type="primary"):
            st.switch_page(
                "pages/1_Multi_Agent_Design.py"
            )

        st.markdown(
            '<div class="cs-note">'
            'Research prototype · Human scientific review required'
            '</div>',
            unsafe_allow_html=True,
        )

    with right:
        if HERO.exists():
            mime = (
                "image/png" if HERO.suffix.lower() == ".png"
                else "image/jpeg"
            )
            encoded = base64.b64encode(
                HERO.read_bytes()
            ).decode("ascii")

            st.markdown(
                '<div class="cs-image-wrap">'
                '<img class="cs-portrait" '
                'src="data:' + mime + ';base64,' + encoded + '" '
                'alt="Conceptual copper catalyst visualization">'
                '</div>',
                unsafe_allow_html=True,
            )
        else:
            st.warning("Catalyst illustration not found.")


# FOOTER
st.markdown(
    '<div class="cs-footer">'
    'CuSelect-AI · Scientific Catalyst Discovery · '
    'Unvalidated predictions are not experimental evidence.'
    '</div>',
    unsafe_allow_html=True,
)


st.markdown(
    """
    <div style="
        margin-top: 12px;
        color: #a5c2be;
        font-size: 16px;
        text-align: left;
    ">
        Created by <strong style="color: #f4f8f6;">
        Bright Nsolebna Jaato</strong>
        &nbsp;|&nbsp; Scientific AI for Electrochemistry
    </div>
    """,
    unsafe_allow_html=True,
)
