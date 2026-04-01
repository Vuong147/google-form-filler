from collections import defaultdict, Counter


def _fmt_time(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f} giây"
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins} phút {secs} giây"


def _print_separator(char="─", width=55):
    print(char * width)


def generate_report(results: list, questions: list, elapsed: float):
    """Print detailed report after all submissions."""
    total = len(results)
    success_count = sum(1 for r in results if r["success"])
    fail_count = total - success_count

    print("\n")
    _print_separator("═")
    print("   📊 BÁO CÁO KẾT QUẢ")
    _print_separator("═")
    print(f"\n  Tổng submit     : {total}")
    print(f"  ✅ Thành công   : {success_count}  ({success_count/total*100:.1f}%)")
    print(f"  ❌ Thất bại     : {fail_count}  ({fail_count/total*100:.1f}%)")
    print(f"  ⏱️  Thời gian    : {_fmt_time(elapsed)}")
    if total > 0:
        avg_time = elapsed / total
        print(f"  ⚡ Trung bình/lần: {avg_time:.2f} giây")

    # Build distribution per question
    answer_counts = defaultdict(list)
    for r in results:
        if r["success"]:
            for q_text, answer in r["answers"].items():
                answer_counts[q_text].append(answer)

    if not answer_counts:
        _print_separator()
        return

    print(f"\n{'─'*55}")
    print("  📈 PHÂN PHỐI CÂU TRẢ LỜI THỰC TẾ")
    print(f"{'─'*55}")

    for q in questions:
        q_text = q["text"]
        if q_text not in answer_counts:
            continue

        raw_answers = answer_counts[q_text]
        n_answered = len(raw_answers)

        print(f"\n  ❓ {q_text}")

        if q["type"] == "checkbox":
            # Flatten list of lists
            flat = []
            for ans in raw_answers:
                if isinstance(ans, list):
                    flat.extend(ans)
                else:
                    flat.append(ans)
            counter = Counter(flat)
            for opt in q.get("options", []) + [k for k in counter if k not in q.get("options", [])]:
                c = counter.get(opt, 0)
                pct = c / n_answered * 100 if n_answered else 0
                target_pct = 0
                ratios = q.get("ratios", [])
                opts = q.get("options", [])
                if opt in opts:
                    idx = opts.index(opt)
                    target_pct = ratios[idx] * 100 if idx < len(ratios) else 0
                bar = "█" * int(pct / 5)
                print(f"    {opt[:35]:<35} {c:>4}次  {pct:5.1f}%  (mục tiêu: {target_pct:.0f}%)  {bar}")
        else:
            # Flatten if needed
            flat = []
            for ans in raw_answers:
                if isinstance(ans, list):
                    flat.extend(ans)
                else:
                    flat.append(str(ans))

            counter = Counter(flat)
            options_order = q.get("options") or q.get("answers") or list(counter.keys())
            seen = set()
            display_opts = []
            for o in options_order:
                if o not in seen:
                    display_opts.append(o)
                    seen.add(o)
            for o in counter:
                if o not in seen:
                    display_opts.append(o)

            for opt in display_opts:
                c = counter.get(opt, 0)
                pct = c / n_answered * 100 if n_answered else 0

                # Find target ratio
                all_opts = q.get("options") or q.get("answers") or []
                ratios = q.get("ratios", [])
                target_pct = 0
                if opt in all_opts:
                    idx = all_opts.index(opt)
                    if idx < len(ratios):
                        target_pct = ratios[idx] * 100

                bar = "█" * int(pct / 5)
                label = str(opt)[:35]
                print(f"    {label:<35} {c:>4}  {pct:5.1f}%  (mục tiêu: {target_pct:.0f}%)  {bar}")

    _print_separator("═")
    print("  ✅ Hoàn tất!")
    _print_separator("═")
    print()
