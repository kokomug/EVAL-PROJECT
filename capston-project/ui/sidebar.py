import streamlit as st
from auth import signout_user

def create_sidebar():
    # Logo and university name
    st.sidebar.image('assets/logo.png', use_container_width=True)
    st.sidebar.markdown('<div style="text-align:center; font-size:18px; font-weight:bold; margin-bottom:0.5em; color:#1976D2;">BAU</div>', unsafe_allow_html=True)
    st.sidebar.markdown('<div style="text-align:center; font-size:14px; color:#1976D2; letter-spacing:1px; margin-bottom:1.5em;">BAHÇEŞEHİR ÜNİVERSİTESİ</div>', unsafe_allow_html=True)
    st.sidebar.markdown('---')
    if st.session_state.is_authenticated:
        st.sidebar.markdown(f'<div style="color:#31333F; font-size:15px; margin-bottom:0.5em;">👤 <b>{st.session_state.user.email}</b></div>', unsafe_allow_html=True)
        if st.sidebar.button("Home", use_container_width=True):
            st.session_state.page = "home"
            st.rerun()
        if st.sidebar.button("Sign Out", use_container_width=True):
            signout_user()
            st.session_state.page = "login"
            st.rerun()
    else:
        if st.sidebar.button("Login", use_container_width=True):
            st.session_state.page = "login"
            st.rerun()
        if st.sidebar.button("Sign Up", use_container_width=True):
            st.session_state.page = "signup"
            st.rerun()
    st.sidebar.markdown('---')
    st.sidebar.markdown('<div style="font-size:12px; color:#888; text-align:center;">Powered by Streamlit</div>', unsafe_allow_html=True) 