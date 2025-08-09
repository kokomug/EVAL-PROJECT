import streamlit as st

def render_home_page():
    """Render the home page."""
    st.title("AI Exam Generator")
    
    if st.session_state.is_authenticated and st.session_state.page == "home":
        if st.session_state.user_role == "teacher":
            st.session_state.page = "teacher_dashboard"
            st.rerun()
        else:
            st.session_state.page = "student_dashboard"
            st.rerun()
    
    with st.container():
        st.subheader("Welcome to the AI Exam Generator!")
        st.write("This tool uses advanced AI to create personalized educational content to help you learn and test your knowledge.")
    
    st.markdown("--- ")
    col1, col2 = st.columns(2)
    
    with col1:
        with st.container():
            st.subheader("Quiz Generator")
            st.write("""
            Create customized multiple-choice questions on any topic with automatic grading and personalized feedback.
            - Choose any topic
            - Set difficulty level
            - Get AI-powered performance analysis
            """)
            if st.button("Create Quiz", use_container_width=True, key="home_create_quiz"):
                if not st.session_state.is_authenticated:
                    st.session_state.page = "login"
                else:
                    # Teachers are directed to quiz creation, students to their dashboard to take quizzes
                    if st.session_state.user_role == "teacher": 
                        st.session_state.page = "quiz"
                    else:
                        st.session_state.page = "student_dashboard" # Or a specific page listing quizzes
                st.rerun()
    
    with col2:
        with st.container():
            st.subheader("Coding Assignment Generator")
            st.write("""
            Generate interactive programming challenges tailored to your interests and skill level.
            - Get starter code templates
            - AI-powered code evaluation
            - Detailed feedback and improvement suggestions
            """)
            if st.button("Create Assignment", use_container_width=True, key="home_create_assignment"):
                if not st.session_state.is_authenticated:
                    st.session_state.page = "login"
                else:
                    # Teachers are directed to assignment creation, students to their dashboard
                    if st.session_state.user_role == "teacher":
                        st.session_state.page = "coding"
                    else:
                        st.session_state.page = "student_dashboard"
                st.rerun()
    
    st.markdown("--- ")
    if not st.session_state.is_authenticated:
        st.markdown("### Get Started")
        col_login, col_signup = st.columns(2)
        with col_login:
            if st.button("Sign In", use_container_width=True, key="home_signin"):
                st.session_state.page = "login"
                st.rerun()
        with col_signup:
            if st.button("Create Account", use_container_width=True, key="home_signup", type="primary"):
                st.session_state.page = "signup"
                st.rerun()
    
    st.markdown("--- ")
    st.caption("Powered by Groq AI • Uses Llama3-8b-8192") 