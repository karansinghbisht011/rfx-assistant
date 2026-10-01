import streamlit as st

from app.services.catalogue_service import Catalogue, CatalogueError
from app.services.gemini_client import GeminiClient, get_client


@st.cache_resource(show_spinner=False)
def get_catalogue() -> Catalogue:
    return Catalogue.load()


def load_catalogue_or_none() -> Catalogue | None:
    try:
        return get_catalogue()
    except CatalogueError:
        return None


@st.cache_resource(show_spinner=False)
def client() -> GeminiClient:
    return get_client()


@st.cache_data(show_spinner=False)
def suggestions(phrase: str, limit: int = 6):
    """Close catalogue matches for some words, cached because every table row asks for them."""
    return get_catalogue().shortlist([phrase], limit=limit)
