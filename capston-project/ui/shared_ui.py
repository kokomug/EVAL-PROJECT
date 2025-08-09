import streamlit as st

def setup_page_config():
    """Set up the page configuration and styling."""
    st.set_page_config(
        page_title="AI Exam Generator",
        page_icon="🧠",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    # Custom styling removed previously, kept clean here 