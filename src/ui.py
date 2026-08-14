"""Shared UI helpers: theming/animation, the login gate, and the percentage gauge."""
from __future__ import annotations

import os
import time

import streamlit as st

CUSTOM_CSS = """
<style>
@keyframes drift1 { 0% {transform: translate(0,0) scale(1);} 50% {transform: translate(40px,-30px) scale(1.15);} 100% {transform: translate(0,0) scale(1);} }
@keyframes drift2 { 0% {transform: translate(0,0) scale(1);} 50% {transform: translate(-50px,40px) scale(1.1);} 100% {transform: translate(0,0) scale(1);} }
@keyframes fadeInUp { from {opacity:0; transform: translateY(16px);} to {opacity:1; transform: translateY(0);} }

.stApp {
    background: radial-gradient(circle at 20% 20%, #1b1f3b 0%, #0e1117 60%) fixed;
}

#ambient-bg { position: fixed; inset: 0; z-index: 0; overflow: hidden; pointer-events: none; }
#ambient-bg .blob { position: absolute; border-radius: 50%; filter: blur(90px); opacity: 0.35; }
#ambient-bg .blob1 { width: 420px; height: 420px; background: #6366f1; top: -120px; left: -80px; animation: drift1 18s ease-in-out infinite; }
#ambient-bg .blob2 { width: 360px; height: 360px; background: #a855f7; bottom: -120px; right: -60px; animation: drift2 22s ease-in-out infinite; }
#ambient-bg .blob3 { width: 300px; height: 300px; background: #22d3ee; top: 35%; left: 55%; animation: drift1 26s ease-in-out infinite reverse; }

section.main > div.block-container { animation: fadeInUp 0.6s ease-out; position: relative; z-index: 1; }

div[data-testid="stFileUploader"] {
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    border-radius: 12px;
}
div[data-testid="stFileUploader"]:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(99,102,241,0.25); }

.stButton>button {
    transition: transform 0.15s ease, box-shadow 0.15s ease;
    border-radius: 10px !important;
}
.stButton>button:hover { transform: translateY(-2px) scale(1.02); box-shadow: 0 6px 18px rgba(99,102,241,0.35); }

div[data-testid="stMetric"] {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px;
    padding: 0.75rem 1rem;
    transition: transform 0.2s ease;
}
div[data-testid="stMetric"]:hover { transform: translateY(-2px); }
</style>
<div id="ambient-bg">
  <div class="blob blob1"></div>
  <div class="blob blob2"></div>
  <div class="blob blob3"></div>
</div>
"""


def inject_theme() -> None:
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def _get_app_password() -> str | None:
    password = os.environ.get("APP_PASSWORD")
    if password:
        return password
    try:
        return st.secrets.get("APP_PASSWORD")
    except Exception:
        return None


def require_login() -> None:
    """Gate the whole app behind a shared password. Halts the script if not authenticated."""
    if st.session_state.get("authenticated"):
        return

    inject_theme()
    st.markdown(
        """
        <div style="max-width:420px;margin:10vh auto 0 auto;text-align:center;">
          <div style="font-size:3.2rem;">🎓</div>
          <h1 style="margin-bottom:0.2rem;">Academic Agent</h1>
          <p style="opacity:0.65;">Enter the access password to continue</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _, center, _ = st.columns([1, 1, 1])
    with center:
        with st.form("login_form"):
            pwd = st.text_input(
                "Password", type="password", label_visibility="collapsed", placeholder="Password"
            )
            submitted = st.form_submit_button("Enter", use_container_width=True, type="primary")

        if submitted:
            expected = _get_app_password()
            if not expected:
                st.error("APP_PASSWORD is not configured on the server. Set it in secrets or .env.")
            elif pwd == expected:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Incorrect password.")

    st.stop()


def render_gauge(percentage: float, label: str = "Score") -> None:
    """Render an animated circular percentage gauge (pure inline SVG/CSS, no extra deps)."""
    pct = max(0, min(100, percentage))
    size = 170
    radius = 70
    circumference = 2 * 3.14159265 * radius
    offset = circumference * (1 - pct / 100)
    anim_name = f"gaugefill{int(time.time() * 1000)}"
    color = "#22c55e" if pct >= 70 else "#eab308" if pct >= 40 else "#ef4444"

    html = f"""
    <div style="display:flex; justify-content:center; margin: 0.5rem 0 1rem 0;">
      <div style="position:relative; width:{size}px; height:{size}px;">
        <svg width="{size}" height="{size}" viewBox="0 0 180 180">
          <circle cx="90" cy="90" r="{radius}" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="14"/>
          <circle cx="90" cy="90" r="{radius}" fill="none" stroke="{color}" stroke-width="14"
                  stroke-linecap="round"
                  stroke-dasharray="{circumference:.1f}"
                  stroke-dashoffset="{circumference:.1f}"
                  transform="rotate(-90 90 90)"
                  style="animation: {anim_name} 1.4s ease-out forwards;"/>
        </svg>
        <div style="position:absolute; inset:0; display:flex; flex-direction:column;
                    align-items:center; justify-content:center;">
          <div style="font-size:2rem; font-weight:700;">{pct:.0f}%</div>
          <div style="font-size:0.85rem; opacity:0.65;">{label}</div>
        </div>
      </div>
    </div>
    <style>
    @keyframes {anim_name} {{
      from {{ stroke-dashoffset: {circumference:.1f}; }}
      to {{ stroke-dashoffset: {offset:.1f}; }}
    }}
    </style>
    """
    st.markdown(html, unsafe_allow_html=True)
