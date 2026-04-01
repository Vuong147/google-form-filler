import base64
import datetime
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
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* ── Animated aurora background ── */
    .stApp {
        font-family: 'Inter', sans-serif;
        background: #060612;
        overflow-x: hidden;
    }
    .stApp::before {
        content: '';
        position: fixed;
        top: -40%;
        left: -20%;
        width: 70%;
        height: 70%;
        background: radial-gradient(ellipse, #7c3aed55 0%, transparent 70%);
        animation: blob1 12s ease-in-out infinite alternate;
        pointer-events: none;
        z-index: 0;
    }
    .stApp::after {
        content: '';
        position: fixed;
        bottom: -30%;
        right: -10%;
        width: 60%;
        height: 60%;
        background: radial-gradient(ellipse, #0ea5e955 0%, transparent 70%);
        animation: blob2 15s ease-in-out infinite alternate;
        pointer-events: none;
        z-index: 0;
    }
    @keyframes blob1 {
        0%   { transform: translate(0, 0) scale(1); }
        50%  { transform: translate(8%, 12%) scale(1.15); }
        100% { transform: translate(-5%, 5%) scale(0.95); }
    }
    @keyframes blob2 {
        0%   { transform: translate(0, 0) scale(1); }
        50%  { transform: translate(-10%, -8%) scale(1.2); }
        100% { transform: translate(5%, 10%) scale(0.9); }
    }

    /* ── Typography ── */
    h1 { color: #f0e6ff !important; letter-spacing: -0.5px; font-weight: 700 !important; }
    h2, h3 { color: #c4b5fd !important; font-weight: 600 !important; }
    p, label, .stMarkdown { color: #cbd5e1 !important; }

    /* ── Main content area ── */
    .block-container {
        background: rgba(255,255,255,0.03);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 20px;
        padding: 2rem 2.5rem !important;
        box-shadow: 0 8px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.05);
    }

    /* ── Inputs ── */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stTextArea > div > div > textarea {
        background: rgba(255,255,255,0.06) !important;
        color: #f0e6ff !important;
        border: 1px solid rgba(167,139,250,0.35) !important;
        border-radius: 12px !important;
        backdrop-filter: blur(10px);
        transition: border-color 0.2s, box-shadow 0.2s;
    }
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #a855f7 !important;
        box-shadow: 0 0 0 3px rgba(168,85,247,0.18) !important;
    }

    /* ── Selectbox / Radio ── */
    .stSelectbox > div > div,
    .stRadio > div {
        background: rgba(255,255,255,0.05) !important;
        border-radius: 12px;
        color: #f0e6ff !important;
    }

    /* ── Primary button ── */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #7c3aed, #06b6d4);
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        padding: 0.55rem 2rem !important;
        box-shadow: 0 4px 20px rgba(124,58,237,0.45);
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 30px rgba(124,58,237,0.6);
    }
    /* ── Secondary button ── */
    .stButton > button:not([kind="primary"]) {
        background: rgba(255,255,255,0.07) !important;
        color: #c4b5fd !important;
        border: 1px solid rgba(167,139,250,0.3) !important;
        border-radius: 12px !important;
        font-weight: 500 !important;
        transition: background 0.2s, transform 0.2s;
    }
    .stButton > button:not([kind="primary"]):hover {
        background: rgba(167,139,250,0.15) !important;
        transform: translateY(-1px);
    }

    /* ── Expander ── */
    .streamlit-expanderHeader {
        background: rgba(124,58,237,0.12) !important;
        border: 1px solid rgba(167,139,250,0.2) !important;
        border-radius: 12px !important;
        color: #e0c3fc !important;
    }
    .streamlit-expanderContent {
        background: rgba(255,255,255,0.02) !important;
        border: 1px solid rgba(167,139,250,0.1) !important;
        border-top: none !important;
        border-radius: 0 0 12px 12px !important;
    }

    /* ── Metric cards ── */
    [data-testid="stMetric"] {
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(167,139,250,0.2);
        border-radius: 16px;
        padding: 1rem;
        backdrop-filter: blur(10px);
        box-shadow: 0 4px 16px rgba(0,0,0,0.2);
    }
    [data-testid="stMetricValue"] { color: #f0e6ff !important; font-weight: 700 !important; }

    /* ── Progress bar ── */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, #7c3aed, #06b6d4) !important;
        border-radius: 99px;
    }
    .stProgress > div > div {
        background: rgba(255,255,255,0.08) !important;
        border-radius: 99px;
    }

    /* ── Alert / Info / Success / Warning ── */
    .stAlert {
        border-radius: 12px !important;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255,255,255,0.1) !important;
    }

    /* ── Divider ── */
    hr { border-color: rgba(167,139,250,0.2) !important; }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: rgba(6,6,18,0.85) !important;
        backdrop-filter: blur(24px);
        border-right: 1px solid rgba(124,58,237,0.25) !important;
    }
    [data-testid="stSidebar"] > div:first-child {
        background: transparent !important;
    }

    /* ── Avatar ── */
    .avatar-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 1.5rem 0 1rem 0;
    }
    .avatar-container img {
        border-radius: 18px;
        border: 2px solid rgba(168,85,247,0.6);
        box-shadow: 0 0 30px rgba(124,58,237,0.5), 0 0 60px rgba(6,182,212,0.15);
        width: 100%;
        object-fit: cover;
        transition: box-shadow 0.3s;
    }
    .avatar-name {
        color: #e0c3fc;
        font-size: 0.95rem;
        font-weight: 600;
        margin-top: 0.7rem;
        text-align: center;
        letter-spacing: 0.3px;
    }

    /* ── Code block ── */
    .stCodeBlock {
        border-radius: 12px !important;
        border: 1px solid rgba(167,139,250,0.15) !important;
    }

    /* ── Scrollbar ── */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(167,139,250,0.4); border-radius: 99px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(167,139,250,0.7); }
</style>
""", unsafe_allow_html=True)

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")

SUPPORTED_TYPES = ("multiple_choice", "dropdown", "checkbox", "linear_scale",
                   "short_text", "paragraph", "date", "time")


# ── Init session state ────────────────────────────────────────────────────────
def _init():
    defaults = {
        "step": 0, "questions": [], "form_id": "", "url": "",
        "configured": [], "n_submissions": 10,
        "timing_mode": "delay", "delay_min": 2.0, "delay_max": 5.0,
        "win_start": "08:00", "win_end": "22:00",
        "proxies": [], "use_proxy": False,
        "results": [], "log": [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init()


# ── Sidebar: ảnh + nhạc ────────────────────────────────────────────────────────
def _render_sidebar():
    with st.sidebar:
        # Ảnh avatar
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
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="avatar-container"><div style="color:#a78bfa;font-size:3rem">👤</div></div>',
                        unsafe_allow_html=True)

        st.markdown('<div class="avatar-name">🤖 Tool của a zai Hàn Quốc</div>', unsafe_allow_html=True)
        st.divider()

        # Nhạc nền autoplay
        music_path = os.path.join(ASSETS_DIR, "music.mp3")
        if os.path.exists(music_path):
            st.markdown("**🎵 Nhạc nền**")
            with open(music_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            st.markdown(
                f'<audio autoplay loop controls style="width:100%;margin-top:4px">'
                f'<source src="data:audio/mp3;base64,{b64}" type="audio/mp3">'
                f'</audio>',
                unsafe_allow_html=True
            )
        else:
            st.caption("⚠️ Chưa có file nhạc.\nThêm `assets/music.mp3` vào project.")

        st.divider()
        # Bước hiện tại
        steps = ["Nhập URL", "Cài đặt câu hỏi", "Cài đặt chạy", "Đang chạy"]
        for idx, label in enumerate(steps):
            icon = "✅" if idx < st.session_state.step else ("🔵" if idx == st.session_state.step else "⚪")
            st.markdown(f"{icon} {label}")


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

    if st.button("Phân tích Form", type="primary", disabled=not url.strip()):
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
                    min_n = _min_n_for_exact(cfg["ratios"])
                    n_cur = st.session_state.n_submissions
                    if n_cur % min_n == 0:
                        st.success(f"✅ {n_cur} lần submit → chia đúng tỉ lệ (bội số của {min_n})")
                    else:
                        suggested = [min_n * k for k in range(1, 6) if min_n * k >= n_cur]
                        nearest = suggested[0] if suggested else min_n
                        st.warning(f"⚠️ {n_cur} lần không chia đúng tỉ lệ cho câu này. "
                                   f"Nên dùng bội số của **{min_n}** → gần nhất: **{nearest}** lần")

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
                per_sub = False
                if st.session_state.n_submissions > 1:
                    mode = st.radio("Chế độ:",
                                    ["Pool (random chọn)",
                                     f"Theo thứ tự ({st.session_state.n_submissions} câu)"],
                                    key=f"q{i}_mode", horizontal=True)
                    per_sub = "thứ tự" in mode

                if per_sub:
                    answers = []
                    st.write(f"Nhập {st.session_state.n_submissions} câu trả lời:")
                    for k in range(st.session_state.n_submissions):
                        ans = st.text_input(f"Lần {k+1}", key=f"q{i}_s{k}")
                        answers.append(ans)
                    if any(not a.strip() for a in answers):
                        st.warning("⚠️ Không được để trống")
                        valid = False
                    cfg["answers"] = answers
                    cfg["ratios"] = [1.0] * len(answers)
                    cfg["per_submission"] = True
                else:
                    raw = st.text_area("Câu trả lời mẫu (mỗi dòng 1 câu):",
                                       key=f"q{i}_pool",
                                       placeholder="Câu trả lời 1\nCâu trả lời 2\n...")
                    answers = [a.strip() for a in raw.splitlines() if a.strip()]
                    if not answers:
                        st.warning("⚠️ Cần ít nhất 1 câu trả lời")
                        valid = False
                    cfg["answers"] = answers
                    cfg["ratios"] = ([1.0 / len(answers)] * len(answers)) if answers else []
                    cfg["per_submission"] = False

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
            st.session_state.step = 2
            st.rerun()


# ── Step 2: Run settings ──────────────────────────────────────────────────────
def page_settings():
    st.title("🚀 Cài đặt chạy")

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
            st.session_state.step = 3
            st.session_state.results = []
            st.rerun()


# ── Step 3: Running ───────────────────────────────────────────────────────────
def page_run():
    st.title("🚀 Đang chạy...")

    n = st.session_state.n_submissions
    configured = st.session_state.configured
    form_id = st.session_state.form_id
    proxies = st.session_state.proxies
    fbzx = st.session_state.get("fbzx")

    precompute_answers(configured, n)

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
        success, answers, debug_info = submit_form(form_id, configured, submission_index=i - 1, proxy=proxy, fbzx=fbzx)
        if not success and debug_info and "first_debug" not in st.session_state:
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
    col1, col2, col3 = st.columns(3)
    col1.metric("Tổng submit", n)
    col2.metric("✅ Thành công", ok)
    col3.metric("❌ Thất bại", fail)
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
