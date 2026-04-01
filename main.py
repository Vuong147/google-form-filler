import datetime
import os
import random
import sys
import time

from config import configure_ratios, get_run_settings
from parser import get_form_id, parse_form
from reporter import generate_report
from submitter import submit_form, precompute_answers


def _load_proxies() -> list:
    proxy_file = os.path.join(os.path.dirname(__file__), "proxies.txt")
    if not os.path.exists(proxy_file):
        return []
    proxies = []
    with open(proxy_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                proxies.append(line)
    return proxies


def _ask_proxy_settings(proxies: list):
    if not proxies:
        print("ℹ️  Không tìm thấy proxy nào trong proxies.txt → chạy không có proxy.")
        return False
    print(f"\n🌐 Tìm thấy {len(proxies)} proxy trong proxies.txt")
    while True:
        choice = input("  Dùng proxy không? (y/n): ").strip().lower()
        if choice in ("y", "n"):
            return choice == "y"
        print("  ⚠️  Nhập y hoặc n.")


def _schedule_submissions(n: int, win_start: str, win_end: str) -> list:
    """Generate n sorted random datetimes within today's time window."""
    now = datetime.datetime.now()
    today = now.date()

    sh, sm = map(int, win_start.split(":"))
    eh, em = map(int, win_end.split(":"))

    start_dt = datetime.datetime.combine(today, datetime.time(sh, sm))
    end_dt = datetime.datetime.combine(today, datetime.time(eh, em))

    if end_dt <= now:
        start_dt += datetime.timedelta(days=1)
        end_dt += datetime.timedelta(days=1)
    elif start_dt < now:
        start_dt = now + datetime.timedelta(seconds=2)

    total_sec = (end_dt - start_dt).total_seconds()
    offsets = sorted(random.uniform(0, total_sec) for _ in range(n))
    return [start_dt + datetime.timedelta(seconds=s) for s in offsets]


def _banner():
    print()
    print("╔══════════════════════════════════════════════════════╗")
    print("║         🤖  GOOGLE FORM AUTO FILLER  🤖              ║")
    print("║         Tự động điền form theo tỉ lệ                 ║")
    print("╚══════════════════════════════════════════════════════╝")
    print()


def main():
    _banner()

    url = input("🔗 Nhập URL Google Form: ").strip()
    if not url:
        print("❌ URL không được để trống.")
        sys.exit(1)

    # Normalize viewform URL
    if "viewform" not in url and "formResponse" not in url:
        if not url.endswith("/"):
            url += "/viewform"
        else:
            url += "viewform"

    print("\n⏳ Đang phân tích form (mở trình duyệt ẩn)...")

    try:
        questions = parse_form(url)
        form_id = get_form_id(url)
    except Exception as e:
        print(f"\n❌ Lỗi khi phân tích form: {e}")
        sys.exit(1)

    supported = [
        q for q in questions
        if q["type"] in ("multiple_choice", "dropdown", "checkbox",
                          "linear_scale", "short_text", "paragraph",
                          "date", "time")
    ]

    print(f"✅ Tìm thấy {len(questions)} câu hỏi "
          f"({len(supported)} loại được hỗ trợ)\n")

    if not supported:
        print("❌ Không có câu hỏi nào được hỗ trợ.")
        sys.exit(1)

    # Run settings
    n_submissions, delay_min, delay_max, win_start, win_end = get_run_settings()

    # Config ratios
    configured = configure_ratios(questions, n_submissions)

    # Proxy
    proxies = _load_proxies()
    use_proxy = _ask_proxy_settings(proxies)

    # Schedule
    schedule = None
    if win_start:
        schedule = _schedule_submissions(n_submissions, win_start, win_end)
        print(f"\n📅 Lịch submit ({win_start} - {win_end}):")
        for idx, t in enumerate(schedule, 1):
            print(f"   Lần {idx:>3}: {t.strftime('%H:%M:%S')}")

    # Confirm
    proxy_info = f" | Proxy: {len(proxies)} cái (xoay vòng)" if use_proxy else ""
    if win_start:
        timing_info = f"Khung giờ: {win_start} - {win_end}"
    else:
        timing_info = f"Delay: {delay_min:.1f}~{delay_max:.1f}s mỗi lần"
    print(f"\n📋 Sẽ submit {n_submissions} lần | {timing_info}{proxy_info}\n")
    confirm = input("▶️  Bắt đầu? (Enter để tiếp tục / Ctrl+C để hủy): ")

    print("\n" + "═" * 55)
    print("   🚀 ĐANG CHẠY...")
    print("═" * 55 + "\n")

    precompute_answers(configured, n_submissions)

    results = []
    start_time = time.time()

    for i in range(1, n_submissions + 1):
        if schedule:
            target = schedule[i - 1]
            wait = (target - datetime.datetime.now()).total_seconds()
            if wait > 0:
                print(f"  [{i:>4}/{n_submissions}] ⏳ Chờ đến {target.strftime('%H:%M:%S')} "
                      f"({wait:.0f}s)...")
                time.sleep(wait)

        proxy = proxies[(i - 1) % len(proxies)] if use_proxy and proxies else None
        success, answers = submit_form(
            form_id, configured, submission_index=i - 1, proxy=proxy
        )
        results.append({"success": success, "answers": answers})

        status_icon = "✅" if success else "❌"
        status_txt = "OK" if success else "FAIL"
        proxy_tag = f" [{proxy}]" if proxy else ""
        time_tag = f" lúc {datetime.datetime.now().strftime('%H:%M:%S')}"

        if not schedule and i < n_submissions:
            delay = random.uniform(delay_min, delay_max)
            print(f"  [{i:>4}/{n_submissions}] {status_icon} {status_txt}{proxy_tag}  "
                  f"→ chờ {delay:.1f}s")
            time.sleep(delay)
        else:
            print(f"  [{i:>4}/{n_submissions}] {status_icon} {status_txt}{proxy_tag}{time_tag}")

    elapsed = time.time() - start_time

    # Report
    generate_report(results, configured, elapsed)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⛔ Đã hủy bởi người dùng.")
        sys.exit(0)
