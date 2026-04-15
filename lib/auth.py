"""
Streamlit Authentication with Supabase
Handles user login, signup, and session management
"""

import streamlit as st
from lib.supabase_client import get_supabase_client
import logging

logger = logging.getLogger(__name__)

def init_auth_session():
    """Initialize authentication session state"""
    if "user" not in st.session_state:
        st.session_state.user = None
    if "session" not in st.session_state:
        st.session_state.session = None
    if "auth_error" not in st.session_state:
        st.session_state.auth_error = None

def show_auth_page():
    """Display login/signup page"""
    st.set_page_config(
        page_title="TradeIQ - Paper Trading",
        layout="centered"
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("https://via.placeholder.com/200x60?text=TradeIQ", use_container_width=True)
        st.title("Paper Trading System")
        st.divider()

        # Tabs for login/signup
        tab_login, tab_signup = st.tabs(["🔓 Sign In", "📝 Sign Up"])

        with tab_login:
            st.subheader("Welcome Back")

            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")

            if st.button("Sign In", use_container_width=True, type="primary"):
                if email and password:
                    try:
                        supabase = get_supabase_client()
                        response = supabase.client.auth.sign_in_with_password({
                            "email": email,
                            "password": password
                        })

                        st.session_state.user = response.user
                        st.session_state.session = response.session
                        st.session_state.auth_error = None

                        logger.info(f"User signed in: {email}")
                        st.success("✅ Signed in successfully!")
                        st.rerun()

                    except Exception as e:
                        error_msg = str(e)
                        st.session_state.auth_error = error_msg
                        st.error(f"❌ Sign in failed: {error_msg}")
                        logger.error(f"Sign in error: {e}")
                else:
                    st.warning("⚠️ Please enter email and password")

        with tab_signup:
            st.subheader("Create Account")

            new_email = st.text_input("Email", key="signup_email")
            new_password = st.text_input(
                "Password (min 6 chars)",
                type="password",
                key="signup_password"
            )
            confirm_password = st.text_input(
                "Confirm Password",
                type="password",
                key="confirm_password"
            )

            if st.button("Sign Up", use_container_width=True, type="primary"):
                if not new_email or not new_password:
                    st.warning("⚠️ Please enter email and password")
                elif new_password != confirm_password:
                    st.error("❌ Passwords don't match")
                elif len(new_password) < 6:
                    st.error("❌ Password must be at least 6 characters")
                else:
                    try:
                        supabase = get_supabase_client()
                        response = supabase.client.auth.sign_up({
                            "email": new_email,
                            "password": new_password
                        })

                        st.success("✅ Account created! Please sign in.")
                        logger.info(f"New user signed up: {new_email}")

                    except Exception as e:
                        error_msg = str(e)
                        if "already registered" in error_msg.lower():
                            st.error("❌ Email already registered")
                        else:
                            st.error(f"❌ Sign up failed: {error_msg}")
                        logger.error(f"Sign up error: {e}")

        st.divider()
        st.caption("🔐 Your data is encrypted and secure. No trading credentials stored.")

def show_logout_button():
    """Show logout button in sidebar"""
    with st.sidebar:
        st.divider()
        col1, col2 = st.columns([3, 1])
        with col1:
            st.caption(f"👤 {st.session_state.user.email}")
        with col2:
            if st.button("🚪", help="Sign out", key="logout_btn"):
                try:
                    supabase = get_supabase_client()
                    supabase.client.auth.sign_out()

                    st.session_state.user = None
                    st.session_state.session = None
                    st.session_state.auth_error = None

                    logger.info("User signed out")
                    st.success("✅ Signed out!")
                    st.rerun()

                except Exception as e:
                    st.error(f"❌ Logout failed: {e}")
                    logger.error(f"Logout error: {e}")

def require_login():
    """Require user to be logged in. Call this at start of main content."""
    init_auth_session()

    if not st.session_state.user:
        show_auth_page()
        return False
    else:
        return True

def get_current_user_id() -> str:
    """Get current logged-in user ID"""
    if st.session_state.user:
        return st.session_state.user.id
    return None
