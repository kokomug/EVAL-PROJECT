import streamlit as st
import os
import time
from langchain_groq import ChatGroq
from typing import Optional

# List of supported Groq models
GROQ_MODELS = [
    # DeepSeek / Meta
    "deepseek-r1-distill-llama-70b",
    # Alibaba Cloud
    "qwen-qwq-32b",
    # Google
    "gemma2-9b-it",
    # Meta
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",
    "llama-guard-3-8b",
    "llama3-70b-8192",
    "llama3-8b-8192",
    "meta-llama/llama-4-maverick-17b-128e-instruct"
]

# Initialize LLM client
@st.cache_resource
def get_llm(model_name: Optional[str] = None):
    try:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            # This function is now in a service, direct st.error might not be ideal.
            # Consider logging or raising an exception to be handled by the caller.
            print("ERROR: No API key found in .env file. Please add your GROQ_API_KEY to the .env file.")
            # For now, to maintain similar behavior without st access here:
            # raise ValueError("No API key found for Groq.")
            return None # Callers should check for None
        if not model_name:
            model_name = "deepseek-r1-distill-llama-70b"  # Default to DeepSeek
        return ChatGroq(model_name=model_name)
    except Exception as e:
        print(f"Error initializing LLM: {e}")
        # raise ConnectionError(f"Error initializing LLM: {e}")
        return None # Callers should check for None

# Generate content using LLM
def generate_content(prompt: str, show_spinner: bool = True, model_name: Optional[str] = None) -> Optional[str]:
    """Generate content using the LLM with proper error handling."""
    llm = get_llm(model_name)
    if not llm:
        # st.error("LLM initialization failed. Check your API key in the .env file.") # Cannot use st.error here directly
        print("LLM initialization failed. Check your API key.")
        return None
    
    try:
        if show_spinner and 'st' in globals(): # Check if streamlit context is available for spinner
            with st.spinner("Generating content..."):
                start_time = time.time()
                response = llm.invoke(prompt).content
                elapsed = time.time() - start_time
                st.success(f"Generated in {elapsed:.2f} seconds")
            return response
        else:
            # Fallback for non-Streamlit contexts or when spinner is off
            start_time = time.time()
            response = llm.invoke(prompt).content
            elapsed = time.time() - start_time
            print(f"LLM content generated in {elapsed:.2f} seconds (no spinner).")
            return response
    except Exception as e:
        # st.error(f"Error generating content: {str(e)}") # Cannot use st.error here directly
        print(f"Error generating content: {str(e)}")
        return None 