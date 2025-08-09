import streamlit as st
import os
from dotenv import load_dotenv

# Custom Modules - Auth is still needed for get_current_user
from auth import get_current_user # Removed signout_user as sidebar handles it

# UI Modules
from ui.shared_ui import setup_page_config
from ui.sidebar import create_sidebar
from ui.home_page import render_home_page
from ui.auth_pages import render_login_page, render_signup_page
from ui.dashboard_pages import render_teacher_dashboard, render_student_dashboard, render_assignment_feedback_page
from ui.quiz_pages import (
    render_quiz_page, 
    render_results_page, 
    render_take_quiz_page, 
    render_quiz_submissions_page
)
from ui.assignment_pages import (
    render_coding_page, 
    render_solve_assignment_page, 
    render_assignment_submissions_page
)

# Load environment variables
load_dotenv()

def main():
    """Main application entry point."""
    # Initialize session state variables
    if "page" not in st.session_state:
        st.session_state.page = "home"
    # Minimal session state, other items are managed by individual page components or their init logic
    # if "questions" not in st.session_state: 
    #     st.session_state.questions = None
    # if "user_answers" not in st.session_state: 
    #     st.session_state.user_answers = {}
    # if "assignment" not in st.session_state: 
    #     st.session_state.assignment = None
    
    if "is_authenticated" not in st.session_state:
        st.session_state.is_authenticated = False
    if "user" not in st.session_state:
        st.session_state.user = None
    if "user_role" not in st.session_state:
        st.session_state.user_role = None
    if "auth_message" not in st.session_state:
        st.session_state.auth_message = ""

    if "view_quiz_id" not in st.session_state:
        st.session_state.view_quiz_id = None
    if "view_assignment_id" not in st.session_state:
        st.session_state.view_assignment_id = None

    setup_page_config()
    
    if not st.session_state.is_authenticated:
        user_info = get_current_user()
        if user_info and user_info.get('success'):
            st.session_state.is_authenticated = True
            st.session_state.user = user_info.get('user')
            st.session_state.user_role = user_info.get('role')

    create_sidebar()
    
    page = st.session_state.get("page", "home")

    if page == "home":
        render_home_page()
    elif page == "login":
        render_login_page()
    elif page == "signup":
        render_signup_page()
    elif page == "teacher_dashboard":
        render_teacher_dashboard()
    elif page == "student_dashboard":
        render_student_dashboard()
    elif page == "quiz":
        render_quiz_page()
    elif page == "results":
        render_results_page()
    elif page == "take_quiz":
        render_take_quiz_page()
    elif page == "quiz_submissions":
        render_quiz_submissions_page()
    elif page == "coding":
        render_coding_page()
    elif page == "solve_assignment":
        render_solve_assignment_page()
    elif page == "assignment_submissions":
        render_assignment_submissions_page()
    elif page == "assignment_feedback":
        render_assignment_feedback_page()
    else:
        st.session_state.page = "home"
        st.rerun()

if __name__ == "__main__":
    main()
