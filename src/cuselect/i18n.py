"""CuSelect-AI interface translations.

Scientific source records are never modified by this module.
"""

import streamlit as st

DEFAULT_LANGUAGE = "en"

LANGUAGES = {
    "en": "🇬🇧 English",
    "de": "🇩🇪 Deutsch",
    "es": "🇪🇸 Español",
    "fr": "🇫🇷 Français",
}

TRANSLATIONS = {
    "en": {
        "language": "Language",
        "app.title": "CuSelect-AI",
        "nav.home": "Home",
        "nav.literature": "Scientific Literature",
        "nav.catalysts": "Catalyst Explorer",
        "nav.research": "Research Workspace",
        "nav.evidence": "Computational Evidence",
        "nav.prediction": "Prediction",
        "catalyst.title": "Catalyst Explorer",
        "catalyst.view": "Catalyst view",
        "catalyst.structures": "3D structures",
        "catalyst.evidence": "Computational evidence",
        "catalyst.workspace": "Research workspace",
        "catalyst.primary": "Primary structure",
        "catalyst.comparison": "Comparison structure",
        "workspace.title": "Cu(100)–Ag Research Workspace",
        "workspace.overview": "Research Overview",
        "workspace.evidence": "Computational Evidence",
        "workspace.critic": "Critic & Revision",
        "workspace.objective": "Research objective",
        "workspace.hypothesis": "Original catalyst hypothesis",
        "workspace.decision": "Current scientific decision",
        "workspace.revised": "Revised hypothesis",
        "workspace.next": "Next research decision gate",
        "workspace.findings": "Critic findings",
        "workspace.responses": "Revision responses",
        "workspace.experiments": "Proposed experiments",
        "status.pending": "Pending",
        "status.completed": "Completed",
        "status.incomplete": "Incomplete",
        "safety.warning": (
            "Scientific results, source quotations and provenance "
            "remain unchanged when the interface language changes."
        ),
    },
    "de": {
        "language": "Sprache",
        "app.title": "CuSelect-AI",
        "nav.home": "Startseite",
        "nav.literature": "Wissenschaftliche Literatur",
        "nav.catalysts": "Katalysator-Explorer",
        "nav.research": "Forschungsarbeitsbereich",
        "nav.evidence": "Berechnungsergebnisse",
        "nav.prediction": "Vorhersage",
        "catalyst.title": "Katalysator-Explorer",
        "catalyst.view": "Katalysatoransicht",
        "catalyst.structures": "3D-Strukturen",
        "catalyst.evidence": "Berechnungsergebnisse",
        "catalyst.workspace": "Forschungsarbeitsbereich",
        "catalyst.primary": "Primärstruktur",
        "catalyst.comparison": "Vergleichsstruktur",
        "workspace.title": "Cu(100)–Ag Forschungsarbeitsbereich",
        "workspace.overview": "Forschungsübersicht",
        "workspace.evidence": "Berechnungsergebnisse",
        "workspace.critic": "Kritik und Überarbeitung",
        "workspace.objective": "Forschungsziel",
        "workspace.hypothesis": "Ursprüngliche Katalysatorhypothese",
        "workspace.decision": "Aktuelle wissenschaftliche Entscheidung",
        "workspace.revised": "Überarbeitete Hypothese",
        "workspace.next": "Nächster Forschungsschritt",
        "workspace.findings": "Kritikpunkte",
        "workspace.responses": "Antworten auf Kritikpunkte",
        "workspace.experiments": "Vorgeschlagene Experimente",
        "status.pending": "Ausstehend",
        "status.completed": "Abgeschlossen",
        "status.incomplete": "Unvollständig",
        "safety.warning": (
            "Wissenschaftliche Ergebnisse, Originalzitate und "
            "Herkunftsnachweise bleiben unverändert."
        ),
    },
    "es": {
        "language": "Idioma",
        "app.title": "CuSelect-AI",
        "nav.home": "Inicio",
        "nav.literature": "Literatura científica",
        "nav.catalysts": "Explorador de catalizadores",
        "nav.research": "Espacio de investigación",
        "nav.evidence": "Evidencia computacional",
        "nav.prediction": "Predicción",
        "catalyst.title": "Explorador de catalizadores",
        "catalyst.view": "Vista del catalizador",
        "catalyst.structures": "Estructuras 3D",
        "catalyst.evidence": "Evidencia computacional",
        "catalyst.workspace": "Espacio de investigación",
        "catalyst.primary": "Estructura principal",
        "catalyst.comparison": "Estructura de comparación",
        "workspace.title": "Espacio de investigación Cu(100)–Ag",
        "workspace.overview": "Resumen de investigación",
        "workspace.evidence": "Evidencia computacional",
        "workspace.critic": "Crítica y revisión",
        "workspace.objective": "Objetivo de investigación",
        "workspace.hypothesis": "Hipótesis original del catalizador",
        "workspace.decision": "Decisión científica actual",
        "workspace.revised": "Hipótesis revisada",
        "workspace.next": "Siguiente decisión de investigación",
        "workspace.findings": "Observaciones críticas",
        "workspace.responses": "Respuestas a las observaciones",
        "workspace.experiments": "Experimentos propuestos",
        "status.pending": "Pendiente",
        "status.completed": "Completado",
        "status.incomplete": "Incompleto",
        "safety.warning": (
            "Los resultados científicos, las citas originales "
            "y los registros de procedencia permanecen intactos."
        ),
    },
    "fr": {
        "language": "Langue",
        "app.title": "CuSelect-AI",
        "nav.home": "Accueil",
        "nav.literature": "Littérature scientifique",
        "nav.catalysts": "Explorateur de catalyseurs",
        "nav.research": "Espace de recherche",
        "nav.evidence": "Données de calcul",
        "nav.prediction": "Prédiction",
        "catalyst.title": "Explorateur de catalyseurs",
        "catalyst.view": "Vue du catalyseur",
        "catalyst.structures": "Structures 3D",
        "catalyst.evidence": "Données de calcul",
        "catalyst.workspace": "Espace de recherche",
        "catalyst.primary": "Structure principale",
        "catalyst.comparison": "Structure comparative",
        "workspace.title": "Espace de recherche Cu(100)–Ag",
        "workspace.overview": "Vue d'ensemble de la recherche",
        "workspace.evidence": "Données de calcul",
        "workspace.critic": "Critique et révision",
        "workspace.objective": "Objectif de recherche",
        "workspace.hypothesis": "Hypothèse initiale du catalyseur",
        "workspace.decision": "Décision scientifique actuelle",
        "workspace.revised": "Hypothèse révisée",
        "workspace.next": "Prochaine décision de recherche",
        "workspace.findings": "Points critiques",
        "workspace.responses": "Réponses aux critiques",
        "workspace.experiments": "Expériences proposées",
        "status.pending": "En attente",
        "status.completed": "Terminé",
        "status.incomplete": "Incomplet",
        "safety.warning": (
            "Les résultats scientifiques, les citations originales "
            "et les données de provenance restent inchangés."
        ),
    },
}


def translate(key, language=DEFAULT_LANGUAGE):
    """Translate a UI label; fall back to English, then the key."""
    if language not in LANGUAGES:
        language = DEFAULT_LANGUAGE
    return TRANSLATIONS.get(language, {}).get(
        key, TRANSLATIONS[DEFAULT_LANGUAGE].get(key, key)
    )


def current_language():
    """Return the active language for this Streamlit session."""
    language = st.session_state.get("cuselect_language", DEFAULT_LANGUAGE)
    return language if language in LANGUAGES else DEFAULT_LANGUAGE


def t(key):
    """Translate a UI string using the active language."""
    return translate(key, current_language())


def render_language_selector():
    """Display the language selector without manual reruns."""
    st.selectbox(
        "Language / Sprache / Idioma / Langue",
        options=list(LANGUAGES),
        format_func=lambda code: LANGUAGES[code],
        key="cuselect_language",
        label_visibility="collapsed",
    )
