"""Streamlit login / register gate. Returns the logged-in user dict, or None while unauthenticated."""

import streamlit as st

from travel_agent.auth import AuthError, UserStore


@st.cache_resource
def _user_store() -> UserStore:
    return UserStore()


def _logout():
    for key in ("auth_user", "thread_id", "reports"):
        st.session_state.pop(key, None)


def current_user() -> dict | None:
    """Render the login screen when logged out; otherwise return the authenticated user."""
    users = _user_store()
    if user := st.session_state.get("auth_user"):
        return user

    st.markdown("<h1 style='text-align:center'>🇮🇳 TripMate AI</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p style='text-align:center;color:#6b7385'>Your multi-agent travel planner for trips within India.<br>"
        "Sign in or create an account to start planning.</p>",
        unsafe_allow_html=True,
    )
    _, center, _ = st.columns([1, 1.3, 1])
    with center:
        login_tab, register_tab = st.tabs(["🔑 Login", "📝 Create account"])

        with login_tab:
            with st.form("login_form"):
                username = st.text_input("Username", key="login_user")
                password = st.text_input("Password", type="password", key="login_pw")
                if st.form_submit_button("Login", use_container_width=True, type="primary"):
                    try:
                        st.session_state.auth_user = users.authenticate(username, password)
                        st.rerun()
                    except AuthError as exc:
                        st.error(str(exc))

        with register_tab:
            with st.form("register_form"):
                full_name = st.text_input("Full name (optional)", key="reg_name")
                new_user = st.text_input("Choose a username", key="reg_user",
                                         help="3-30 characters: letters, numbers, dot, dash or underscore.")
                new_pw = st.text_input("Choose a password", type="password", key="reg_pw",
                                       help="At least 6 characters.")
                confirm = st.text_input("Confirm password", type="password", key="reg_pw2")
                if st.form_submit_button("Create account", use_container_width=True, type="primary"):
                    if new_pw != confirm:
                        st.error("Passwords do not match.")
                    else:
                        try:
                            users.register(new_user, new_pw, full_name)
                            st.session_state.auth_user = users.authenticate(new_user, new_pw)
                            st.success("Account created! Signing you in...")
                            st.rerun()
                        except AuthError as exc:
                            st.error(str(exc))

        st.caption("🔒 Passwords are salted and hashed; they are never stored in plain text.")
    return None


def sidebar_account():
    """Show the signed-in user and a logout button. Call inside `with st.sidebar`."""
    user = st.session_state.get("auth_user", {})
    name = user.get("full_name") or user.get("username", "")
    st.markdown(f"👤 Signed in as **{name}**  \n`@{user.get('username', '')}`")
    if st.button("Log out", use_container_width=True):
        _logout()
        st.rerun()
