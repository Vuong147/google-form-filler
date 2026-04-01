import base64
import datetime
import math
import os
import random
import time

import streamlit as st

from parser import parse_form, get_form_id
from submitter import submit_form, precompute_answers

st.set_page_config(page_title="Tool của a zai Hàn Quốc", page_icon="🤖", layout="centered")

st.markdown("""
<style>
    /* Nền gradient toàn trang */
    .stApp {
        background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
    }
    /* Tiêu đề chính */
    h1 { color: #e0c3fc !important; letter-spacing: 1px; }
    h2, h3 { color: #a78bfa !important; }
    /* Input box */
    .stTextInput > div > div > input {
        background: rgba(255,255,255,0.08);
        color: #fff;
        border: 1px solid #7c3aed;
        border-radius: 10px;
    }
    /* Nút bấm chính */
    .stButton > button[kind="primary"] {
        background: linear-gradient(90deg, #7c3aed, #a855f7);
        color: white;
        border: none;
        border-radius: 10px;
        font-weight: bold;
        padding: 0.5rem 2rem;
        transition: 0.3s;
    }
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(90deg, #6d28d9, #9333ea);
        transform: scale(1.03);
    }
    /* Card expander */
    .streamlit-expanderHeader {
        background: rgba(124,58,237,0.15);
        border-radius: 8px;
        color: #e0c3fc !important;
    }
    /* Divider */
    hr { border-color: #7c3aed44; }
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: rgba(15,12,41,0.95);
        border-right: 1px solid #7c3aed44;
    }
    /* Ảnh avatar tòn đẹp */
    .avatar-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 1.5rem 0 1rem 0;
    }
    .avatar-container img {
        border-radius: 16px;
        border: 3px solid #a855f7;
        box-shadow: 0 0 20px #7c3aed88;
        width: 100%;
        object-fit: cover;
    }
    .avatar-name {
        color: #e0c3fc;
        font-size: 1rem;
        font-weight: 600;
        margin-top: 0.6rem;
        text-align: center;
    }
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
                questions = parse_form(u)
                form_id = get_form_id(u)
                st.session_state.questions = questions
                st.session_state.form_id = form_id
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

    col_n, col_btn = st.columns([2, 1])
    with col_n:
        n = st.number_input("Số lần submit", min_value=1, max_value=10000,
                            value=st.session_state.n_submissions, step=1)
        st.session_state.n_submissions = int(n)
    with col_btn:
        st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)
        if st.button("🎯 Tự động điều chỉnh"):
            global_lcm = 1
            for q in questions:
                if q["type"] in ("multiple_choice", "dropdown", "linear_scale") and q.get("options"):
                    n_opts = len(q["options"])
                    global_lcm = global_lcm * n_opts // math.gcd(global_lcm, n_opts)
            cur = st.session_state.n_submissions
            if cur % global_lcm != 0:
                adjusted = math.ceil(cur / global_lcm) * global_lcm
                st.session_state.n_submissions = adjusted
                st.rerun()
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

    st.divider()
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
        success, answers = submit_form(form_id, configured, submission_index=i - 1, proxy=proxy)
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
    st.success(f"🎉 Hoàn thành! Tỉ lệ thành công: {ok/n*100:.1f}%")

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
