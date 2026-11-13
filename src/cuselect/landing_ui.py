"""CuSelect-AI landing page — compact scientific design."""

import base64
from pathlib import Path

import streamlit as st

from .i18n import current_language

_LANDING_TRANSLATIONS = {
    "de": {
        "About": "Über uns",
        "Research": "Forschung",
        "Documentation": "Dokumentation",
        "SCIENTIFIC AI FOR ELECTROCHEMISTRY":
            "WISSENSCHAFTLICHE KI FÜR ELEKTROCHEMIE",
        "Discover what's": "Entdecken Sie, was",
        "possible in": "in der Katalyse",
        "catalysis.": "möglich ist.",
        "Evidence-grounded AI for exploring catalysts, evaluating hypotheses":
            "Evidenzbasierte KI zur Erforschung von Katalysatoren und Bewertung von Hypothesen",
        "and designing scientific investigations.":
            "sowie zur Planung wissenschaftlicher Untersuchungen.",
        "Explore CuSelect-AI": "CuSelect-AI entdecken",
        "Research prototype": "Forschungsprototyp",
        "Human scientific review required":
            "Wissenschaftliche Prüfung durch Fachleute erforderlich",
        "Exploring catalytic interfaces":
            "Katalytische Grenzflächen erforschen",
        "Conceptual visualization": "Konzeptionelle Visualisierung",
        "Not validated scientific evidence":
            "Keine validierten wissenschaftlichen Belege",
    },
    "es": {
        "About": "Acerca de",
        "Research": "Investigación",
        "Documentation": "Documentación",
        "SCIENTIFIC AI FOR ELECTROCHEMISTRY":
            "IA CIENTÍFICA PARA ELECTROQUÍMICA",
        "Discover what's": "Descubre lo que es",
        "possible in": "posible en la",
        "catalysis.": "catálisis.",
        "Evidence-grounded AI for exploring catalysts, evaluating hypotheses":
            "IA basada en evidencia para explorar catalizadores y evaluar hipótesis",
        "and designing scientific investigations.":
            "y diseñar investigaciones científicas.",
        "Explore CuSelect-AI": "Explorar CuSelect-AI",
        "Research prototype": "Prototipo de investigación",
        "Human scientific review required":
            "Requiere revisión científica humana",
        "Exploring catalytic interfaces":
            "Explorando interfaces catalíticas",
        "Conceptual visualization": "Visualización conceptual",
        "Not validated scientific evidence":
            "No constituye evidencia científica validada",
    },
    "fr": {
        "About": "À propos",
        "Research": "Recherche",
        "Documentation": "Documentation",
        "SCIENTIFIC AI FOR ELECTROCHEMISTRY":
            "IA SCIENTIFIQUE POUR L'ÉLECTROCHIMIE",
        "Discover what's": "Découvrez ce qui est",
        "possible in": "possible en",
        "catalysis.": "catalyse.",
        "Evidence-grounded AI for exploring catalysts, evaluating hypotheses":
            "Une IA fondée sur des preuves pour explorer les catalyseurs et évaluer les hypothèses",
        "and designing scientific investigations.":
            "et concevoir des études scientifiques.",
        "Explore CuSelect-AI": "Explorer CuSelect-AI",
        "Research prototype": "Prototype de recherche",
        "Human scientific review required":
            "Évaluation scientifique humaine requise",
        "Exploring catalytic interfaces":
            "Exploration des interfaces catalytiques",
        "Conceptual visualization": "Visualisation conceptuelle",
        "Not validated scientific evidence":
            "Pas de preuve scientifique validée",
    },
}


def _landing_text(value):
    if not isinstance(value, str):
        return value
    language = current_language()
    if language == "en":
        return value
    translations = _LANDING_TRANSLATIONS.get(language, {})
    for english, translated in sorted(
        translations.items(), key=lambda item: -len(item[0])
    ):
        value = value.replace(english, translated)
    return value


def _landing_markdown(value, *args, **kwargs):
    return st.markdown(_landing_text(value), *args, **kwargs)


def _landing_caption(value, *args, **kwargs):
    return st.caption(_landing_text(value), *args, **kwargs)

from .i18n import render_language_selector


ROOT = Path(__file__).resolve().parents[2]
IMAGE_PATH = ROOT / "assets" / "cuselect_hero.png"


def show_public_research():
    st.session_state["public_page"] = "research"


def enter_workspace():
    """Authenticate before entering the research workspace."""
    st.login("google")


def render_landing():
    # PSEUDOCODE
    # 1. Display a compact product header.
    # 2. Present the scientific introduction on the left.
    # 3. Present the catalyst artwork on the right.
    # 4. Keep navigation clickable.
    # 5. Preserve the existing research application.

    _landing_markdown("""
    <style>
    [data-testid="stAppViewContainer"] {
        background: #101718;
        color: #f8f9f8;
    }

    [data-testid="stHeader"] {
        background: transparent;
    }

    [data-testid="stSidebar"] {
        display: none;
    }

    .block-container {
        max-width: 1450px;
        padding-top: 1rem;
        padding-bottom: 2rem;
    }

    .brand {
        color: #ffffff;
        font-size: 1.4rem;
        font-weight: 750;
        letter-spacing: -.035em;
        padding-top: 7px;
    }

    .brand span {
        color: #68d4c8;
        margin-right: 8px;
    }

    .header-rule {
        border-top: 1px solid #345052;
        margin-top: .65rem;
    }

    .hero-kicker {
        color: #70d8cd;
        font-size: .75rem;
        letter-spacing: .13em;
        font-weight: 750;
        margin-bottom: 1.2rem;
    }

    .hero-title {
        color: #ffffff;
        font-family: Arial, Helvetica, sans-serif;
        font-weight: 780;
        font-size: clamp(2.4rem, 3.6vw, 4.1rem);
        line-height: 1.11;
        letter-spacing: -.045em;
        margin-bottom: 1.2rem;
    }

    .hero-description {
        color: #c0cccc;
        font-size: 1.04rem;
        line-height: 1.7;
        max-width: 500px;
        margin-bottom: 1.3rem;
    }

    .hero-note {
        margin-top: 1.4rem;
        color: #98b0b1;
        font-size: .83rem;
        line-height: 1.65;
    }

    .hero-visual {
        position: relative;
        height: 560px;
        overflow: hidden;
        border-radius: 22px;
        background: #172326;
        border: 1px solid #3c5658;
    }

    .hero-visual img {
        display: block;
        width: 100%;
        height: 100%;
        object-fit: cover;
        object-position: 58% center;
    }

    .hero-visual::after {
        content: "";
        position: absolute;
        inset: 0;
        background: linear-gradient(
            to top,
            rgba(5, 12, 16, .82),
            transparent 45%
        );
        pointer-events: none;
    }

    .hero-caption {
        position: absolute;
        bottom: 25px;
        left: 26px;
        right: 26px;
        z-index: 1;
        color: white;
        font-size: .92rem;
        font-weight: 650;
    }

    .hero-caption small {
        display: block;
        font-size: .73rem;
        font-weight: 400;
        color: #c7d5d6;
        margin-top: 7px;
    }

    div.stButton > button[kind="primary"] {
        background: #6bd7ca;
        border-color: #6bd7ca;
        color: #102326;
        border-radius: 9px;
        font-weight: 700;
        padding: .7rem 1.6rem;
        min-height: 3rem;
    }

    div.stButton > button[kind="primary"]:hover {
        background: #9be8de;
        border-color: #9be8de;
        color: #102326;
    }

    @media(max-width: 768px) {
        .hero-visual {
            height: 330px;
        }

        .hero-title {
            font-size: 2.5rem;
        }
    }

    /* Dark, minimal header navigation */
    [data-testid="stPopover"] button,
    div.stButton > button[kind="secondary"] {
        background: transparent !important;
        color: #c7d3d3 !important;
        border: 1px solid transparent !important;
        box-shadow: none !important;
        border-radius: 8px !important;
        padding: 0.45rem 0.65rem !important;
        font-weight: 500 !important;
    }

    [data-testid="stPopover"] button:hover,
    div.stButton > button[kind="secondary"]:hover {
        background: #203034 !important;
        color: #ffffff !important;
        border-color: #344c50 !important;
    }

    [data-testid="stPopover"] button:focus-visible,
    div.stButton > button[kind="secondary"]:focus-visible {
        outline: 2px solid #6bd7ca !important;
        outline-offset: 2px;
    }
    </style>
    """, unsafe_allow_html=True)

    # Multilingual interface selector
    language_space, language_column = st.columns([8, 2])
    with language_column:
        render_language_selector()


    logo, about, research, docs = st.columns(
        [4.5, 0.9, 1, 1.5],
        vertical_alignment="center",
    )

    with logo:
        _landing_markdown(
            '<div class="brand"><span>⌬</span>'
            'CuSelect-AI</div>',
            unsafe_allow_html=True,
        )

    with about:
        with st.popover(_landing_text("About")):
            st.write(
                "CuSelect-AI explores scientific evidence "
                "and research hypotheses for electrochemical "
                "CO₂ reduction."
            )
            _landing_caption("Scientific research prototype")

    with research:
        st.button(
            "Research",
            key="landing_research_nav",
            on_click=show_public_research,
        )

    with docs:
        with st.popover(_landing_text("Documentation")):
            st.write(
                "Scientific records, provenance checks and "
                "research audits are available inside "
                "the research workspace."
            )

    _landing_markdown(
        '<div class="header-rule"></div>',
        unsafe_allow_html=True,
    )

    st.write("")
    st.write("")

    left, right = st.columns(
        [1.02, 1.12],
        gap="large",
        vertical_alignment="center",
    )

    with left:
        _landing_markdown("""
        <div class="hero-kicker">
            SCIENTIFIC AI FOR ELECTROCHEMISTRY
        </div>

        <div class="hero-title">
            Discover what's<br>
            possible in catalysis.
        </div>

        <div class="hero-description">
            Evidence-grounded AI for exploring catalysts,
            evaluating hypotheses and designing scientific
            investigations.
        </div>
        """, unsafe_allow_html=True)

        st.button(
            _landing_text("Explore CuSelect-AI →"),
            type="primary",
            key="landing_explore",
            on_click=enter_workspace,
        )

        _landing_markdown("""
        <div class="hero-note">
            Research prototype · Human scientific review required
        </div>
        """, unsafe_allow_html=True)

    with right:
        if IMAGE_PATH.is_file():
            encoded = base64.b64encode(
                IMAGE_PATH.read_bytes()
            ).decode("ascii")

            _landing_markdown(
                '<div class="hero-visual">'
                '<img src="data:image/png;base64,'
                + encoded
                + '" alt="Conceptual electrocatalyst interface">'
                '<div class="hero-caption">'
                'Exploring catalytic interfaces'
                '<small>Conceptual visualization · '
                'Not validated scientific evidence</small>'
                '</div></div>',
                unsafe_allow_html=True,
            )
        else:
            st.warning(
                "Hero image missing: assets/cuselect_hero.png"
            )
