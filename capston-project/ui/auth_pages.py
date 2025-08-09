import streamlit as st
from auth import signin_user, signup_user # Assuming auth.py is accessible

def render_login_page():
    """Render the login page."""
    st.title("Sign In")
    with st.form("login_form"):
        email = st.text_input("Email:", placeholder="your@email.com")
        password = st.text_input("Password:", type="password")
        
        if st.session_state.get("auth_message"): # Check if message exists
            st.error(st.session_state.auth_message)
            st.session_state.auth_message = "" # Clear after displaying
        
        submit_btn = st.form_submit_button("Sign In", use_container_width=True, type="primary")
        
        if submit_btn:
            if not email or not password:
                st.session_state.auth_message = "Email and password are required."
                st.rerun()

            response = signin_user(email, password)
            if response.get("success"):
                st.session_state.is_authenticated = True
                st.session_state.user = response.get("user")
                st.session_state.user_role = response.get("role")
                st.session_state.auth_message = ""
                if response.get("role") == "teacher":
                    st.session_state.page = "teacher_dashboard"
                else:
                    st.session_state.page = "student_dashboard"
                st.rerun()
            else:
                st.session_state.auth_message = response.get("error", "Login failed. Please try again.")
                st.rerun()
    
    st.markdown("--- ")
    st.write("Don't have an account?")
    if st.button("Create Account", use_container_width=True, key="login_signup_btn"):
        st.session_state.page = "signup"
        st.session_state.auth_message = "" # Clear any previous login error
        st.rerun()

def render_signup_page():
    """Render the signup page."""
    st.title("Create Account")
    with st.form("signup_form"):
        email = st.text_input("Email:", placeholder="your@email.com")
        password = st.text_input("Password:", type="password")
        confirm_password = st.text_input("Confirm Password:", type="password")
        role = st.selectbox("I am a:", ["Student", "Teacher"])
        role_value = role.lower()
        
        if st.session_state.get("auth_message"): # Check if message exists
            st.error(st.session_state.auth_message)
            st.session_state.auth_message = "" # Clear after displaying
        
        submit_btn = st.form_submit_button("Create Account", use_container_width=True, type="primary")
        
        if submit_btn:
            if not email or not password:
                st.session_state.auth_message = "Email and password are required."
            elif password != confirm_password:
                st.session_state.auth_message = "Passwords do not match."
            elif len(password) < 6:
                st.session_state.auth_message = "Password must be at least 6 characters long."
            else:
                response = signup_user(email, password, role_value)
                if response.get("success"):
                    st.session_state.is_authenticated = True
                    st.session_state.user = response.get("user")
                    st.session_state.user_role = response.get("role")
                    st.session_state.auth_message = ""
                    if role_value == "teacher":
                        st.session_state.page = "teacher_dashboard"
                    else:
                        st.session_state.page = "student_dashboard"
                    st.rerun()
                else:
                    st.session_state.auth_message = response.get("error", "Registration failed. Please try again.")
            
            if st.session_state.auth_message: # If any message was set, rerun to display it before next action
                 st.rerun()
    
    st.markdown("--- ")
    st.write("Already have an account?")
    if st.button("Sign In", use_container_width=True, key="signup_login_btn"):
        st.session_state.page = "login"
        st.session_state.auth_message = "" # Clear any previous signup error
        st.rerun() 