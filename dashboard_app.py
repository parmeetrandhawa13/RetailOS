import math
from textwrap import dedent
from typing import Any

import altair as alt
import pandas as pd
import streamlit as st

from src.auth import (
    authenticate_local_user,
    build_google_user,
    google_auth_available,
    load_access_config,
)
from src.retail_intelligence import (
    PIPELINE_STAGES,
    build_conversion_funnel_proxy,
    build_daily_metrics,
    build_segment_distribution,
    calculate_health_score,
    compute_kpis,
    detect_anomalies,
    evaluate_forecast_accuracy,
    forecast_demand,
    generate_recommendations,
    run_retail_intelligence,
    summarize_countries,
)


st.set_page_config(
    page_title="RetailOS",
    layout="wide",
    initial_sidebar_state="expanded",
)


def inject_styles(theme: str) -> None:
    if theme == "Dark":
        css_variables = """
            --app-bg: #111716;
            --paper: rgba(20, 28, 28, 0.94);
            --paper-soft: rgba(17, 23, 22, 0.9);
            --ink: #f1efe8;
            --muted: #b3bdb9;
            --accent: #f4a261;
            --accent-soft: #e76f51;
            --teal: #70c1b3;
            --line: rgba(241, 239, 232, 0.08);
            --hero-a: rgba(22, 30, 30, 0.96);
            --hero-b: rgba(25, 67, 64, 0.94);
        """
    else:
        css_variables = """
            --app-bg: #f4efe8;
            --paper: rgba(255, 252, 246, 0.92);
            --paper-soft: rgba(250, 245, 236, 0.92);
            --ink: #1f2a2c;
            --muted: #5c6869;
            --accent: #e76f51;
            --accent-soft: #f4a261;
            --teal: #287271;
            --line: rgba(31, 42, 44, 0.12);
            --hero-a: rgba(31, 42, 44, 0.95);
            --hero-b: rgba(40, 114, 113, 0.92);
        """

    st.markdown(
        f"""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=DM+Sans:wght@400;500;700&display=swap');

            :root {{
                {css_variables}
            }}

            .stApp {{
                background:
                    radial-gradient(circle at top left, rgba(233, 196, 106, 0.18), transparent 28%),
                    radial-gradient(circle at top right, rgba(40, 114, 113, 0.18), transparent 24%),
                    linear-gradient(180deg, var(--app-bg) 0%, color-mix(in srgb, var(--app-bg) 88%, #000 12%) 100%);
                color: var(--ink);
                font-family: "DM Sans", sans-serif;
            }}

            .block-container {{
                max-width: 1340px;
                padding-top: 1.8rem;
                padding-bottom: 3rem;
            }}

            h1, h2, h3 {{
                font-family: "Space Grotesk", sans-serif;
                letter-spacing: -0.03em;
                color: var(--ink);
            }}

            @keyframes rise {{
                from {{
                    opacity: 0;
                    transform: translateY(10px);
                }}
                to {{
                    opacity: 1;
                    transform: translateY(0);
                }}
            }}

            .hero, .metric-card, .surface-card, .alert-card {{
                animation: rise 0.45s ease-out;
            }}

            .auth-shell {{
                max-width: 980px;
                margin: 0 auto;
                display: grid;
                grid-template-columns: 1.1fr 0.9fr;
                gap: 1rem;
                align-items: stretch;
            }}

            .auth-panel {{
                padding: 1.6rem 1.7rem;
                border-radius: 26px;
                background: var(--paper);
                border: 1px solid var(--line);
                box-shadow: 0 22px 48px rgba(0, 0, 0, 0.1);
            }}

            .auth-lead {{
                color: var(--muted);
                max-width: 54ch;
                margin-bottom: 1rem;
            }}

            .auth-kpi-grid {{
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 0.75rem;
                margin-top: 1.2rem;
            }}

            .auth-kpi {{
                padding: 0.9rem 1rem;
                border-radius: 18px;
                background: color-mix(in srgb, var(--paper-soft) 92%, var(--accent-soft) 8%);
                border: 1px solid var(--line);
            }}

            .auth-kpi strong {{
                display: block;
                font-family: "Space Grotesk", sans-serif;
                font-size: 1.15rem;
                color: var(--ink);
            }}

            .auth-kpi span {{
                font-size: 0.88rem;
                color: var(--muted);
            }}

            .setup-note {{
                padding: 1rem 1.1rem;
                border-radius: 18px;
                background: color-mix(in srgb, var(--paper-soft) 84%, var(--accent) 16%);
                border: 1px solid var(--line);
                color: var(--ink);
            }}

            .toolbar {{
                display: flex;
                justify-content: space-between;
                gap: 1rem;
                align-items: center;
                margin: 0.2rem 0 1rem;
                padding: 0.8rem 1rem;
                border-radius: 18px;
                background: color-mix(in srgb, var(--paper-soft) 92%, transparent);
                border: 1px solid var(--line);
            }}

            .toolbar-copy {{
                color: var(--muted);
                font-size: 0.92rem;
            }}

            div[data-testid="stFormSubmitButton"] button {{
                color: #fff8ef !important;
                font-weight: 700;
            }}

            .hero {{
                padding: 1.7rem 1.9rem;
                border-radius: 28px;
                background:
                    linear-gradient(135deg, var(--hero-a), var(--hero-b)),
                    linear-gradient(45deg, rgba(231, 111, 81, 0.12), transparent);
                color: #fff8ef;
                border: 1px solid rgba(255, 255, 255, 0.08);
                box-shadow: 0 30px 60px rgba(0, 0, 0, 0.18);
            }}

            .hero-kicker {{
                text-transform: uppercase;
                letter-spacing: 0.24em;
                font-size: 0.74rem;
                opacity: 0.72;
                margin-bottom: 0.6rem;
            }}

            .hero-title {{
                font-family: "Space Grotesk", sans-serif;
                font-size: clamp(2.1rem, 5vw, 4rem);
                line-height: 1.02;
                margin: 0;
                max-width: 15ch;
            }}

            .hero-copy {{
                margin-top: 1rem;
                max-width: 64ch;
                color: rgba(255, 248, 239, 0.88);
                font-size: 1rem;
            }}

            .hero-chip-row {{
                display: flex;
                flex-wrap: wrap;
                gap: 0.65rem;
                margin-top: 1.25rem;
            }}

            .hero-chip {{
                padding: 0.45rem 0.8rem;
                border-radius: 999px;
                background: rgba(255, 255, 255, 0.12);
                border: 1px solid rgba(255, 255, 255, 0.1);
                font-size: 0.85rem;
            }}

            .status-grid {{
                display: grid;
                grid-template-columns: repeat(3, minmax(0, 1fr));
                gap: 0.75rem;
                margin-top: 1rem;
            }}

            .status-tile {{
                padding: 0.95rem 1rem;
                border-radius: 18px;
                background: var(--paper-soft);
                border: 1px solid var(--line);
            }}

            .status-label, .metric-label {{
                color: var(--muted);
                font-size: 0.82rem;
                text-transform: uppercase;
                letter-spacing: 0.12em;
            }}

            .status-value {{
                font-family: "Space Grotesk", sans-serif;
                font-size: 1.25rem;
                margin-top: 0.35rem;
                color: var(--ink);
            }}

            .metric-card, .surface-card, .alert-card {{
                background: var(--paper);
                border-radius: 22px;
                padding: 1rem 1.1rem;
                border: 1px solid var(--line);
                box-shadow: 0 18px 36px rgba(0, 0, 0, 0.08);
            }}

            .metric-card {{
                min-height: 150px;
            }}

            .metric-value {{
                font-family: "Space Grotesk", sans-serif;
                font-size: 2rem;
                color: var(--ink);
                margin-top: 0.35rem;
            }}

            .metric-delta {{
                margin-top: 0.6rem;
                font-size: 0.92rem;
                color: var(--teal);
            }}

            .metric-note, .section-copy {{
                color: var(--muted);
                margin-top: 0.45rem;
                font-size: 0.92rem;
            }}

            .section-copy {{
                max-width: 74ch;
                margin-bottom: 1rem;
            }}

            .surface-card {{
                min-height: 100%;
            }}

            .section-panel {{
                background: var(--paper);
                border: 1px solid var(--line);
                border-radius: 22px;
                padding: 1rem 1.1rem;
                box-shadow: 0 18px 36px rgba(0, 0, 0, 0.08);
            }}

            .mini-badge {{
                display: inline-block;
                padding: 0.2rem 0.55rem;
                border-radius: 999px;
                background: rgba(244, 162, 97, 0.16);
                color: var(--accent);
                font-size: 0.8rem;
                margin-bottom: 0.7rem;
            }}

            .pipeline-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 0.7rem;
                margin-top: 0.8rem;
            }}

            .pipeline-stage {{
                background: var(--paper);
                border: 1px solid var(--line);
                border-radius: 18px;
                padding: 0.85rem;
                min-height: 110px;
            }}

            .pipeline-index {{
                width: 34px;
                height: 34px;
                border-radius: 999px;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                background: linear-gradient(135deg, var(--accent), var(--accent-soft));
                color: #fff;
                font-family: "Space Grotesk", sans-serif;
                margin-bottom: 0.6rem;
            }}

            .pipeline-name {{
                font-family: "Space Grotesk", sans-serif;
                font-size: 1rem;
                margin-bottom: 0.3rem;
                color: var(--ink);
            }}

            .pipeline-copy {{
                color: var(--muted);
                font-size: 0.88rem;
                line-height: 1.35;
            }}

            .health-ring {{
                display: flex;
                align-items: center;
                justify-content: center;
                width: 186px;
                height: 186px;
                margin: 0 auto 0.8rem;
                border-radius: 50%;
                background: conic-gradient(var(--teal) calc(var(--score) * 1%), rgba(148, 163, 163, 0.18) 0);
                position: relative;
            }}

            .health-ring::after {{
                content: "";
                position: absolute;
                width: 138px;
                height: 138px;
                border-radius: 50%;
                background: color-mix(in srgb, var(--paper) 92%, transparent);
                box-shadow: inset 0 0 0 1px var(--line);
            }}

            .health-ring-value {{
                position: relative;
                z-index: 1;
                text-align: center;
                color: var(--ink);
            }}

            .health-ring-number {{
                font-family: "Space Grotesk", sans-serif;
                font-size: 2.8rem;
                line-height: 1;
            }}

            .alert-card {{
                min-height: 158px;
                background: linear-gradient(180deg, var(--paper), color-mix(in srgb, var(--paper) 84%, var(--accent-soft) 16%));
            }}

            .priority-pill {{
                display: inline-block;
                padding: 0.22rem 0.55rem;
                border-radius: 999px;
                background: rgba(40, 114, 113, 0.12);
                color: var(--teal);
                font-size: 0.8rem;
                margin-bottom: 0.7rem;
            }}

            div[data-testid="stDataFrame"] {{
                border: 1px solid var(--line);
                border-radius: 18px;
                overflow: hidden;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def format_currency(value: float) -> str:
    return f"${value:,.0f}"


def format_indian_number(value: float, decimals: int = 0) -> str:
    sign = "-" if value < 0 else ""
    value = abs(float(value))
    rounded = f"{value:.{decimals}f}"
    integer_part, _, fraction_part = rounded.partition(".")
    if len(integer_part) > 3:
        last_three = integer_part[-3:]
        remaining = integer_part[:-3]
        groups = []
        while len(remaining) > 2:
            groups.insert(0, remaining[-2:])
            remaining = remaining[:-2]
        if remaining:
            groups.insert(0, remaining)
        integer_part = ",".join(groups + [last_three])
    formatted = sign + integer_part
    if decimals > 0:
        formatted += f".{fraction_part}"
    return formatted


def format_money(value: float, market_view: str = "India", compact: bool = False) -> str:
    if market_view == "India":
        absolute = abs(float(value))
        if compact:
            if absolute >= 10_000_000:
                return f"Rs. {value / 10_000_000:.2f} Cr"
            if absolute >= 100_000:
                return f"Rs. {value / 100_000:.2f} L"
            if absolute >= 1_000:
                return f"Rs. {value / 1_000:.1f} K"
        return f"Rs. {format_indian_number(value, 0)}"
    if compact:
        return format_compact(value)
    return format_currency(value)


def format_compact(value: float) -> str:
    absolute = abs(value)
    if absolute >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    if absolute >= 1_000:
        return f"${value / 1_000:.1f}K"
    return f"${value:,.0f}"


def format_percent(value: float) -> str:
    return f"{value:.1f}%"


def format_count(value: float, market_view: str = "India") -> str:
    if market_view == "India":
        return format_indian_number(value, 0)
    return f"{int(value):,}"


def load_artifacts(source: Any):
    return run_retail_intelligence(source)


def _ensure_auth_state() -> None:
    st.session_state.setdefault("auth_status", False)
    st.session_state.setdefault("auth_user", "")
    st.session_state.setdefault("auth_name", "")
    st.session_state.setdefault("auth_role", "viewer")
    st.session_state.setdefault("auth_source", "local")


def _current_role() -> str:
    return st.session_state.get("auth_role", "viewer")


def _role_allows_upload() -> bool:
    return _current_role() == "admin"


def _role_allows_download() -> bool:
    return _current_role() in {"admin", "analyst"}


def _role_label() -> str:
    role = _current_role()
    return role.capitalize()


def _streamlit_identity() -> Any:
    return getattr(st, "user", getattr(st, "experimental_user", None))


def _streamlit_login(provider: str) -> None:
    if hasattr(st, "login"):
        st.login(provider)
        return
    if hasattr(st, "experimental_login"):
        st.experimental_login(provider)
        return
    raise RuntimeError("This Streamlit version does not support native login.")


def _streamlit_logout() -> None:
    if hasattr(st, "logout"):
        st.logout()
        return
    if hasattr(st, "experimental_logout"):
        st.experimental_logout()
        return


def _hydrate_google_session(access_config) -> bool:
    identity = _streamlit_identity()
    if identity is None or not getattr(identity, "is_logged_in", False):
        return False

    google_user = build_google_user(identity, access_config)
    if google_user is None:
        return False

    st.session_state["auth_status"] = True
    st.session_state["auth_user"] = google_user.username
    st.session_state["auth_name"] = google_user.name
    st.session_state["auth_role"] = google_user.role
    st.session_state["auth_source"] = google_user.auth_source
    return True


def _render_auth_setup(theme: str) -> None:
    inject_styles(theme)
    left, right = st.columns([1.15, 0.9], gap="large")
    with left:
        st.markdown(
            """
            <section class="hero">
                <div class="hero-kicker">RetailOS secure access</div>
                <h1 class="hero-title">Authentication is required before analytics can be opened.</h1>
                <p class="hero-copy">
                    The dashboard is now protected by credential-based access. Configure one admin user in Streamlit
                    secrets or environment variables, then sign in normally.
                </p>
                <div class="hero-chip-row">
                    <span class="hero-chip">Session-based login</span>
                    <span class="hero-chip">Password hash supported</span>
                    <span class="hero-chip">Logout control enabled</span>
                </div>
            </section>
            """,
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(
            """
            <section class="auth-panel">
                <div class="mini-badge">Setup required</div>
                <h3>Configure one admin account</h3>
                <p class="auth-lead">
                    RetailOS did not find auth credentials yet, so the app is refusing open access.
                    This is the safer default for deployment.
                </p>
                <div class="setup-note">
                    Add either <code>st.secrets["auth"]</code> or environment variables for
                    <code>RETAILOS_AUTH_USERNAME</code> with a password or password hash.
                </div>
            </section>
            """,
            unsafe_allow_html=True,
        )
    st.code(
        dedent(
            """
            # .streamlit/secrets.toml
            [auth]
            redirect_uri = "http://localhost:8501/oauth2callback"
            cookie_secret = "replace-with-a-long-random-string"

            [auth.google]
            client_id = "your-google-client-id"
            client_secret = "your-google-client-secret"
            server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"

            [access]

            [[access.users]]
            username = "admin"
            name = "Retail Admin"
            role = "admin"
            password = "ChangeMeNow123"

            [[access.users]]
            username = "analyst"
            name = "Operations Analyst"
            role = "analyst"
            password = "Analyse123"

            [[access.users]]
            username = "viewer"
            name = "Business Viewer"
            role = "viewer"
            password = "Viewer123"

            [access.google_roles]
            admin = ["admin@example.com"]
            analyst = ["analyst@example.com"]
            viewer = ["viewer@example.com"]
            """
        ).strip(),
        language="toml",
    )
    st.info(
        "For deployment, prefer `password_hash` instead of a plain password. "
        "Google Sign-In uses Streamlit's native OIDC flow, while local users remain available as a fallback."
    )


def require_authentication(theme: str) -> None:
    _ensure_auth_state()
    access_config = load_access_config(st.secrets)
    google_enabled = google_auth_available(st.secrets)

    if _hydrate_google_session(access_config):
        return

    if access_config is None and not google_enabled:
        _render_auth_setup(theme)
        st.stop()

    if st.session_state["auth_status"]:
        return

    inject_styles(theme)
    auth_copy = (
        "Use Google Sign-In when available, or continue with your assigned RetailOS account."
        if google_enabled
        else "Use your assigned RetailOS account to continue."
    )
    left, right = st.columns([1.15, 0.9], gap="large")
    with left:
        st.markdown(
            """
            <section class="hero">
                <div class="hero-kicker">RetailOS secure retail command centre</div>
                <h1 class="hero-title">Protected access for operators, analysts, and decision makers.</h1>
                <p class="hero-copy">
                    Sign in to open customer segmentation, demand forecasting, anomaly detection,
                    health scoring, and recommendation workflows in one secure workspace.
                </p>
                <div class="auth-kpi-grid">
                    <div class="auth-kpi">
                        <strong>Secure sign-in</strong>
                        <span>Google Sign-In plus fallback credentials for the dashboard</span>
                    </div>
                    <div class="auth-kpi">
                        <strong>Multi-user access</strong>
                        <span>Admins, analysts, and viewers can each have separate credentials</span>
                    </div>
                    <div class="auth-kpi">
                        <strong>India-ready reporting</strong>
                        <span>IST timestamps and lakh/crore presentation remain available after login</span>
                    </div>
                    <div class="auth-kpi">
                        <strong>Role-based controls</strong>
                        <span>Uploads and downloads can be restricted based on user responsibility</span>
                    </div>
                </div>
            </section>
            """,
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(
            f"""
            <section class="auth-panel">
                <div class="mini-badge">Login</div>
                <h3>RetailOS authentication</h3>
                <p class="auth-lead">{auth_copy}</p>
            </section>
            """,
            unsafe_allow_html=True,
        )
        if google_enabled:
            if st.button("Continue with Google", use_container_width=True, type="primary"):
                _streamlit_login("google")
            st.caption("Google accounts are mapped to Admin, Analyst, or Viewer access using configured email rules.")
        else:
            st.button("Continue with Google", use_container_width=True, disabled=True)
            st.caption("Google Sign-In is available in RetailOS but is not configured for this deployment yet.")
        st.markdown("---")
        with st.form("retailos_login_form", clear_on_submit=False):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in with RetailOS account", use_container_width=True)

    if submitted:
        authenticated_user = authenticate_local_user(username.strip(), password, access_config)
        if authenticated_user:
            st.session_state["auth_status"] = True
            st.session_state["auth_user"] = authenticated_user.username
            st.session_state["auth_name"] = authenticated_user.name
            st.session_state["auth_role"] = authenticated_user.role
            st.session_state["auth_source"] = authenticated_user.auth_source
            st.success("Login successful. Opening RetailOS.")
            st.rerun()
        else:
            st.error("The username or password is incorrect.")

    st.stop()


def configure_runtime_controls():
    st.sidebar.markdown("## RetailOS Controls")
    st.sidebar.caption(
        f"Signed in as {st.session_state.get('auth_name') or st.session_state.get('auth_user', 'operator')}"
    )
    st.sidebar.caption(f"Role: {_role_label()}")
    st.sidebar.caption(f"Auth: {st.session_state.get('auth_source', 'local').capitalize()}")
    if st.sidebar.button("Logout", use_container_width=True):
        if st.session_state.get("auth_source") == "google":
            _streamlit_logout()
        st.session_state["auth_status"] = False
        st.session_state["auth_user"] = ""
        st.session_state["auth_name"] = ""
        st.session_state["auth_role"] = "viewer"
        st.session_state["auth_source"] = "local"
        st.rerun()
    source_options = ["Project dataset"]
    if _role_allows_upload():
        source_options.append("Upload custom CSV")
    source_mode = st.sidebar.radio("Data source", options=source_options, index=0)
    uploaded_file = None
    if source_mode == "Upload custom CSV":
        uploaded_file = st.sidebar.file_uploader("Upload retail CSV", type=["csv"])
    else:
        st.sidebar.caption("Using the bundled project dataset from the workspace.")
    if not _role_allows_upload():
        st.sidebar.caption("CSV upload is restricted to admin users.")
    theme = st.sidebar.selectbox("Theme", options=["Light", "Dark"], index=0)
    market_view = st.sidebar.selectbox("Market view", options=["India", "Global"], index=0)
    workspace_page = st.sidebar.radio(
        "Workspace page",
        options=[
            "Overview",
            "CSV Summary",
            "Pipeline",
            "Ingestion & Cleaning",
            "Segmentation",
            "Forecasting",
            "Alerts & Recommendations",
            "Health & Geography",
        ],
        index=0,
    )
    auto_refresh = st.sidebar.toggle("Auto refresh", value=False)
    refresh_seconds = st.sidebar.slider("Refresh interval (sec)", 15, 300, 60, 15)
    if market_view == "India":
        st.sidebar.caption("India view uses lakh/crore number styling and IST timestamps. Source values are not currency-converted.")

    if auto_refresh:
        st.markdown(
            f'<meta http-equiv="refresh" content="{refresh_seconds}">',
            unsafe_allow_html=True,
        )

    return {
        "source_mode": source_mode,
        "uploaded_file": uploaded_file,
        "theme": theme,
        "market_view": market_view,
        "workspace_page": workspace_page,
    }


def render_workspace_toolbar(runtime_controls, source: Any) -> None:
    source_label = "Bundled project dataset" if runtime_controls["source_mode"] == "Project dataset" else getattr(source, "name", "Uploaded CSV")
    market_label = "India mode" if runtime_controls["market_view"] == "India" else "Global mode"
    st.markdown(
        f"""
        <div class="toolbar">
            <div>
                <div class="metric-label">Workspace</div>
                <div class="status-value">RetailOS Control Centre</div>
            </div>
            <div class="toolbar-copy">
                Source: <strong>{source_label}</strong> &nbsp;|&nbsp; View: <strong>{market_label}</strong> &nbsp;|&nbsp;
                User: <strong>{st.session_state.get('auth_name') or st.session_state.get('auth_user', 'operator')}</strong> &nbsp;|&nbsp;
                Role: <strong>{_role_label()}</strong>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def configure_filter_controls(artifacts, market_view: str):
    min_date = artifacts.clean_data["OrderDate"].min().date()
    max_date = artifacts.clean_data["OrderDate"].max().date()
    countries = sorted(artifacts.clean_data["Country"].dropna().unique().tolist())
    segments = sorted(artifacts.customer_features["segment"].dropna().unique().tolist())
    default_countries = ["India"] if market_view == "India" and "India" in countries else countries

    selected_dates = st.sidebar.date_input(
        "Date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )
    selected_countries = st.sidebar.multiselect("Country", options=countries, default=default_countries)
    selected_segments = st.sidebar.multiselect("Segment", options=segments, default=segments)

    if _role_allows_download():
        st.sidebar.download_button(
            "Download clean data",
            artifacts.clean_data.to_csv(index=False).encode("utf-8"),
            file_name="retailos_clean_data.csv",
            mime="text/csv",
            use_container_width=True,
        )
        st.sidebar.download_button(
            "Download anomalies",
            artifacts.anomalies.to_csv(index=False).encode("utf-8"),
            file_name="retailos_anomalies.csv",
            mime="text/csv",
            use_container_width=True,
        )
    else:
        st.sidebar.caption("Downloads are disabled for viewer accounts.")

    return {
        "selected_dates": selected_dates,
        "selected_countries": selected_countries,
        "selected_segments": selected_segments,
    }


def _segment_summary_from_features(customer_features: pd.DataFrame) -> pd.DataFrame:
    if customer_features.empty:
        return pd.DataFrame(
            columns=[
                "segment",
                "customers",
                "avg_recency",
                "avg_frequency",
                "avg_monetary",
                "avg_order_value",
            ]
        )

    return (
        customer_features.groupby("segment")
        .agg(
            customers=("segment", "size"),
            avg_recency=("recency_days", "mean"),
            avg_frequency=("frequency", "mean"),
            avg_monetary=("monetary", "mean"),
            avg_order_value=("avg_order_value", "mean"),
        )
        .reset_index()
        .sort_values("avg_monetary", ascending=False)
    )


def build_filtered_view(artifacts, controls):
    if isinstance(controls["selected_dates"], tuple) and len(controls["selected_dates"]) == 2:
        start_date, end_date = controls["selected_dates"]
    else:
        start_date = end_date = controls["selected_dates"]

    filtered_transactions = artifacts.clean_data.copy()
    filtered_transactions = filtered_transactions[
        filtered_transactions["OrderDate"].between(
            pd.Timestamp(start_date), pd.Timestamp(end_date)
        )
    ]

    if controls["selected_countries"]:
        filtered_transactions = filtered_transactions[
            filtered_transactions["Country"].isin(controls["selected_countries"])
        ]

    filtered_customer_features = artifacts.customer_features[
        artifacts.customer_features.index.isin(filtered_transactions["CustomerID"].unique())
    ].copy()

    if controls["selected_segments"]:
        filtered_customer_features = filtered_customer_features[
            filtered_customer_features["segment"].isin(controls["selected_segments"])
        ]
        filtered_transactions = filtered_transactions[
            filtered_transactions["CustomerID"].isin(filtered_customer_features.index)
        ]

    filtered_daily = build_daily_metrics(filtered_transactions)
    filtered_forecast_metrics = evaluate_forecast_accuracy(filtered_daily)
    filtered_forecast = forecast_demand(
        filtered_daily, rmse=filtered_forecast_metrics["rmse"]
    )
    filtered_anomalies = detect_anomalies(filtered_daily)
    filtered_country_summary = summarize_countries(filtered_transactions)
    filtered_funnel_proxy = build_conversion_funnel_proxy(filtered_transactions)
    filtered_health_score, filtered_health_status, filtered_health_components = calculate_health_score(
        filtered_transactions,
        filtered_customer_features,
        filtered_daily,
        filtered_anomalies,
        filtered_forecast_metrics,
    )
    filtered_segment_summary = _segment_summary_from_features(filtered_customer_features)
    filtered_segment_distribution = build_segment_distribution(filtered_customer_features)
    filtered_recommendations = generate_recommendations(
        filtered_daily,
        filtered_forecast,
        filtered_segment_summary,
        filtered_anomalies,
        filtered_health_score,
    )
    filtered_kpis = compute_kpis(
        filtered_transactions,
        filtered_daily,
        filtered_customer_features,
        filtered_health_score,
    )

    return {
        "clean_data": filtered_transactions,
        "customer_features": filtered_customer_features,
        "daily_metrics": filtered_daily,
        "forecast": filtered_forecast,
        "forecast_metrics": filtered_forecast_metrics,
        "anomalies": filtered_anomalies,
        "country_summary": filtered_country_summary,
        "funnel_proxy": filtered_funnel_proxy,
        "health_score": filtered_health_score,
        "health_status": filtered_health_status,
        "health_components": filtered_health_components,
        "segment_summary": filtered_segment_summary,
        "segment_distribution": filtered_segment_distribution,
        "recommendations": filtered_recommendations,
        "kpis": filtered_kpis,
        "market_view": controls["market_view"],
    }


def render_header(artifacts, view) -> None:
    market_view = view["market_view"]
    if market_view == "India":
        refreshed_text = artifacts.refreshed_at.tz_convert("Asia/Kolkata").strftime("%d %b %Y, %I:%M %p IST")
        hero_kicker = "RetailOS Bharat retail intelligence platform"
        hero_title = "Indian retail decisions, monitored and recommended in one control centre."
        hero_copy = (
            "RetailOS is tuned for Indian retail operators, distributor teams, and chain stores. "
            "It validates transaction quality, segments customers, forecasts demand, flags anomalies, "
            "scores operational health, and turns analysis into actions."
        )
    else:
        refreshed_text = artifacts.refreshed_at.strftime("%Y-%m-%d %H:%M UTC")
        hero_kicker = "RetailOS autonomous retail intelligence platform"
        hero_title = "Retail decisions, monitored and recommended in one operating system."
        hero_copy = (
            "RetailOS ingests retail transactions, validates data quality, segments customers, "
            "forecasts demand, detects anomalies, scores operational health, and translates model outputs "
            "into business actions for operators."
        )
    rmse_text = (
        format_money(view["forecast_metrics"]["rmse"], market_view)
        if not math.isnan(view["forecast_metrics"]["rmse"])
        else "N/A"
    )
    st.markdown(
        f"""
        <section class="hero">
            <div class="hero-kicker">{hero_kicker}</div>
            <h1 class="hero-title">{hero_title}</h1>
            <p class="hero-copy">{hero_copy}</p>
            <div class="hero-chip-row">
                <span class="hero-chip">{format_count(view['kpis']['total_customers'], market_view)} active customers</span>
                <span class="hero-chip">{format_count(view['kpis']['total_orders'], market_view)} completed orders</span>
                <span class="hero-chip">{len(view['anomalies'])} live alerts</span>
                <span class="hero-chip">Forecast RMSE {rmse_text}</span>
            </div>
            <div class="status-grid">
                <div class="status-tile">
                    <div class="status-label">System status</div>
                    <div class="status-value">{view['health_status']}</div>
                </div>
                <div class="status-tile">
                    <div class="status-label">Last update</div>
                    <div class="status-value">{refreshed_text}</div>
                </div>
                <div class="status-tile">
                    <div class="status-label">Retail health score</div>
                    <div class="status-value">{view['health_score']}/100</div>
                </div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_metric_cards(view) -> None:
    kpis = view["kpis"]
    market_view = view["market_view"]
    cards = [
        ("Revenue", format_money(kpis["total_revenue"], market_view, compact=True), format_percent(kpis["weekly_growth"]), "Weekly growth versus previous 7-day period"),
        ("Growth", format_percent(kpis["weekly_growth"]), "Trend signal", "Short-term trading acceleration"),
        ("Customers", format_count(kpis["total_customers"], market_view), f"{kpis['repeat_rate']:.1f}% repeat", "Active customer base in current filters"),
        ("Health score", f"{int(view['health_score'])}/100", view["health_status"], "Weighted operating health status"),
    ]

    columns = st.columns(4)
    for column, (label, value, delta, note) in zip(columns, cards):
        with column:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">{label}</div>
                    <div class="metric-value">{value}</div>
                    <div class="metric-delta">{delta}</div>
                    <div class="metric-note">{note}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_pipeline() -> None:
    descriptions = [
        "CSV ingestion today, with room for POS, ERP, and GST-aware integrations.",
        "Remove invalid, cancelled, or incomplete transactions before analysis.",
        "Create revenue, recency, frequency, value, and basket metrics for operators.",
        "RFM plus KMeans segmentation for VIP, Regular, and Low engagement customers.",
        "ARIMA demand forecasting with confidence intervals and RMSE backtesting.",
        "Z-score monitoring for unusual sales swings and basket mix disruptions.",
        "Weighted health score for retail stability, retention, and volatility.",
        "Action recommendations for merchandising, retention, and stock planning.",
        "Interactive RetailOS workspace for daily monitoring and decision support.",
    ]
    st.markdown("## Architecture Flow")
    st.markdown(
        '<p class="section-copy">The product is organized as an operating pipeline rather than a static dashboard.</p>',
        unsafe_allow_html=True,
    )
    cards = list(zip(PIPELINE_STAGES, descriptions))
    for start in range(0, len(cards), 3):
        columns = st.columns(3)
        for offset, (name, description) in enumerate(cards[start : start + 3]):
            with columns[offset]:
                st.markdown(
                    f"""
                    <div class="pipeline-stage">
                        <div class="pipeline-index">{start + offset + 1}</div>
                        <div class="pipeline-name">{name}</div>
                        <div class="pipeline-copy">{description}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def render_data_engine(artifacts, market_view: str) -> None:
    left, right = st.columns([1, 1.1])
    with left:
        st.markdown("## Data Ingestion Layer")
        st.markdown(
            '<p class="section-copy">Current runtime supports CSV ingestion and validates the retail schema before analytics are applied.</p>',
            unsafe_allow_html=True,
        )
        ingestion_df = pd.DataFrame(
            {
                "Metric": [
                    "Source",
                    "Rows loaded",
                    "Columns loaded",
                    "Required columns valid",
                    "Encoding",
                    "Delimiter",
                    "Coverage countries",
                    "Date min",
                    "Date max",
                ],
                "Value": [
                    artifacts.ingestion_summary["source"],
                    format_count(artifacts.ingestion_summary["rows_loaded"], market_view),
                    format_count(artifacts.ingestion_summary["columns_loaded"], market_view),
                    artifacts.ingestion_summary["required_columns_ok"],
                    artifacts.ingestion_summary["encoding_used"],
                    artifacts.ingestion_summary["delimiter_used"],
                    format_count(artifacts.ingestion_summary["countries"], market_view),
                    artifacts.ingestion_summary["date_min"],
                    artifacts.ingestion_summary["date_max"],
                ],
            }
        )
        st.dataframe(ingestion_df, use_container_width=True, hide_index=True)

    with right:
        st.markdown("## Data Processing Engine")
        st.markdown(
            '<p class="section-copy">Cleaning and feature engineering make the downstream forecasting and segmentation layers auditable.</p>',
            unsafe_allow_html=True,
        )
        cleaning_df = pd.DataFrame(
            {
                "Metric": [
                    "Original rows",
                    "Clean rows",
                    "Validity rate",
                    "Removed rows",
                    "Invalid dates",
                    "Missing customers",
                    "Cancelled invoices",
                    "Non-positive lines",
                ],
                "Value": [
                    format_count(artifacts.cleaning_summary["original_rows"], market_view),
                    format_count(artifacts.cleaning_summary["clean_rows"], market_view),
                    format_percent(artifacts.cleaning_summary["validity_rate"]),
                    format_count(artifacts.cleaning_summary["removed_rows"], market_view),
                    format_count(artifacts.cleaning_summary["invalid_dates"], market_view),
                    format_count(artifacts.cleaning_summary["missing_customers"], market_view),
                    format_count(artifacts.cleaning_summary["cancelled_rows"], market_view),
                    format_count(artifacts.cleaning_summary["non_positive_rows"], market_view),
                ],
            }
        )
        st.dataframe(cleaning_df, use_container_width=True, hide_index=True)


def render_quick_csv_summary(artifacts, view) -> None:
    market_view = view["market_view"]
    st.markdown("## Quick CSV Summary")
    st.markdown(
        '<p class="section-copy">This page gives a fast read on the uploaded or bundled retail file before you go deep into forecasting and segmentation.</p>',
        unsafe_allow_html=True,
    )

    summary_cols = st.columns(4)
    summary_cards = [
        ("Rows loaded", format_count(artifacts.ingestion_summary["rows_loaded"], market_view)),
        ("Clean rows", format_count(artifacts.cleaning_summary["clean_rows"], market_view)),
        ("Columns", format_count(artifacts.ingestion_summary["columns_loaded"], market_view)),
        ("Countries", format_count(artifacts.ingestion_summary["countries"], market_view)),
    ]
    for column, (label, value) in zip(summary_cols, summary_cards):
        with column:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">{label}</div>
                    <div class="metric-value">{value}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    left, right = st.columns([0.9, 1.1])
    with left:
        st.markdown("#### File snapshot")
        snapshot_df = pd.DataFrame(
            {
                "Metric": [
                    "Source",
                    "Encoding",
                    "Delimiter",
                    "Date min",
                    "Date max",
                    "Active customers",
                    "Orders",
                ],
                "Value": [
                    artifacts.ingestion_summary["source"],
                    artifacts.ingestion_summary["encoding_used"],
                    artifacts.ingestion_summary["delimiter_used"],
                    artifacts.ingestion_summary["date_min"],
                    artifacts.ingestion_summary["date_max"],
                    format_count(view["kpis"]["total_customers"], market_view),
                    format_count(view["kpis"]["total_orders"], market_view),
                ],
            }
        )
        st.dataframe(snapshot_df, use_container_width=True, hide_index=True)

        missing_df = (
            artifacts.raw_data.isna()
            .sum()
            .reset_index()
            .rename(columns={"index": "Column", 0: "Missing values"})
        )
        missing_df["Missing %"] = missing_df["Missing values"].div(max(len(artifacts.raw_data), 1)).mul(100).round(1)
        st.markdown("#### Missing values")
        st.dataframe(missing_df.sort_values("Missing values", ascending=False), use_container_width=True, hide_index=True)

    with right:
        st.markdown("#### Column explorer")
        selected_column = st.selectbox("Inspect a column", options=artifacts.raw_data.columns.tolist())
        preview_rows = st.slider("Preview rows", min_value=5, max_value=30, value=10, step=5)
        column_series = artifacts.raw_data[selected_column]

        if pd.api.types.is_numeric_dtype(column_series):
            stats_df = pd.DataFrame(
                {
                    "Metric": ["Count", "Mean", "Median", "Min", "Max"],
                    "Value": [
                        int(column_series.count()),
                        round(float(column_series.mean()), 2) if column_series.count() else "N/A",
                        round(float(column_series.median()), 2) if column_series.count() else "N/A",
                        round(float(column_series.min()), 2) if column_series.count() else "N/A",
                        round(float(column_series.max()), 2) if column_series.count() else "N/A",
                    ],
                }
            )
        else:
            top_values = column_series.fillna("Missing").astype(str).value_counts().head(5)
            stats_df = pd.DataFrame(
                {
                    "Value": top_values.index,
                    "Count": top_values.values,
                }
            )
        st.dataframe(stats_df, use_container_width=True, hide_index=True)

        st.markdown("#### Data preview")
        st.dataframe(artifacts.raw_data.head(preview_rows), use_container_width=True, hide_index=True)


def render_segmentation(view) -> None:
    st.markdown("## Customer Segmentation Engine")
    st.markdown(
        '<p class="section-copy">RFM and KMeans separate customers into actionable commercial segments with value contribution visible beside the cluster map.</p>',
        unsafe_allow_html=True,
    )
    left, middle, right = st.columns([1.15, 0.85, 0.9])
    market_view = view["market_view"]

    with left:
        st.markdown("#### RFM + KMeans")
        if view["customer_features"].empty:
            st.info("No customer data matches the current filter set.")
        else:
            scatter_df = view["customer_features"].reset_index()
            chart = (
                alt.Chart(scatter_df)
                .mark_circle(size=90, opacity=0.8)
                .encode(
                    x=alt.X("frequency:Q", title="Customer frequency"),
                    y=alt.Y("monetary:Q", title="Monetary value"),
                    color=alt.Color("segment:N", scale=alt.Scale(range=["#287271", "#f4a261", "#e76f51"])),
                    tooltip=["CustomerID:N", "segment:N", "frequency:Q", "monetary:Q", "avg_order_value:Q", "recency_days:Q"],
                )
                .properties(height=350, title="Segment scatter")
            )
            st.altair_chart(chart, use_container_width=True)

    with middle:
        st.markdown("#### Segment distribution")
        if view["segment_distribution"].empty:
            st.info("No segment distribution available.")
        else:
            dist = view["segment_distribution"].sort_values("customers", ascending=True)
            chart = (
                alt.Chart(dist)
                .mark_bar(color="#287271")
                .encode(
                    x=alt.X("customers:Q", title="Customers"),
                    y=alt.Y("segment:N", sort=None, title=None),
                    tooltip=["segment:N", "customers:Q", "revenue:Q"],
                )
                .properties(height=350, title="Customer share")
            )
            st.altair_chart(chart, use_container_width=True)

    with right:
        st.markdown("#### Revenue contribution")
        if view["segment_distribution"].empty:
            st.info("No revenue contribution available.")
        else:
            revenue_dist = view["segment_distribution"].sort_values("revenue", ascending=True)
            chart = (
                alt.Chart(revenue_dist)
                .mark_bar(color="#f4a261")
                .encode(
                    x=alt.X("revenue:Q", title="Revenue"),
                    y=alt.Y("segment:N", sort=None, title=None),
                    tooltip=["segment:N", "customers:Q", "revenue:Q"],
                )
                .properties(height=350, title="Segment revenue")
            )
            st.altair_chart(chart, use_container_width=True)
        st.dataframe(
            view["segment_summary"].assign(
                customers=view["segment_summary"]["customers"].map(lambda value: format_count(value, market_view)),
                avg_monetary=view["segment_summary"]["avg_monetary"].map(lambda value: format_money(value, market_view)),
                avg_order_value=view["segment_summary"]["avg_order_value"].map(lambda value: format_money(value, market_view)),
                avg_frequency=view["segment_summary"]["avg_frequency"].map(lambda value: round(float(value), 1)),
                avg_recency=view["segment_summary"]["avg_recency"].map(lambda value: round(float(value), 1)),
            ),
            use_container_width=True,
            hide_index=True,
        )


def render_forecasting(view) -> None:
    st.markdown("## Forecasting Engine")
    st.markdown(
        '<p class="section-copy">ARIMA is used for the 30-day revenue outlook, with RMSE backtesting to expose reliability instead of treating the forecast as unqualified truth.</p>',
        unsafe_allow_html=True,
    )
    left, right = st.columns([1.3, 0.7])
    market_view = view["market_view"]

    with left:
        history = view["daily_metrics"].tail(120)
        forecast = view["forecast"]
        history_df = history.reset_index().rename(columns={"index": "OrderDate"})
        forecast_df = forecast.reset_index().rename(columns={"index": "OrderDate"})
        historical_chart = (
            alt.Chart(history_df)
            .transform_fold(
                ["revenue", "revenue_7d_ma"],
                as_=["series", "value"],
            )
            .mark_line(strokeWidth=3)
            .encode(
                x=alt.X("OrderDate:T", title=None),
                y=alt.Y("value:Q", title="Revenue"),
                color=alt.Color(
                    "series:N",
                    scale=alt.Scale(
                        domain=["revenue", "revenue_7d_ma"],
                        range=["#287271", "#e76f51"],
                    ),
                    title=None,
                ),
                strokeDash=alt.StrokeDash(
                    "series:N",
                    scale=alt.Scale(
                        domain=["revenue", "revenue_7d_ma"],
                        range=[[1, 0], [6, 4]],
                    ),
                    title=None,
                ),
                tooltip=["OrderDate:T", "series:N", "value:Q"],
            )
        )
        interval_chart = (
            alt.Chart(forecast_df)
            .mark_area(color="#e9c46a", opacity=0.25)
            .encode(
                x="OrderDate:T",
                y=alt.Y("forecast_lower:Q", title="Revenue"),
                y2="forecast_upper:Q",
                tooltip=["OrderDate:T", "forecast_lower:Q", "forecast_upper:Q"],
            )
        )
        forecast_line = (
            alt.Chart(forecast_df)
            .mark_line(color="#1f2a2c", strokeWidth=3)
            .encode(
                x="OrderDate:T",
                y="forecast_revenue:Q",
                tooltip=["OrderDate:T", "forecast_revenue:Q"],
            )
        )
        chart = (interval_chart + historical_chart + forecast_line).properties(height=360, title="Sales forecast")
        st.altair_chart(chart, use_container_width=True)

    with right:
        st.markdown("#### Forecast quality")
        rmse_value = view["forecast_metrics"]["rmse"]
        mape_value = view["forecast_metrics"]["mape"]
        quality_df = pd.DataFrame(
            {
                "Metric": [
                    "RMSE",
                    "MAPE",
                    "Reliability score",
                    "Evaluation window",
                ],
                "Value": [
                    "N/A" if math.isnan(rmse_value) else format_money(rmse_value, market_view),
                    "N/A" if math.isnan(mape_value) else format_percent(mape_value),
                    f"{view['forecast_metrics']['forecast_reliability_score']:.1f}/100",
                    int(view["forecast_metrics"]["evaluation_window"]),
                ],
            }
        )
        st.dataframe(quality_df, use_container_width=True, hide_index=True)


def render_funnel_and_alerts(view) -> None:
    left, right = st.columns([0.95, 1.05])
    market_view = view["market_view"]

    with left:
        st.markdown("## Conversion Funnel")
        st.markdown(
            '<p class="section-copy">This funnel is a modeled proxy based on completed transactions. Replace it with digital event streams for exact visitor and cart analytics.</p>',
            unsafe_allow_html=True,
        )
        funnel = view["funnel_proxy"].copy()
        if funnel.empty:
            st.info("No funnel data available.")
        else:
            funnel_sorted = funnel.copy()
            funnel_sorted["stage"] = pd.Categorical(
                funnel_sorted["stage"],
                categories=["Visitors", "Product Views", "Cart", "Purchase"],
                ordered=True,
            )
            funnel_sorted = funnel_sorted.sort_values("stage", ascending=False)
            chart = (
                alt.Chart(funnel_sorted)
                .mark_bar()
                .encode(
                    x=alt.X("value:Q", title="Volume"),
                    y=alt.Y("stage:N", sort=None, title=None),
                    color=alt.Color(
                        "stage:N",
                        scale=alt.Scale(
                            domain=["Visitors", "Product Views", "Cart", "Purchase"],
                            range=["#d9b44a", "#f4a261", "#e76f51", "#287271"],
                        ),
                        legend=None,
                    ),
                    tooltip=["stage:N", "value:Q"],
                )
                .properties(height=300, title="Modeled funnel")
            )
            st.altair_chart(chart, use_container_width=True)

            purchase_value = max(int(funnel.loc[funnel["stage"] == "Purchase", "value"].iloc[0]), 1)
            visitor_value = max(int(funnel.loc[funnel["stage"] == "Visitors", "value"].iloc[0]), 1)
            cart_value = max(int(funnel.loc[funnel["stage"] == "Cart", "value"].iloc[0]), 1)
            conversion_rate = purchase_value / visitor_value * 100
            abandonment_rate = (1 - (purchase_value / cart_value)) * 100
            st.dataframe(
                pd.DataFrame(
                    {
                        "Metric": ["Conversion rate", "Abandonment rate"],
                        "Value": [format_percent(conversion_rate), format_percent(abandonment_rate)],
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )

    with right:
        st.markdown("## Alert & Recommendation Panel")
        st.markdown(
            '<p class="section-copy">Alerts are generated from statistical monitoring and paired with recommended actions from the decision engine.</p>',
            unsafe_allow_html=True,
        )
        top_alerts = view["anomalies"][["OrderDate", "anomaly_type", "severity"]].head(4).copy()
        if top_alerts.empty:
            st.info("No anomaly alerts are active in the selected window.")
        else:
            date_pattern = "%d-%m-%Y" if market_view == "India" else "%Y-%m-%d"
            top_alerts["OrderDate"] = pd.to_datetime(top_alerts["OrderDate"]).dt.strftime(date_pattern)
            st.dataframe(top_alerts, use_container_width=True, hide_index=True)

        recommendation_columns = st.columns(2)
        for index, recommendation in enumerate(view["recommendations"]):
            with recommendation_columns[index % 2]:
                st.markdown(
                    f"""
                    <div class="alert-card">
                        <div class="priority-pill">{recommendation['priority']} priority</div>
                        <h3>{recommendation['title']}</h3>
                        <p class="section-copy">{recommendation['action']}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def render_health_and_geography(view) -> None:
    left, right = st.columns([0.9, 1.1])
    market_view = view["market_view"]

    with left:
        st.markdown("## Retail Health Score")
        st.markdown(
            '<p class="section-copy">The health score blends revenue stability, forecast reliability, customer retention, and sales volatility using the blueprint weights.</p>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""
            <div class="health-ring" style="--score:{view['health_score']};">
                <div class="health-ring-value">
                    <div class="health-ring-number">{view['health_score']}</div>
                    <div>{view['health_status']}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        health_table = view["health_components"].copy()
        health_table["weight"] = health_table["weight"].map(lambda value: format_percent(value * 100))
        health_table["score"] = health_table["score"].map(lambda value: round(float(value), 1))
        health_table["value"] = health_table["value"].map(
            lambda value: "N/A" if pd.isna(value) else round(float(value), 2)
        )
        st.dataframe(health_table, use_container_width=True, hide_index=True)

    with right:
        st.markdown("## Geography and Market Coverage")
        st.markdown(
            '<p class="section-copy">Top markets indicate where demand concentration is strongest and where operational decisions will have the highest leverage.</p>',
            unsafe_allow_html=True,
        )
        if view["country_summary"].empty:
            st.info("No country summary is available for the selected filters.")
        else:
            countries = view["country_summary"].head(8).iloc[::-1]
            chart = (
                alt.Chart(countries)
                .mark_bar(color="#f4a261")
                .encode(
                    x=alt.X("revenue:Q", title="Revenue"),
                    y=alt.Y("Country:N", sort=None, title=None),
                    tooltip=["Country:N", "orders:Q", "customers:Q", "revenue:Q", "avg_order_value:Q"],
                )
                .properties(height=360, title="Top revenue markets")
            )
            st.altair_chart(chart, use_container_width=True)
            country_table = view["country_summary"].copy()
            country_table["orders"] = country_table["orders"].map(lambda value: format_count(value, market_view))
            country_table["customers"] = country_table["customers"].map(lambda value: format_count(value, market_view))
            country_table["revenue"] = country_table["revenue"].map(lambda value: format_money(value, market_view))
            country_table["avg_order_value"] = country_table["avg_order_value"].map(lambda value: format_money(value, market_view))
            st.dataframe(country_table, use_container_width=True, hide_index=True)


def render_workspace_page(page_name: str, artifacts, view) -> None:
    if page_name == "Overview":
        render_workspace_toolbar(
            {
                "source_mode": "Upload custom CSV" if artifacts.ingestion_summary["source"] != "data/retail.csv" else "Project dataset",
                "market_view": view["market_view"],
            },
            artifacts.ingestion_summary["source"],
        )
        render_header(artifacts, view)
        st.write("")
        render_metric_cards(view)
        st.write("")
        render_quick_csv_summary(artifacts, view)
        return

    if page_name == "CSV Summary":
        render_workspace_toolbar(
            {
                "source_mode": "Upload custom CSV" if artifacts.ingestion_summary["source"] != "data/retail.csv" else "Project dataset",
                "market_view": view["market_view"],
            },
            artifacts.ingestion_summary["source"],
        )
        render_quick_csv_summary(artifacts, view)
        return

    if page_name == "Pipeline":
        render_workspace_toolbar(
            {
                "source_mode": "Upload custom CSV" if artifacts.ingestion_summary["source"] != "data/retail.csv" else "Project dataset",
                "market_view": view["market_view"],
            },
            artifacts.ingestion_summary["source"],
        )
        render_pipeline()
        return

    if page_name == "Ingestion & Cleaning":
        render_workspace_toolbar(
            {
                "source_mode": "Upload custom CSV" if artifacts.ingestion_summary["source"] != "data/retail.csv" else "Project dataset",
                "market_view": view["market_view"],
            },
            artifacts.ingestion_summary["source"],
        )
        render_data_engine(artifacts, view["market_view"])
        return

    if page_name == "Segmentation":
        render_workspace_toolbar(
            {
                "source_mode": "Upload custom CSV" if artifacts.ingestion_summary["source"] != "data/retail.csv" else "Project dataset",
                "market_view": view["market_view"],
            },
            artifacts.ingestion_summary["source"],
        )
        render_segmentation(view)
        return

    if page_name == "Forecasting":
        render_workspace_toolbar(
            {
                "source_mode": "Upload custom CSV" if artifacts.ingestion_summary["source"] != "data/retail.csv" else "Project dataset",
                "market_view": view["market_view"],
            },
            artifacts.ingestion_summary["source"],
        )
        render_forecasting(view)
        return

    if page_name == "Alerts & Recommendations":
        render_workspace_toolbar(
            {
                "source_mode": "Upload custom CSV" if artifacts.ingestion_summary["source"] != "data/retail.csv" else "Project dataset",
                "market_view": view["market_view"],
            },
            artifacts.ingestion_summary["source"],
        )
        render_funnel_and_alerts(view)
        return

    render_workspace_toolbar(
        {
            "source_mode": "Upload custom CSV" if artifacts.ingestion_summary["source"] != "data/retail.csv" else "Project dataset",
            "market_view": view["market_view"],
        },
        artifacts.ingestion_summary["source"],
    )
    render_health_and_geography(view)


def main() -> None:
    require_authentication(theme="Light")
    runtime_controls = configure_runtime_controls()
    source = "data/retail.csv"
    if runtime_controls["source_mode"] == "Upload custom CSV":
        if runtime_controls["uploaded_file"] is None:
            inject_styles(runtime_controls["theme"])
            st.info("Choose a CSV file in the sidebar or switch back to Project dataset.")
            st.stop()
        source = runtime_controls["uploaded_file"]
    try:
        artifacts = load_artifacts(source)
    except ValueError as error:
        inject_styles(runtime_controls["theme"])
        st.error(f"Data validation failed: {error}")
        st.stop()

    if artifacts.clean_data.empty:
        inject_styles(runtime_controls["theme"])
        st.error("No valid retail transactions remained after cleaning. Check the source data and retry.")
        st.stop()

    filter_controls = configure_filter_controls(artifacts, runtime_controls["market_view"])
    controls = {**runtime_controls, **filter_controls}
    inject_styles(runtime_controls["theme"])
    view = build_filtered_view(artifacts, controls)

    render_workspace_page(runtime_controls["workspace_page"], artifacts, view)


if __name__ == "__main__":
    main()
