def _print_separator(char="─", width=55):
    print(char * width)


def _ask_ratios(options: list, q_index: int) -> list:
    """Ask user to input ratios for a list of options. Returns normalized float list."""
    while True:
        print(f"\n  Các lựa chọn:")
        for i, opt in enumerate(options, 1):
            print(f"    [{i}] {opt}")

        raw = input(
            f"\n  Nhập tỉ lệ cho {len(options)} lựa chọn "
            f"(cách nhau bằng dấu cách, ví dụ: {' '.join(['30'] + ['20'] * (len(options)-1))}): "
        ).strip()

        parts = raw.split()
        if len(parts) != len(options):
            print(f"  ⚠️  Cần đúng {len(options)} số. Nhập lại.")
            continue

        try:
            values = [float(v) for v in parts]
            if any(v < 0 for v in values):
                print("  ⚠️  Tỉ lệ không được âm. Nhập lại.")
                continue
            total = sum(values)
            if total == 0:
                print("  ⚠️  Tổng tỉ lệ phải > 0. Nhập lại.")
                continue
            # Normalize
            normalized = [v / total for v in values]
            print(f"  ✅ Tỉ lệ: {' | '.join(f'{opt}: {v*100:.1f}%' for opt, v in zip(options, normalized))}")
            return normalized
        except ValueError:
            print("  ⚠️  Chỉ nhập số. Ví dụ: 40 30 30")


def _ask_text_answers(q_index: int) -> tuple:
    """Ask user to provide text answers and their ratios for text questions."""
    print("\n  ℹ️  Câu hỏi văn bản: nhập các câu trả lời mẫu (dòng trống để kết thúc):")

    answers = []
    i = 1
    while True:
        ans = input(f"    Câu trả lời [{i}]: ").strip()
        if ans == "":
            if len(answers) == 0:
                print("  ⚠️  Cần ít nhất 1 câu trả lời.")
                continue
            break
        answers.append(ans)
        i += 1

    equal = [1.0 / len(answers)] * len(answers)
    return answers, equal, False


def _ask_text_answers_sequential(n: int) -> tuple:
    """Ask user to provide exactly n answers, one per submission."""
    print(f"\n  ℹ️  Nhập {n} câu trả lời cho {n} lần submit (theo thứ tự):")
    answers = []
    for i in range(1, n + 1):
        while True:
            ans = input(f"    Lần [{i:>3}]: ").strip()
            if ans == "":
                print("  ⚠️  Không được để trống.")
                continue
            answers.append(ans)
            break
    return answers, [1.0] * n, True


def configure_ratios(questions: list, n_submissions: int = 1) -> list:
    """Interactive terminal configuration of answer ratios for each question."""
    print()
    _print_separator("═")
    print("   ⚙️  CÀI ĐẶT TỈ LỆ CÂU TRẢ LỜI")
    _print_separator("═")

    for i, q in enumerate(questions, 1):
        print(f"\n📌 Câu {i}: {q['text']}")
        print(f"   Loại: {q['type']}")

        if q["type"] in ("multiple_choice", "dropdown") and q["options"]:
            q["ratios"] = _ask_ratios(q["options"], i)

        elif q["type"] == "checkbox" and q["options"]:
            print(f"\n  ℹ️  Checkbox: nhập xác suất chọn mỗi ô (0-100):")
            while True:
                raw = input(
                    f"  Xác suất cho {len(q['options'])} ô "
                    f"(ví dụ: {' '.join(['50'] * len(q['options']))}): "
                ).strip()
                parts = raw.split()
                if len(parts) != len(q["options"]):
                    print(f"  ⚠️  Cần đúng {len(q['options'])} số.")
                    continue
                try:
                    probs = [max(0.0, min(100.0, float(v))) / 100 for v in parts]
                    for opt, p in zip(q["options"], probs):
                        print(f"    {opt}: {p*100:.0f}%")
                    q["ratios"] = probs
                    break
                except ValueError:
                    print("  ⚠️  Chỉ nhập số 0-100.")

        elif q["type"] == "linear_scale" and q["options"]:
            print(f"  Thang điểm: {q['options'][0]} → {q['options'][-1]}")
            q["ratios"] = _ask_ratios(q["options"], i)

        elif q["type"] in ("short_text", "paragraph"):
            if n_submissions > 1:
                print(f"\n  Chọn cách nhập câu trả lời:")
                print(f"    [1] Nhập {n_submissions} câu riêng cho từng lần submit (theo thứ tự)")
                print(f"    [2] Nhập pool câu trả lời, tool random chọn")
                while True:
                    choice = input("  Chọn (1/2): ").strip()
                    if choice in ("1", "2"):
                        break
                    print("  ⚠️  Nhập 1 hoặc 2.")
                if choice == "1":
                    q["answers"], q["ratios"], q["per_submission"] = _ask_text_answers_sequential(n_submissions)
                else:
                    q["answers"], q["ratios"], q["per_submission"] = _ask_text_answers(i)
            else:
                q["answers"], q["ratios"], q["per_submission"] = _ask_text_answers(i)

        elif q["type"] in ("date", "time"):
            print(f"\n  ℹ️  Câu hỏi {q['type']}: nhập các giá trị mẫu (dòng trống để kết thúc):")
            answers = []
            fmt = "YYYY-MM-DD" if q["type"] == "date" else "HH:MM"
            idx = 1
            while True:
                ans = input(f"    Giá trị [{idx}] ({fmt}): ").strip()
                if ans == "":
                    if not answers:
                        print("  ⚠️  Cần ít nhất 1 giá trị.")
                        continue
                    break
                answers.append(ans)
                idx += 1
            q["answers"] = answers
            q["ratios"] = [1.0 / len(answers)] * len(answers)

        else:
            print("  ⚠️  Loại câu hỏi không hỗ trợ, sẽ bỏ qua.")
            q["skip"] = True

    return questions


def _parse_hhmm(s: str):
    """Parse HH:MM string, return (hour, minute) or None."""
    try:
        parts = s.strip().split(":")
        if len(parts) != 2:
            return None
        h, m = int(parts[0]), int(parts[1])
        if 0 <= h <= 23 and 0 <= m <= 59:
            return h, m
    except ValueError:
        pass
    return None


def get_run_settings() -> tuple:
    """Get number of submissions and timing settings from user.
    Returns (n, d_min, d_max, win_start, win_end)
    win_start/win_end are 'HH:MM' strings or None if not using window mode.
    """
    print()
    _print_separator("═")
    print("   🚀 CÀI ĐẶT CHẠY")
    _print_separator("═")

    while True:
        try:
            n = int(input("\nSố lần submit: ").strip())
            if n <= 0:
                print("⚠️  Nhập số > 0.")
                continue
            break
        except ValueError:
            print("⚠️  Nhập số nguyên.")

    print("\nChế độ thời gian:")
    print("  [1] Delay ngẫu nhiên giữa mỗi lần (giây)")
    print("  [2] Rải đều trong khung giờ (HH:MM - HH:MM)")
    while True:
        mode = input("Chọn (1/2): ").strip()
        if mode in ("1", "2"):
            break
        print("⚠️  Nhập 1 hoặc 2.")

    if mode == "1":
        while True:
            try:
                raw = input("Delay ngẫu nhiên giữa mỗi lần (giây, ví dụ: 2 5): ").strip()
                parts = raw.split()
                if len(parts) == 1:
                    d_min = d_max = float(parts[0])
                elif len(parts) == 2:
                    d_min, d_max = float(parts[0]), float(parts[1])
                    if d_min > d_max:
                        d_min, d_max = d_max, d_min
                else:
                    print("⚠️  Nhập 1 hoặc 2 số.")
                    continue
                if d_min < 0:
                    print("⚠️  Delay không được âm.")
                    continue
                break
            except ValueError:
                print("⚠️  Nhập số hợp lệ.")
        return n, d_min, d_max, None, None

    else:
        while True:
            raw = input("Khung giờ bắt đầu (HH:MM, ví dụ: 08:00): ").strip()
            win_start = _parse_hhmm(raw)
            if win_start:
                break
            print("⚠️  Định dạng sai. Ví dụ: 08:00")

        while True:
            raw = input("Khung giờ kết thúc (HH:MM, ví dụ: 22:00): ").strip()
            win_end = _parse_hhmm(raw)
            if not win_end:
                print("⚠️  Định dạng sai. Ví dụ: 22:00")
                continue
            if (win_end[0] * 60 + win_end[1]) <= (win_start[0] * 60 + win_start[1]):
                print("⚠️  Giờ kết thúc phải sau giờ bắt đầu.")
                continue
            break

        ws = f"{win_start[0]:02d}:{win_start[1]:02d}"
        we = f"{win_end[0]:02d}:{win_end[1]:02d}"
        return n, 0, 0, ws, we
