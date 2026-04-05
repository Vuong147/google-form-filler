import base64
import datetime
import hashlib
import json
import math
import os
import random
import time

import streamlit as st

from form_parser import parse_form, get_form_id
from submitter import submit_form, precompute_answers, SUBMIT_URL_TEMPLATE

st.set_page_config(page_title="Tool của a zai Hàn Quốc", page_icon="🤖", layout="centered")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&display=swap');

    /* ── Dark Gray Gradient Theme ── */
    .stApp {
        font-family: 'Space Grotesk', sans-serif;
        background: radial-gradient(circle at 20% 10%, #10233f 0%, #0a1428 38%, #060d1d 100%);
        overflow-x: hidden;
    }
    .stApp::before {
        content: '';
        position: fixed;
        top: -30%;
        left: -10%;
        width: 60%;
        height: 60%;
        background: radial-gradient(ellipse, rgba(34, 211, 238, 0.2) 0%, transparent 72%);
        animation: blob1 20s ease-in-out infinite alternate;
        pointer-events: none;
        z-index: 0;
    }
    .stApp::after {
        content: '';
        position: fixed;
        bottom: -22%;
        right: -8%;
        width: 58%;
        height: 58%;
        background: radial-gradient(ellipse, rgba(14, 165, 233, 0.18) 0%, transparent 74%);
        animation: blob2 24s ease-in-out infinite alternate;
        pointer-events: none;
        z-index: 0;
    }

    .stApp > div { position: relative; z-index: 1; }

    .mesh-layer {
        position: fixed;
        inset: 0;
        pointer-events: none;
        z-index: 0;
        overflow: hidden;
    }
    .mesh-orb {
        position: absolute;
        top: var(--top);
        left: var(--left);
        width: var(--size);
        height: var(--size);
        border-radius: 50%;
        background: radial-gradient(circle at 35% 30%, rgba(125, 250, 255, 0.65), rgba(15, 118, 161, 0.08));
        filter: blur(1.2px);
        opacity: 0.48;
        animation: mesh-float var(--dur) ease-in-out infinite;
        animation-delay: var(--delay);
    }
    .mesh-line {
        content: '';
        position: absolute;
        top: var(--top);
        left: var(--left);
        width: var(--width);
        height: 1px;
        background: linear-gradient(90deg, rgba(103, 232, 249, 0), rgba(103, 232, 249, 0.45), rgba(103, 232, 249, 0));
        transform: rotate(var(--angle));
        animation: mesh-slide var(--dur) ease-in-out infinite;
        animation-delay: var(--delay);
    }

    @keyframes blob1 {
        0%   { transform: translate(0, 0) scale(1); }
        50%  { transform: translate(5%, 6%) scale(1.08); }
        100% { transform: translate(-3%, -2%) scale(0.95); }
    }
    @keyframes blob2 {
        0%   { transform: translate(0, 0) scale(1); }
        50%  { transform: translate(-6%, -3%) scale(1.07); }
        100% { transform: translate(3%, 4%) scale(0.94); }
    }
    @keyframes mesh-float {
        0% {
            transform: translate3d(0, 0, 0) scale(1);
            opacity: 0.34;
        }
        50% {
            transform: translate3d(26px, -20px, 0) scale(1.18);
            opacity: 0.58;
        }
        100% {
            transform: translate3d(-20px, 18px, 0) scale(0.92);
            opacity: 0.28;
        }
    }
    @keyframes mesh-slide {
        0% { transform: translateX(0) rotate(var(--angle)); opacity: 0.22; }
        50% { transform: translateX(16px) rotate(var(--angle)); opacity: 0.45; }
        100% { transform: translateX(-10px) rotate(var(--angle)); opacity: 0.2; }
    }
    /* ── Typography ── */
    h1 { color: #ecfeff !important; letter-spacing: -0.6px; font-weight: 700 !important; }
    h2, h3 { color: #cffafe !important; font-weight: 600 !important; }
    p, label, .stMarkdown { color: #cbd5e1 !important; }

    /* ── Main content area ── */
    .block-container {
        background: linear-gradient(160deg, rgba(10, 24, 44, 0.74), rgba(8, 19, 36, 0.66));
        backdrop-filter: blur(18px);
        border: 1px solid rgba(103, 232, 249, 0.2);
        border-radius: 20px;
        padding: 2rem 2.5rem !important;
        box-shadow: 0 16px 44px rgba(2, 8, 23, 0.65), inset 0 1px 0 rgba(125, 250, 255, 0.12);
    }

    /* ── Inputs ── */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stTextArea > div > div > textarea {
        background: rgba(15, 23, 34, 0.9) !important;
        color: #f8fafc !important;
        border: 1px solid rgba(148, 163, 184, 0.42) !important;
        border-radius: 12px !important;
        backdrop-filter: blur(10px);
        transition: border-color 0.2s, box-shadow 0.2s;
    }
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #22d3ee !important;
        box-shadow: 0 0 0 3px rgba(34, 211, 238, 0.24) !important;
    }

    /* ── Selectbox / Radio ── */
    .stSelectbox > div > div,
    .stRadio > div {
        background: rgba(15, 23, 34, 0.78) !important;
        border-radius: 12px;
        color: #f1f5f9 !important;
    }

    /* ── Primary button ── */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #0891b2, #22d3ee);
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        padding: 0.55rem 2rem !important;
        box-shadow: 0 8px 24px rgba(6, 182, 212, 0.42);
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 12px 34px rgba(8, 145, 178, 0.58);
    }
    /* ── Secondary button ── */
    .stButton > button:not([kind="primary"]) {
        background: rgba(15, 23, 34, 0.7) !important;
        color: #e2e8f0 !important;
        border: 1px solid rgba(148, 163, 184, 0.35) !important;
        border-radius: 12px !important;
        font-weight: 500 !important;
        transition: background 0.2s, transform 0.2s;
    }
    .stButton > button:not([kind="primary"]):hover {
        background: rgba(30, 41, 59, 0.85) !important;
        transform: translateY(-1px);
    }

    /* ── Expander ── */
    .streamlit-expanderHeader {
        background: rgba(30, 41, 59, 0.8) !important;
        border: 1px solid rgba(100, 116, 139, 0.35) !important;
        border-radius: 12px !important;
        color: #f1f5f9 !important;
    }
    .streamlit-expanderContent {
        background: rgba(15, 23, 34, 0.72) !important;
        border: 1px solid rgba(100, 116, 139, 0.22) !important;
        border-top: none !important;
        border-radius: 0 0 12px 12px !important;
    }

    /* ── Metric cards ── */
    [data-testid="stMetric"] {
        background: rgba(9, 20, 36, 0.78);
        border: 1px solid rgba(103, 232, 249, 0.22);
        border-radius: 16px;
        padding: 1rem;
        backdrop-filter: blur(10px);
        box-shadow: 0 8px 20px rgba(2, 6, 23, 0.45);
    }
    [data-testid="stMetricValue"] { color: #ecfeff !important; font-weight: 700 !important; }
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(120px, 1fr));
        gap: 0.9rem;
        margin-top: 0.4rem;
    }
    .kpi-card {
        background: linear-gradient(165deg, rgba(10, 24, 44, 0.82), rgba(8, 20, 36, 0.74));
        border: 1px solid rgba(103, 232, 249, 0.26);
        border-radius: 16px;
        padding: 0.95rem 1rem;
        box-shadow: inset 0 1px 0 rgba(186, 230, 253, 0.12), 0 10px 26px rgba(2, 10, 23, 0.52);
    }
    .kpi-label {
        color: #a5f3fc;
        font-size: 0.88rem;
        font-weight: 500;
        margin-bottom: 0.36rem;
    }
    .kpi-value {
        color: #ecfeff;
        font-size: 2rem;
        line-height: 1;
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    @media (max-width: 760px) {
        .kpi-grid { grid-template-columns: 1fr; }
    }

    /* ── Progress bar ── */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, #2563eb, #60a5fa) !important;
        border-radius: 99px;
    }
    .stProgress > div > div {
        background: rgba(15, 23, 34, 0.45) !important;
        border-radius: 99px;
    }

    /* ── Alert / Info / Success / Warning ── */
    .stAlert {
        border-radius: 12px !important;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(100, 116, 139, 0.35) !important;
    }

    /* ── Divider ── */
    hr { border-color: rgba(148, 163, 184, 0.24) !important; }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: rgba(10, 15, 24, 0.9) !important;
        backdrop-filter: blur(24px);
        border-right: 1px solid rgba(100, 116, 139, 0.25) !important;
    }
    [data-testid="stSidebar"] > div:first-child {
        background: transparent !important;
        overflow-y: auto !important;
        height: 100vh;
        padding-bottom: 1.25rem;
        position: relative;
    }
    .sidebar-snow {
        position: absolute;
        inset: 0;
        pointer-events: none;
        z-index: 0;
        overflow: hidden;
    }
    .sidebar-snow span {
        position: absolute;
        top: -10%;
        left: var(--x);
        width: var(--s);
        height: var(--s);
        background: rgba(255, 255, 255, 0.88);
        border-radius: 50%;
        box-shadow: 0 0 4px rgba(255, 255, 255, 0.3);
        animation: avatar-snow-fall var(--d) linear infinite;
        animation-delay: var(--delay);
    }
    [data-testid="stSidebar"] .block-container,
    [data-testid="stSidebar"] .stMarkdown,
    [data-testid="stSidebar"] [data-testid="stImage"] {
        position: relative;
        z-index: 1;
    }

    /* ── Avatar ── */
    .avatar-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 0.9rem 0 0.6rem 0;
        position: relative;
        border-radius: 18px;
    }
    .avatar-container img {
        border-radius: 18px;
        border: 2px solid rgba(96, 165, 250, 0.45);
        box-shadow: 0 0 28px rgba(37, 99, 235, 0.3);
        width: 100%;
        max-height: 220px;
        object-fit: cover;
        transition: box-shadow 0.3s;
        position: relative;
        z-index: 1;
    }
    @keyframes avatar-snow-fall {
        0% {
            transform: translate3d(0, -10%, 0);
            opacity: 0;
        }
        15% { opacity: 0.9; }
        80% { opacity: 0.85; }
        100% {
            transform: translate3d(10px, 115%, 0);
            opacity: 0;
        }
    }
    .avatar-name {
        color: #dbeafe;
        font-size: 0.95rem;
        font-weight: 600;
        margin-top: 0.7rem;
        text-align: center;
        letter-spacing: 0.3px;
    }
    .avatar-music {
        width: 100%;
        margin-top: 0.55rem;
        padding: 0.32rem 0.42rem;
        background: rgba(15, 23, 34, 0.86);
        border: 1px solid rgba(34, 197, 94, 0.25);
        border-radius: 12px;
    }
    .avatar-music audio {
        width: 100%;
        height: 34px;
        border-radius: 10px;
    }

    /* ── Spotify-like Music Card ── */
    .music-card {
        background: linear-gradient(155deg, rgba(18, 18, 18, 0.96), rgba(28, 28, 28, 0.95));
        border: 1px solid rgba(34, 197, 94, 0.25);
        border-radius: 16px;
        padding: 0.78rem 0.82rem 0.66rem 0.82rem;
        box-shadow: 0 12px 26px rgba(0, 0, 0, 0.45);
        margin-top: 0.1rem;
    }
    .music-title {
        color: #f8fafc;
        font-size: 0.95rem;
        font-weight: 700;
        letter-spacing: 0.2px;
        margin-bottom: 0.1rem;
    }
    .music-subtitle {
        color: #94a3b8;
        font-size: 0.75rem;
        margin-bottom: 0.4rem;
    }
    .music-card audio {
        width: 100%;
        border-radius: 12px;
        outline: none;
        filter: saturate(1.08) contrast(1.03);
    }
    .music-foot {
        margin-top: 0.45rem;
        color: #22c55e;
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.3px;
        text-transform: uppercase;
    }

    /* ── Code block ── */
    .stCodeBlock {
        border-radius: 12px !important;
        border: 1px solid rgba(100, 116, 139, 0.25) !important;
    }

    /* ── Scrollbar ── */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(148, 163, 184, 0.42); border-radius: 99px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(148, 163, 184, 0.68); }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="mesh-layer" aria-hidden="true">
  <span class="mesh-orb" style="--left:8%;--top:20%;--size:220px;--dur:22s;--delay:-4s"></span>
  <span class="mesh-orb" style="--left:56%;--top:9%;--size:260px;--dur:26s;--delay:-11s"></span>
  <span class="mesh-orb" style="--left:73%;--top:58%;--size:210px;--dur:24s;--delay:-8s"></span>
  <span class="mesh-orb" style="--left:18%;--top:68%;--size:240px;--dur:28s;--delay:-16s"></span>
  <span class="mesh-line" style="--left:10%;--top:36%;--width:40%;--angle:11deg;--dur:18s;--delay:-6s"></span>
  <span class="mesh-line" style="--left:34%;--top:63%;--width:46%;--angle:-8deg;--dur:22s;--delay:-12s"></span>
  <span class="mesh-line" style="--left:46%;--top:22%;--width:34%;--angle:17deg;--dur:20s;--delay:-9s"></span>
</div>
""", unsafe_allow_html=True)

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
APP_PASSWORD = "2707"
DEVICE_REGISTRY_PATH = os.path.join(os.path.dirname(__file__), "device_registry.json")

SUPPORTED_TYPES = ("multiple_choice", "dropdown", "checkbox", "linear_scale",
                   "short_text", "paragraph", "date", "time")


def _get_device_id() -> str:
    """Fingerprint ổn định từ browser headers — không dùng IP."""
    headers = {}
    try:
        headers = dict(st.context.headers)
    except Exception:
        headers = {}

    user_agent  = headers.get("User-Agent", "")
    accept_lang = headers.get("Accept-Language", "")
    ch_platform = headers.get("Sec-CH-UA-Platform", "")
    ch_ua       = headers.get("Sec-CH-UA", "")

    # Không dùng IP (X-Forwarded-For) vì IP thay đổi → ID thay đổi
    fingerprint_raw = "|".join([user_agent, accept_lang, ch_platform, ch_ua])
    if not fingerprint_raw.strip():
        fingerprint_raw = "unknown-device"

    return hashlib.sha256(fingerprint_raw.encode("utf-8")).hexdigest()[:20]


def _load_device_registry() -> dict:
    default_data = {"allowed_devices": [], "blocked_devices": [], "device_meta": {}}
    if not os.path.exists(DEVICE_REGISTRY_PATH):
        return default_data
    try:
        with open(DEVICE_REGISTRY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return default_data
        # Backward-compat
        data.setdefault("allowed_devices", [])
        data.setdefault("blocked_devices", [])
        data.setdefault("device_meta", {})
        return data
    except Exception:
        return default_data


def _save_device_registry(data: dict) -> None:
    try:
        with open(DEVICE_REGISTRY_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _now_str() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _authorize_device() -> tuple:
    device_id = _get_device_id()
    registry = _load_device_registry()

    allowed = set(registry.get("allowed_devices", []))
    blocked = set(registry.get("blocked_devices", []))
    meta: dict = registry.get("device_meta", {})

    if device_id in blocked:
        # Cập nhật last_seen dù bị block
        if device_id not in meta:
            meta[device_id] = {"first_seen": _now_str(), "last_seen": _now_str(), "label": ""}
        else:
            meta[device_id]["last_seen"] = _now_str()
        registry["device_meta"] = meta
        _save_device_registry(registry)
        return False, device_id, "Thiết bị này đã bị chặn."

    now = _now_str()
    if device_id not in meta:
        meta[device_id] = {"first_seen": now, "last_seen": now, "label": ""}
    else:
        meta[device_id]["last_seen"] = now

    if device_id not in allowed:
        allowed.add(device_id)

    registry["allowed_devices"] = list(allowed)
    registry["blocked_devices"] = list(blocked)
    registry["device_meta"] = meta
    _save_device_registry(registry)

    return True, device_id, ""


# ── Init session state ────────────────────────────────────────────────────────
def _init():
    defaults = {
        "step": 0, "questions": [], "form_id": "", "url": "",
        "configured": [], "n_submissions": 10,
        "timing_mode": "delay", "delay_min": 2.0, "delay_max": 5.0,
        "win_start": "08:00", "win_end": "22:00",
        "proxies": [], "use_proxy": False,
        "results": [], "log": [],
        "logic_rules": [], "logic_rule_count": 0,
        "accuracy_mode": "balanced",
        "authenticated": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init()


def page_password():
    st.markdown(
        """
        <div style='text-align:center; padding: 2.2rem 0 1.2rem 0;'>
            <h2 style='margin-bottom: 0.6rem;'>🔐 NHẬP PASSWORD ĐỂ DÙNG TOOL (NGÀY SINH CỦA VƯN)</h2>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        pwd = st.text_input("Password", type="password", key="password_input")
        if st.button("Mở tool", type="primary", use_container_width=True):
            if pwd == APP_PASSWORD:
                ok, device_id, message = _authorize_device()
                if ok:
                    st.session_state.authenticated = True
                    st.session_state.device_id = device_id
                    st.rerun()
                else:
                    st.error(f"❌ {message}")
                    st.code(device_id)
            else:
                st.error("❌ Sai mật khẩu")


# ── Sidebar: ảnh + nhạc ────────────────────────────────────────────────────────
def _render_sidebar():
    with st.sidebar:
        st.markdown(
            """
            <div class="sidebar-snow" aria-hidden="true">
                <span style="--x:6%;--s:4px;--d:8s;--delay:-1s"></span>
                <span style="--x:14%;--s:3px;--d:9s;--delay:-5s"></span>
                <span style="--x:22%;--s:5px;--d:10s;--delay:-2s"></span>
                <span style="--x:31%;--s:3px;--d:8.5s;--delay:-6s"></span>
                <span style="--x:40%;--s:4px;--d:9.2s;--delay:-3s"></span>
                <span style="--x:50%;--s:3px;--d:11s;--delay:-7s"></span>
                <span style="--x:60%;--s:5px;--d:9.5s;--delay:-4s"></span>
                <span style="--x:69%;--s:3px;--d:8.8s;--delay:-8s"></span>
                <span style="--x:78%;--s:4px;--d:10.5s;--delay:-2.5s"></span>
                <span style="--x:87%;--s:3px;--d:9s;--delay:-6.5s"></span>
                <span style="--x:94%;--s:4px;--d:8.4s;--delay:-3.5s"></span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Ảnh avatar
        music_path = os.path.join(ASSETS_DIR, "music.mp3")
        avatar_extensions = ["jpg", "jpeg", "png", "webp"]
        avatar_path = None
        for ext in avatar_extensions:
            p = os.path.join(ASSETS_DIR, f"avatar.{ext}")
            if os.path.exists(p):
                avatar_path = p
                break

        if avatar_path:
            st.markdown('<div class="avatar-container">', unsafe_allow_html=True)
            st.image(avatar_path, use_container_width=True)

            if os.path.exists(music_path):
                with open(music_path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode()
                st.markdown(
                    f"""
                    <div class="avatar-music">
                        <audio autoplay loop controls>
                            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
                        </audio>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="avatar-container"><div style="color:#a78bfa;font-size:3rem">👤</div></div>',
                        unsafe_allow_html=True)

        st.markdown('<div class="avatar-name">🤖 Tool của a zai Hàn Quốc</div>', unsafe_allow_html=True)
        st.divider()

        if not os.path.exists(music_path):
            st.caption("⚠️ Chưa có file nhạc.\nThêm `assets/music.mp3` vào project.")

        st.divider()
        # Bước hiện tại
        steps = ["Nhập URL", "Cài đặt câu hỏi", "Cài đặt chạy", "Đang chạy"]
        for idx, label in enumerate(steps):
            icon = "✅" if idx < st.session_state.step else ("🔵" if idx == st.session_state.step else "⚪")
            st.markdown(f"{icon} {label}")

        st.divider()
        st.markdown("**🌐 Liên kết mạng xã hội**")
        st.markdown("- [Instagram](https://www.instagram.com/hvgnoul_/)")
        st.markdown("- [TikTok](https://www.tiktok.com/@hvunn_)")
        st.markdown("- [Facebook](https://www.facebook.com/youngboist/)")

        st.divider()
        with st.expander("🛡️ Quản lý thiết bị (Admin)"):
            admin_pwd = st.text_input("Admin password", type="password", key="admin_panel_password")
            if admin_pwd == APP_PASSWORD:
                registry = _load_device_registry()
                allowed_set = set(registry.get("allowed_devices", []))
                blocked_set = set(registry.get("blocked_devices", []))
                meta: dict = registry.get("device_meta", {})

                current_device = st.session_state.get("device_id", _get_device_id())
                all_known = list(dict.fromkeys(
                    list(allowed_set) + list(blocked_set) + list(meta.keys())
                ))

                st.caption(f"🖥️ Thiết bị hiện tại: `{current_device}`")
                st.caption(f"Tổng: **{len(all_known)}** thiết bị đã biết")
                st.divider()

                def _save_action(a_set, b_set, m):
                    _save_device_registry({
                        "allowed_devices": list(a_set),
                        "blocked_devices": list(b_set),
                        "device_meta": m,
                    })

                # ── Danh sách thiết bị ──────────────────────────────
                for dev_id in all_known:
                    is_blocked = dev_id in blocked_set
                    is_current = dev_id == current_device
                    dev_meta = meta.get(dev_id, {})
                    label = dev_meta.get("label", "") or ""
                    first_seen = dev_meta.get("first_seen", "—")
                    last_seen = dev_meta.get("last_seen", "—")

                    status_icon = "⛔" if is_blocked else "✅"
                    you_tag = " 👤 **(bạn)**" if is_current else ""
                    display_name = f"{label}" if label else f"`{dev_id[:12]}...`"

                    st.markdown(
                        f"{status_icon} **{display_name}**{you_tag}  \n"
                        f"<span style='font-size:0.75rem;color:#94a3b8;'>"
                        f"ID: `{dev_id}` · Lần đầu: {first_seen} · Lần cuối: {last_seen}"
                        f"</span>",
                        unsafe_allow_html=True,
                    )

                    col_label, col_block, col_del = st.columns([2, 1, 1])

                    with col_label:
                        new_label = st.text_input(
                            "Tên", value=label,
                            placeholder="Đặt tên thiết bị...",
                            key=f"label_{dev_id}",
                            label_visibility="collapsed",
                        )
                        if new_label != label:
                            if dev_id not in meta:
                                meta[dev_id] = {"first_seen": _now_str(), "last_seen": _now_str(), "label": ""}
                            meta[dev_id]["label"] = new_label
                            _save_action(allowed_set, blocked_set, meta)
                            st.rerun()

                    with col_block:
                        if is_blocked:
                            if st.button("✅ Mở", key=f"unblock_{dev_id}", use_container_width=True):
                                blocked_set.discard(dev_id)
                                allowed_set.add(dev_id)
                                _save_action(allowed_set, blocked_set, meta)
                                st.rerun()
                        else:
                            if st.button("⛔ Block", key=f"block_{dev_id}", use_container_width=True):
                                allowed_set.discard(dev_id)
                                blocked_set.add(dev_id)
                                _save_action(allowed_set, blocked_set, meta)
                                st.rerun()

                    with col_del:
                        if st.button("🗑️", key=f"del_{dev_id}", use_container_width=True):
                            allowed_set.discard(dev_id)
                            blocked_set.discard(dev_id)
                            meta.pop(dev_id, None)
                            _save_action(allowed_set, blocked_set, meta)
                            st.rerun()

                    st.markdown("<hr style='margin:6px 0;border-color:rgba(100,116,139,0.2)'>" , unsafe_allow_html=True)

                if not all_known:
                    st.info("Chưa có thiết bị nào đăng nhập")
            elif admin_pwd:
                st.error("Sai admin password")


# ── Helpers ───────────────────────────────────────────────────────────────────
def _min_n_for_exact(ratios: list) -> int:
    """Return minimum N so that N*ratio[i] is integer for all i."""
    from fractions import Fraction
    lcm = 1
    for r in ratios:
        frac = Fraction(r).limit_denominator(1000)
        lcm = lcm * frac.denominator // math.gcd(lcm, frac.denominator)
    return lcm


def _schedule(n, ws, we):
    now = datetime.datetime.now()
    today = now.date()
    sh, sm = map(int, ws.split(":"))
    eh, em = map(int, we.split(":"))
    s = datetime.datetime.combine(today, datetime.time(sh, sm))
    e = datetime.datetime.combine(today, datetime.time(eh, em))
    if e <= now:
        s += datetime.timedelta(days=1)
        e += datetime.timedelta(days=1)
    elif s < now:
        s = now + datetime.timedelta(seconds=2)
    total = (e - s).total_seconds()
    return sorted([s + datetime.timedelta(seconds=random.uniform(0, total)) for _ in range(n)])


def _pick_weighted_allowed(options: list, ratios: list, forbidden_options=None):
    forbidden = {str(x) for x in (forbidden_options or set()) if x is not None}
    allowed_idx = [i for i, opt in enumerate(options) if str(opt) not in forbidden]
    if not allowed_idx:
        return None

    allowed_options = [options[i] for i in allowed_idx]
    if ratios and len(ratios) == len(options):
        weights = [max(0.0, float(ratios[i])) for i in allowed_idx]
        if sum(weights) > 0:
            return random.choices(allowed_options, weights=weights, k=1)[0]
    return random.choice(allowed_options)


def _estimate_logic_distribution(configured: list, logic_rules: list, sample_size: int = 1200):
    single_types = ("multiple_choice", "dropdown", "linear_scale")
    candidates = [
        q for q in configured
        if (not q.get("skip")) and q.get("type") in single_types and q.get("options")
    ]
    if not candidates:
        return [], 0.0

    rules_by_source = {}
    for rule in (logic_rules or []):
        src = str(rule.get("source_entry_id", "")).strip()
        if not src:
            continue
        rules_by_source.setdefault(src, []).append(rule)

    counts_by_entry = {
        str(q["entry_id"]): {opt: 0 for opt in q.get("options", [])}
        for q in candidates
    }
    shown_by_entry = {str(q["entry_id"]): 0 for q in candidates}

    loops = max(200, int(sample_size))
    for _ in range(loops):
        forbidden_by_target = {}

        for q in configured:
            if q.get("skip") or q.get("type") not in single_types or not q.get("options"):
                continue

            entry_id = str(q["entry_id"])
            answer = _pick_weighted_allowed(
                q.get("options", []),
                q.get("ratios", []),
                forbidden_by_target.get(entry_id, set()),
            )
            if answer is None:
                continue

            if entry_id in shown_by_entry:
                shown_by_entry[entry_id] += 1
                if answer in counts_by_entry[entry_id]:
                    counts_by_entry[entry_id][answer] += 1

            for rule in rules_by_source.get(entry_id, []):
                if answer != rule.get("source_answer"):
                    continue
                target_id = str(rule.get("target_entry_id", "")).strip()
                forbidden_answer = rule.get("forbidden_answer")
                if target_id and forbidden_answer is not None:
                    forbidden_by_target.setdefault(target_id, set()).add(str(forbidden_answer))

    rows = []
    max_delta = 0.0
    for idx, q in enumerate(candidates):
        entry_id = str(q["entry_id"])
        options = q.get("options", [])
        ratios = q.get("ratios", [])
        shown = shown_by_entry.get(entry_id, 0)
        if shown <= 0:
            continue

        if ratios and len(ratios) == len(options) and sum(ratios) > 0:
            base_total = float(sum(ratios))
            base_pct = [float(r) / base_total * 100 for r in ratios]
        else:
            base_pct = [100.0 / len(options)] * len(options)

        question_label = f"Câu {idx + 1}: {q.get('text', '')}"
        if len(question_label) > 72:
            question_label = question_label[:69] + "..."

        for opt, base in zip(options, base_pct):
            est = counts_by_entry[entry_id].get(opt, 0) / shown * 100
            delta = est - base
            max_delta = max(max_delta, abs(delta))
            rows.append({
                "Câu hỏi": question_label,
                "Đáp án": opt,
                "% đã đặt": f"{base:.1f}%",
                "% ước tính": f"{est:.1f}%",
                "Lệch": f"{delta:+.1f}%",
                "Tần suất xuất hiện câu": f"{shown / loops * 100:.1f}%",
            })

    return rows, max_delta


def _validate_before_run(configured: list, logic_rules: list, accuracy_mode: str = "balanced") -> tuple:
    errors = []
    warnings = []
    single_types = ("multiple_choice", "dropdown", "linear_scale")
    mode = (accuracy_mode or "balanced").lower()

    q_by_entry = {}
    for q in configured:
        entry_id = str(q.get("entry_id", "")).strip()
        if entry_id:
            q_by_entry[entry_id] = q

    for q in configured:
        if q.get("skip") or q.get("type") not in single_types:
            continue
        if not q.get("required"):
            continue
        options = q.get("options", [])
        ratios = q.get("ratios", [])
        if not options:
            errors.append(f"Câu bắt buộc '{q.get('text', '')}' chưa có đáp án.")
            continue
        if ratios and len(ratios) == len(options):
            if sum(max(0.0, float(r)) for r in ratios) <= 0:
                errors.append(f"Câu bắt buộc '{q.get('text', '')}' có tổng % = 0.")

    grouped_forbidden = {}
    for i, rule in enumerate(logic_rules or [], start=1):
        src = str(rule.get("source_entry_id", "")).strip()
        tgt = str(rule.get("target_entry_id", "")).strip()
        src_ans = rule.get("source_answer")
        forb = rule.get("forbidden_answer")

        if not src or src not in q_by_entry:
            errors.append(f"Rule {i}: không tìm thấy câu nguồn.")
            continue
        if not tgt or tgt not in q_by_entry:
            errors.append(f"Rule {i}: không tìm thấy câu đích.")
            continue

        src_q = q_by_entry[src]
        tgt_q = q_by_entry[tgt]
        if src_ans not in (src_q.get("options") or []):
            errors.append(f"Rule {i}: đáp án nguồn không hợp lệ.")
            continue
        if forb not in (tgt_q.get("options") or []):
            errors.append(f"Rule {i}: đáp án cấm không hợp lệ.")
            continue

        key = (src, src_ans, tgt)
        grouped_forbidden.setdefault(key, set()).add(str(forb))

    for (src, src_ans, tgt), forb_set in grouped_forbidden.items():
        tgt_q = q_by_entry.get(tgt)
        if not tgt_q:
            continue
        options = [str(o) for o in (tgt_q.get("options") or [])]
        if options and all(opt in forb_set for opt in options):
            src_text = q_by_entry.get(src, {}).get("text", src)
            tgt_text = tgt_q.get("text", tgt)
            msg = (
                f"Rule conflict: nếu '{src_text}' = '{src_ans}' thì câu '{tgt_text}' bị cấm toàn bộ đáp án."
            )
            if mode == "strict":
                errors.append(msg)
            else:
                warnings.append(msg)

    return errors, warnings


def _build_preview_suggestions(rows: list, max_delta: float) -> list:
    tips = []
    if not rows:
        return ["Chưa đủ dữ liệu preview để gợi ý. Hãy tăng số lượt mô phỏng."]

    sorted_rows = sorted(
        rows,
        key=lambda r: abs(float(str(r.get("Lệch", "0")).replace("%", ""))),
        reverse=True,
    )

    for r in sorted_rows[:3]:
        try:
            delta = float(str(r.get("Lệch", "0")).replace("%", ""))
        except Exception:
            continue
        if abs(delta) < 1.0:
            continue

        q = r.get("Câu hỏi", "Câu hỏi")
        opt = r.get("Đáp án", "Đáp án")
        adjust = round(min(20.0, abs(delta) * 0.6), 1)
        if delta > 0:
            tips.append(f"Giảm trọng số `{opt}` ở `{q}` khoảng **{adjust} điểm %** để bám mục tiêu tốt hơn.")
        else:
            tips.append(f"Tăng trọng số `{opt}` ở `{q}` khoảng **{adjust} điểm %** để bám mục tiêu tốt hơn.")

    if max_delta >= 10:
        tips.append("Độ lệch còn cao; nên thử nới bớt rule hoặc đổi sang mode `Balanced` nếu ưu tiên sát %.")
    elif max_delta <= 3:
        tips.append("Phân phối hiện đã khá sát mục tiêu; có thể chạy thật.")

    return tips[:4] if tips else ["Phân phối hiện đã ổn, chưa cần chỉnh thêm."]


# ── Step 0: URL ───────────────────────────────────────────────────────────────
def page_url():
    st.markdown("""
    <div style='text-align:center; padding: 1rem 0 0.5rem 0;'>
        <span style='font-size:3rem;'>🤖</span>
        <h1 style='margin:0; font-size:2.2rem;'>Tool của a zai Hàn Quốc</h1>
        <p style='color:#a78bfa; margin-top:0.3rem;'>Tự động điền và submit Google Form theo tỉ lệ tùy chỉnh</p>
    </div>
    """, unsafe_allow_html=True)
    st.divider()

    url = st.text_input("🔗 Nhập URL Google Form",
                        placeholder="https://docs.google.com/forms/d/...")

    analyze_clicked = st.button("Phân tích Form", type="primary", disabled=not url.strip())

    st.divider()
    st.markdown("**🌐 Liên kết mạng xã hội**")
    st.markdown(
        """
        <div style="display:flex;justify-content:center;align-items:center;gap:18px;margin:0.25rem 0 0.35rem 0;">
            <a href="https://www.instagram.com/hvgnoul_/" target="_blank" style="display:inline-flex;">
                <img src="https://cdn.simpleicons.org/instagram/E4405F" alt="Instagram" width="28" height="28" />
            </a>
            <a href="https://www.tiktok.com/@hvunn_" target="_blank" style="display:inline-flex;">
                <img src="https://cdn.simpleicons.org/tiktok/FFFFFF" alt="TikTok" width="28" height="28" />
            </a>
            <a href="https://www.facebook.com/youngboist/" target="_blank" style="display:inline-flex;">
                <img src="https://cdn.simpleicons.org/facebook/1877F2" alt="Facebook" width="28" height="28" />
            </a>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if analyze_clicked:
        with st.spinner("Đang phân tích form..."):
            try:
                u = url.strip().rstrip("/")
                if "viewform" not in u and "formResponse" not in u:
                    u += "/viewform"
                questions, _published_id, fbzx = parse_form(u)
                form_id = get_form_id(u)
                st.session_state.questions = questions
                st.session_state.form_id = form_id
                st.session_state.fbzx = fbzx
                st.session_state.url = u
                st.session_state.step = 1
                st.rerun()
            except Exception as e:
                st.error(f"❌ {e}")


# ── Step 1: Configure questions ───────────────────────────────────────────────
def page_configure():
    st.title("⚙️ Cài đặt câu trả lời")

    questions = st.session_state.questions
    supported = [q for q in questions if q["type"] in SUPPORTED_TYPES]

    page_total = 1
    for qq in questions:
        try:
            page_total = max(page_total, int(qq.get("page_index", 0)) + 1)
        except Exception:
            pass
        for route in (qq.get("option_routes") or {}).values():
            if isinstance(route, int):
                page_total = max(page_total, route + 1)

    st.info(f"✅ Tìm thấy **{len(questions)}** câu hỏi ({len(supported)} loại được hỗ trợ)")

    n = st.number_input("Số lần submit", min_value=1, max_value=10000,
                        value=st.session_state.n_submissions, step=1)
    st.session_state.n_submissions = int(n)
    st.divider()

    configured = []
    valid = True

    for i, q in enumerate(questions):
        if q["type"] not in SUPPORTED_TYPES:
            continue
        cfg = dict(q)

        with st.expander(f"📌 Câu {i+1}: {q['text']}", expanded=True):
            st.caption(f"Loại: `{q['type']}`")

            if q["type"] in ("multiple_choice", "dropdown", "linear_scale") and q["options"]:
                st.write("Trọng số cho từng lựa chọn (để 0 = không chọn):")
                cols = st.columns(min(len(q["options"]), 4))
                ratios = []
                n_opts = len(q["options"])
                for j, opt in enumerate(q["options"]):
                    with cols[j % 4]:
                        v = st.number_input(opt, min_value=0.0, max_value=10000.0,
                                            value=round(100.0 / n_opts, 1),
                                            step=1.0, key=f"q{i}_o{j}")
                        ratios.append(v)
                total = sum(ratios)
                if total == 0:
                    st.warning("⚠️ Tổng trọng số phải > 0")
                    valid = False
                else:
                    cfg["ratios"] = [v / total for v in ratios]
                    pct_cols = st.columns(min(len(q["options"]), 4))
                    for j, (opt, r) in enumerate(zip(q["options"], ratios)):
                        with pct_cols[j % 4]:
                            st.caption(f"→ **{r/total*100:.1f}%**")

                if q["type"] in ("multiple_choice", "dropdown"):
                    st.caption("Điều kiện nhảy trang (tuỳ chọn):")
                    base_routes = cfg.get("option_routes") or {}
                    overrides = {}
                    choice_items = ["Theo form gốc", "Trang kế tiếp", "Kết thúc form"]
                    choice_items.extend([f"Nhảy tới trang {p}" for p in range(1, page_total + 1)])

                    cur_page = int(q.get("page_index", 0))
                    next_page_label = f"Nhảy tới trang {cur_page + 2}"

                    for j, opt in enumerate(q["options"]):
                        route_default = base_routes.get(opt)
                        default_choice = "Theo form gốc"

                        if route_default == "__submit__":
                            default_choice = "Kết thúc form"
                        elif isinstance(route_default, int):
                            if route_default == cur_page + 1:
                                default_choice = "Trang kế tiếp"
                            else:
                                label = f"Nhảy tới trang {route_default + 1}"
                                if label in choice_items:
                                    default_choice = label

                        key = f"q{i}_route_{j}"
                        selected = st.selectbox(
                            f"Nếu chọn '{opt}'",
                            choice_items,
                            index=choice_items.index(default_choice),
                            key=key,
                        )

                        if selected == "Theo form gốc":
                            continue
                        if selected == "Kết thúc form":
                            overrides[opt] = "__submit__"
                        elif selected == "Trang kế tiếp":
                            overrides[opt] = cur_page + 1
                        elif selected.startswith("Nhảy tới trang "):
                            page_no = int(selected.split(" ")[-1])
                            overrides[opt] = max(0, page_no - 1)

                    cfg["option_routes_override"] = overrides

            elif q["type"] == "checkbox" and q["options"]:
                st.write("Xác suất chọn mỗi ô (%):")
                cols = st.columns(min(len(q["options"]), 4))
                probs = []
                for j, opt in enumerate(q["options"]):
                    with cols[j % 4]:
                        v = st.slider(opt, 0, 100, 50, key=f"q{i}_cb{j}")
                        probs.append(v / 100)
                cfg["ratios"] = probs

            elif q["type"] in ("short_text", "paragraph"):
                n_subs = st.session_state.n_submissions
                st.write(f"Nhập câu trả lời — **mỗi dòng = 1 lần submit** (để trống nếu không cần):")
                prev_raw = st.session_state.get(f"q{i}_bulk_raw", "")
                raw = st.text_area(
                    f"Câu trả lời (mỗi dòng 1 submit)",
                    value=prev_raw,
                    height=max(120, min(n_subs * 32, 400)),
                    placeholder="\n".join([f"Câu trả lời lần {k+1}" for k in range(min(n_subs, 3))] + (["..."] if n_subs > 3 else [])),
                    key=f"q{i}_bulk",
                    label_visibility="collapsed",
                )
                st.session_state[f"q{i}_bulk_raw"] = raw
                filled = [ln for ln in raw.splitlines() if ln.strip()]

                # Chỉ hiển thị gợi ý nhẹ, không bắt buộc
                if len(filled) > n_subs:
                    st.caption(f"🟠 {len(filled)} dòng — nhiều hơn số submit ({n_subs}), sẽ dùng {n_subs} dòng đầu")
                elif 0 < len(filled) <= n_subs:
                    st.caption(f"🟢 {len(filled)}/{n_subs} dòng")
                else:
                    st.caption(f"💡 Để trống → tất cả submit gửi câu trả lời rỗng")

                # Lấy đúng n_subs dòng (padding rỗng nếu thiếu)
                answers = (filled + [""] * n_subs)[:n_subs]
                cfg["answers"] = answers
                cfg["ratios"] = [1.0] * len(answers)
                cfg["per_submission"] = True

            elif q["type"] in ("date", "time"):
                fmt = "YYYY-MM-DD" if q["type"] == "date" else "HH:MM"
                ph = "2024-01-15\n2024-02-20" if q["type"] == "date" else "08:30\n14:00"
                raw = st.text_area(f"Giá trị mẫu ({fmt}), mỗi dòng 1 giá trị:",
                                   key=f"q{i}_dt", placeholder=ph)
                answers = [a.strip() for a in raw.splitlines() if a.strip()]
                if not answers:
                    st.warning("⚠️ Cần ít nhất 1 giá trị")
                    valid = False
                cfg["answers"] = answers
                cfg["ratios"] = ([1.0 / len(answers)] * len(answers)) if answers else []

        configured.append(cfg)

    logic_candidates = [
        q for q in configured
        if q.get("type") in ("multiple_choice", "dropdown", "linear_scale") and q.get("options")
    ]
    logic_rules = []

    st.divider()
    with st.expander("🧠 Ràng buộc logic giữa các câu (tuỳ chọn)", expanded=False):
        if len(logic_candidates) < 2:
            st.caption("Cần ít nhất 2 câu dạng chọn 1 đáp án để tạo rule logic.")
        else:
            labels = [f"Câu {idx+1}: {qq['text']}" for idx, qq in enumerate(logic_candidates)]
            default_count = int(st.session_state.get("logic_rule_count", 0))
            rule_count = st.number_input(
                "Số rule",
                min_value=0,
                max_value=20,
                value=min(default_count, 20),
                step=1,
                key="logic_rule_count_input",
            )
            st.session_state.logic_rule_count = int(rule_count)

            for ridx in range(int(rule_count)):
                st.markdown(f"**Rule {ridx + 1}**")
                c1, c2 = st.columns(2)

                with c1:
                    src_idx = st.selectbox(
                        "Nếu câu",
                        options=list(range(len(logic_candidates))),
                        format_func=lambda x: labels[x],
                        key=f"logic_src_q_{ridx}",
                    )
                src_q = logic_candidates[src_idx]
                with c2:
                    src_answer = st.selectbox(
                        "Chọn đáp án",
                        options=src_q.get("options", []),
                        key=f"logic_src_opt_{ridx}",
                    )

                d1, d2 = st.columns(2)
                target_indices = [i for i in range(len(logic_candidates)) if i != src_idx]
                if not target_indices:
                    target_indices = [src_idx]

                with d1:
                    tgt_idx = st.selectbox(
                        "Thì câu",
                        options=target_indices,
                        format_func=lambda x: labels[x],
                        key=f"logic_tgt_q_{ridx}",
                    )
                tgt_q = logic_candidates[tgt_idx]
                with d2:
                    tgt_answer = st.selectbox(
                        "Không được chọn đáp án",
                        options=tgt_q.get("options", []),
                        key=f"logic_tgt_opt_{ridx}",
                    )

                logic_rules.append({
                    "source_entry_id": str(src_q["entry_id"]),
                    "source_answer": src_answer,
                    "target_entry_id": str(tgt_q["entry_id"]),
                    "forbidden_answer": tgt_answer,
                })

            if logic_rules:
                st.caption(f"Đã tạo {len(logic_rules)} rule logic.")
                sample_size = min(2000, max(400, st.session_state.n_submissions * 15))
                rows, max_delta = _estimate_logic_distribution(
                    configured,
                    logic_rules,
                    sample_size=sample_size,
                )
                if rows:
                    st.caption(
                        f"📊 Đã mô phỏng nhanh {sample_size:,} lượt để ước tính độ lệch tỉ lệ sau khi áp rule."
                    )
                if max_delta >= 10:
                    st.warning(
                        f"⚠️ Rule đang làm lệch tối đa khoảng {max_delta:.1f}% so với % đã đặt. "
                        "Bạn có thể giảm trọng số đáp án bị cấm hoặc nới rule để phân phối tự nhiên hơn."
                    )
                elif max_delta >= 5:
                    st.info(f"ℹ️ Rule làm lệch khoảng {max_delta:.1f}% — vẫn ổn nếu bạn ưu tiên logic hơn tỉ lệ tuyệt đối.")
            else:
                st.caption("Chưa có rule nào. Tool sẽ chạy theo tỉ lệ bình thường.")

    st.divider()
    st.subheader("🧪 Preview mô phỏng (không submit)")
    preview_n = st.number_input(
        "Số lượt preview",
        min_value=50,
        max_value=5000,
        value=300,
        step=50,
        key="preview_sample_size",
    )
    if st.button("Chạy preview"):
        with st.spinner("Đang mô phỏng..."):
            rows, max_delta = _estimate_logic_distribution(
                configured,
                logic_rules,
                sample_size=int(preview_n),
            )
            errors, warnings = _validate_before_run(
                configured,
                logic_rules,
                st.session_state.get("accuracy_mode", "balanced"),
            )
        suggestions = _build_preview_suggestions(rows, max_delta)
        st.caption(f"Đã mô phỏng {int(preview_n)} lượt, không gửi lên Google Form.")
        st.write(f"Độ lệch tối đa so với % đã đặt: **{max_delta:.1f}%**")
        if rows:
            top_rows = sorted(rows, key=lambda r: abs(float(r["Lệch"].replace("%", ""))), reverse=True)[:5]
            st.caption("Top 5 đáp án lệch nhiều nhất:")
            for r in top_rows:
                st.markdown(
                    f"- `{r['Câu hỏi']}` · `{r['Đáp án']}`: đặt {r['% đã đặt']} → ước tính {r['% ước tính']} (lệch {r['Lệch']})"
                )
        st.caption("🎯 Gợi ý tối ưu sát mục tiêu:")
        for tip in suggestions:
            st.markdown(f"- {tip}")
        for w in warnings[:5]:
            st.warning(f"⚠️ {w}")
        for e in errors[:5]:
            st.error(f"❌ {e}")

    # Tính LCM từ tỉ lệ THỰC TẾ đã nhập
    global_lcm = 1
    for cfg_q in configured:
        if cfg_q.get("type") in ("multiple_choice", "dropdown", "linear_scale") and cfg_q.get("ratios"):
            min_n = _min_n_for_exact(cfg_q["ratios"])
            global_lcm = global_lcm * min_n // math.gcd(global_lcm, min_n)

    n_cur = st.session_state.n_submissions
    st.divider()
    if global_lcm > 1:
        if n_cur % global_lcm == 0:
            st.success(f"✅ **{n_cur}** lần submit → đúng tỉ lệ tuyệt đối (bội số của {global_lcm})")
        else:
            nearest = math.ceil(n_cur / global_lcm) * global_lcm
            st.warning(
                f"⚠️ **{n_cur}** lần không chia đúng tỉ lệ. "
                f"Cần bội số của **{global_lcm}** → gần nhất: **{nearest}** lần"
            )
            if st.button(f"🎯 Điều chỉnh thành {nearest} lần"):
                st.session_state.n_submissions = nearest
                st.rerun()

    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Quay lại"):
            st.session_state.step = 0
            st.rerun()
    with col2:
        if st.button("Tiếp tục →", type="primary", disabled=not valid):
            st.session_state.configured = configured
            st.session_state.logic_rules = logic_rules
            st.session_state.step = 2
            st.rerun()


# ── Step 2: Run settings ──────────────────────────────────────────────────────
def page_settings():
    st.title("🚀 Cài đặt chạy")

    st.subheader("🎯 Chế độ chính xác")
    mode_label = st.radio(
        "",
        ["Balanced (giữ tỉ lệ tối đa)", "Strict (ưu tiên rule tuyệt đối)"],
        horizontal=True,
        index=0 if st.session_state.get("accuracy_mode", "balanced") == "balanced" else 1,
        label_visibility="collapsed",
    )
    st.session_state.accuracy_mode = "strict" if mode_label.startswith("Strict") else "balanced"
    if st.session_state.accuracy_mode == "strict":
        st.caption("Rule mâu thuẫn sẽ bị chặn chạy để đảm bảo đúng logic tuyệt đối.")
    else:
        st.caption("Ưu tiên giữ phân phối %, rule mâu thuẫn sẽ được nới mềm nếu cần.")

    st.subheader("⏱️ Chế độ thời gian")
    timing = st.radio("", ["Delay ngẫu nhiên (giây)", "Khung giờ"],
                      horizontal=True, label_visibility="collapsed")

    if timing == "Delay ngẫu nhiên (giây)":
        col1, col2 = st.columns(2)
        with col1:
            dmin = st.number_input("Delay min (giây)", min_value=0.0,
                                   value=st.session_state.delay_min, step=0.5)
        with col2:
            dmax = st.number_input("Delay max (giây)", min_value=0.0,
                                   value=st.session_state.delay_max, step=0.5)
        st.session_state.timing_mode = "delay"
        st.session_state.delay_min = dmin
        st.session_state.delay_max = max(dmin, dmax)
    else:
        col1, col2 = st.columns(2)
        with col1:
            ws = st.text_input("Giờ bắt đầu (HH:MM)", value=st.session_state.win_start)
        with col2:
            we = st.text_input("Giờ kết thúc (HH:MM)", value=st.session_state.win_end)
        st.session_state.timing_mode = "window"
        st.session_state.win_start = ws
        st.session_state.win_end = we

    st.divider()
    st.subheader("🌐 Proxy (tuỳ chọn)")
    proxy_raw = st.text_area(
        "Danh sách proxy (mỗi dòng 1 proxy, để trống nếu không dùng):",
        placeholder="http://103.152.112.162:80\nhttp://user:pass@45.77.56.114:8080",
        height=100
    )
    proxies = [p.strip() for p in proxy_raw.splitlines()
               if p.strip() and not p.strip().startswith("#")]
    st.session_state.proxies = proxies
    if proxies:
        st.caption(f"✅ {len(proxies)} proxy sẽ được xoay vòng")

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Quay lại"):
            st.session_state.step = 1
            st.rerun()
    with col2:
        if st.button("▶️ Bắt đầu", type="primary"):
            errors, warnings = _validate_before_run(
                st.session_state.configured,
                st.session_state.get("logic_rules", []),
                st.session_state.get("accuracy_mode", "balanced"),
            )
            if errors:
                st.error("Không thể bắt đầu do cấu hình chưa hợp lệ:")
                for e in errors[:8]:
                    st.markdown(f"- ❌ {e}")
                return
            for w in warnings[:5]:
                st.warning(f"⚠️ {w}")
            st.session_state.step = 3
            st.session_state.results = []
            st.rerun()


# ── Step 3: Running ───────────────────────────────────────────────────────────
def page_run():
    st.title("🚀 Đang chạy...")

    n = st.session_state.n_submissions
    configured = st.session_state.configured
    logic_rules = st.session_state.get("logic_rules", [])
    accuracy_mode = st.session_state.get("accuracy_mode", "balanced")
    form_id = st.session_state.form_id
    proxies = st.session_state.proxies
    fbzx = st.session_state.get("fbzx")

    precompute_answers(configured, n)
    st.session_state.pop("first_debug", None)

    errors, warnings = _validate_before_run(configured, logic_rules, accuracy_mode)
    if errors:
        st.error("Cấu hình hiện tại chưa hợp lệ, vui lòng quay lại bước cài đặt:")
        for e in errors[:8]:
            st.markdown(f"- ❌ {e}")
        if st.button("⬅️ Quay lại cài đặt"):
            st.session_state.step = 2
            st.rerun()
        return
    for w in warnings[:3]:
        st.warning(f"⚠️ {w}")

    schedule = None
    if st.session_state.timing_mode == "window":
        schedule = _schedule(n, st.session_state.win_start, st.session_state.win_end)
        st.info(f"📅 Lịch: {schedule[0].strftime('%H:%M:%S')} → {schedule[-1].strftime('%H:%M:%S')}")

    progress_bar = st.progress(0, text="Đang khởi động...")
    status_box = st.empty()
    log_box = st.empty()

    results = []
    log_lines = []

    for i in range(1, n + 1):
        if schedule:
            target = schedule[i - 1]
            wait = (target - datetime.datetime.now()).total_seconds()
            if wait > 0:
                status_box.info(f"⏳ [{i}/{n}] Chờ đến {target.strftime('%H:%M:%S')} ({wait:.0f}s)...")
                time.sleep(wait)

        proxy = proxies[(i - 1) % len(proxies)] if proxies else None
        try:
            success, answers, debug_info = submit_form(
                form_id,
                configured,
                submission_index=i - 1,
                proxy=proxy,
                fbzx=fbzx,
                logic_rules=logic_rules,
                accuracy_mode=accuracy_mode,
            )
        except TypeError as e:
            if "logic_rules" not in str(e) and "accuracy_mode" not in str(e):
                raise
            try:
                success, answers, debug_info = submit_form(
                    form_id,
                    configured,
                    submission_index=i - 1,
                    proxy=proxy,
                    fbzx=fbzx,
                    logic_rules=logic_rules,
                )
            except TypeError:
                success, answers, debug_info = submit_form(
                    form_id,
                    configured,
                    submission_index=i - 1,
                    proxy=proxy,
                    fbzx=fbzx,
                )
        if not success and debug_info:
            st.session_state["first_debug"] = debug_info
        results.append({"success": success, "answers": answers})

        icon = "✅" if success else "❌"
        txt = "OK" if success else "FAIL"
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        proxy_tag = f" `{proxy}`" if proxy else ""
        log_lines.append(f"`[{i:>4}/{n}]` {icon} **{txt}**{proxy_tag} — {ts}")

        progress_bar.progress(i / n, text=f"[{i}/{n}] {icon} {txt}")
        log_box.markdown("\n\n".join(log_lines[-15:]))

        if not schedule and i < n:
            time.sleep(random.uniform(st.session_state.delay_min, st.session_state.delay_max))

    # Report
    st.divider()
    ok = sum(1 for r in results if r["success"])
    fail = n - ok
    def _kpi_html(total_val: int, ok_val: int, fail_val: int) -> str:
        return f"""
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-label">Tổng submit</div>
                <div class="kpi-value">{total_val}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">✅ Thành công</div>
                <div class="kpi-value">{ok_val}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">❌ Thất bại</div>
                <div class="kpi-value">{fail_val}</div>
            </div>
        </div>
        """

    kpi_box = st.empty()
    frames = 18
    for frame in range(1, frames + 1):
        progress = frame / frames
        eased = 1 - (1 - progress) ** 3
        cur_n = int(round(n * eased))
        cur_ok = int(round(ok * eased))
        cur_fail = int(round(fail * eased))
        kpi_box.markdown(_kpi_html(cur_n, cur_ok, cur_fail), unsafe_allow_html=True)
        time.sleep(0.018)
    kpi_box.markdown(_kpi_html(n, ok, fail), unsafe_allow_html=True)
    if ok > 0:
        st.success(f"🎉 Hoàn thành! Tỉ lệ thành công: {ok/n*100:.1f}%")
    else:
        st.error("❌ Tất cả submit đều thất bại")

    if st.session_state.get("first_debug"):
        with st.expander("🔍 Debug response (Google trả về)", expanded=True):
            st.caption(f"Form ID: `{form_id}`")
            st.caption(f"Submit URL: `{SUBMIT_URL_TEMPLATE.format(form_id=form_id)}`")
            st.code(st.session_state["first_debug"][:800], language="html")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔄 Form khác"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    with c2:
        if st.button("⚙️ Chạy lại form này"):
            st.session_state.step = 1
            st.rerun()


# ── Router ────────────────────────────────────────────────────────────────────
_render_sidebar()
pages = {0: page_url, 1: page_configure, 2: page_settings, 3: page_run}
pages[st.session_state.step]()
