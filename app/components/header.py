
import streamlit as st


def render_header():
    """Display the shared CuSelect-AI navigation header."""

    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');

        /* CuSelect-AI branding */
        .cs-brand {
            text-decoration: none !important;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 12px;
            font-family: 'Outfit', sans-serif;
            font-size: 42px;
            font-weight: 700;
            letter-spacing: -0.045em;
            color: #F5F8F7;
            white-space: nowrap;
            min-height: 60px;
        }

        .cs-brand span {
            color: #62D5C8;
        }


        /* Preserve logo colors when the brand is clickable */
        a.cs-brand,
        a.cs-brand:link,
        a.cs-brand:visited,
        a.cs-brand:hover,
        a.cs-brand:active {
            color: #F5F8F7 !important;
            text-decoration: none !important;
        }

        a.cs-brand span {
            color: #62D5C8 !important;
        }

        /* Custom hexagon logo */
        .cs-brand svg {
            width: 52px;
            height: 52px;
            flex-shrink: 0;
        }

        /* Navigation links */
        [data-testid="stPageLink"] p,
        [data-testid="stPageLink"] span {
            font-family: 'Inter', sans-serif !important;
            font-size: 22px !important;
            font-weight: 600 !important;
            color: #F5F8F7 !important;
            white-space: nowrap !important;
        }

        /* Hover effect */
        [data-testid="stPageLink"] a:hover p,
        [data-testid="stPageLink"] a:hover span {
            color: #62D5C8 !important;
        }

        /* Navigation alignment */
        [data-testid="stPageLink"] a {
            display: flex;
            align-items: center;
            min-height: 54px;
            text-decoration: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Shared navigation layout
    brand, discover, validate, decide, settings = st.columns(
        [2.4, 1.15, 1.15, 1.0, 1.15],
        gap="small",
        vertical_alignment="center",
    )

    # Brand logo
    with brand:
        st.markdown(
            '<a class="cs-brand" href="/" target="_self" ''aria-label="Go to CuSelect-AI homepage">'
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'viewBox="0 0 80 80" '
            'fill="none" '
            'stroke="#62D5C8" '
            'stroke-width="4" '
            'stroke-linecap="round" '
            'stroke-linejoin="round">'
            '<path d="M40 5 L70 22.5 L70 57.5 '
            'L40 75 L10 57.5 L10 22.5 Z"/>'
            '<path d="M28 48 L40 29 L53 47" '
            'stroke-width="2.8"/>'
            '<circle cx="28" cy="48" r="5.5" '
            'fill="#62D5C8"/>'
            '<circle cx="40" cy="29" r="5.5" '
            'fill="#62D5C8"/>'
            '<circle cx="53" cy="47" r="5.5" '
            'fill="#62D5C8"/>'
            '</svg>'
            'CuSelect<span>-AI</span>'
            '</a>',
            unsafe_allow_html=True,
        )

    # Discover
    with discover:
        st.page_link(
            "pages/1_Multi_Agent_Design.py",
            label="Discover",
        )

    # Validate
    with validate:
        st.page_link(
            "pages/4_DFT_Analysis.py",
            label="Validate",
        )

    # Decide
    with decide:
        st.page_link(
            "pages/3_Research_Cycle_Dashboard.py",
            label="Decide",
        )


    # Settings
    with settings:
        st.page_link(
            "pages/6_Settings.py",
            label="Settings",
        )
