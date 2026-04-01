import json
import re
import requests

QUESTION_TYPES = {
    0: "short_text",
    1: "paragraph",
    2: "multiple_choice",
    3: "dropdown",
    4: "checkbox",
    5: "linear_scale",
    7: "grid_multiple_choice",
    9: "date",
    10: "time",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
}


def get_form_id(url: str) -> str:
    patterns = [
        r"/forms/d/e/([a-zA-Z0-9_-]+)/",
        r"/forms/d/([a-zA-Z0-9_-]+)/",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError("Không tìm được Form ID từ URL.")


def parse_form(url: str) -> list:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        source = resp.text
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Không thể tải form: {e}")

    match = re.search(r"FB_PUBLIC_LOAD_DATA_ = (.*?);</script>", source, re.DOTALL)
    if not match:
        raise ValueError("Không thể đọc dữ liệu form. Đảm bảo form công khai.")

    raw_data = json.loads(match.group(1))

    try:
        raw_questions = raw_data[1][1]
    except (IndexError, TypeError):
        raise ValueError("Cấu trúc form không nhận dạng được.")

    questions = []

    for item in raw_questions:
        try:
            q_text = item[1] or "(Không có tiêu đề)"
            q_type_code = item[3]
            q_type = QUESTION_TYPES.get(q_type_code, "unknown")
            entry_data = item[4] if len(item) > 4 else None
            if not entry_data:
                continue

            # ── GRID: mỗi hàng có entry_id riêng ──
            if q_type == "grid_multiple_choice":
                # Lấy options cột từ hàng đầu tiên
                col_options = []
                try:
                    if entry_data[0][1]:
                        col_options = [o[0] for o in entry_data[0][1] if o and o[0]]
                except Exception:
                    pass

                for row_entry in entry_data:
                    row_id = row_entry[0]
                    # Tên hàng thường ở index 3[0]
                    row_label = ""
                    try:
                        row_label = row_entry[3][0]
                    except Exception:
                        pass
                    if not row_label:
                        row_label = str(row_id)

                    questions.append({
                        "text": q_text + " -> " + row_label,
                        "type": "multiple_choice",
                        "type_code": q_type_code,
                        "entry_id": str(row_id),
                        "options": col_options,
                        "ratios": [],
                        "answers": [],
                        "is_grid_row": True,
                        "grid_title": q_text,
                        "row_label": row_label,
                    })
                continue

            # ── Câu hỏi thông thường ──
            first_entry = entry_data[0]
            entry_id = first_entry[0]
            options = []

            if q_type in ("multiple_choice", "dropdown", "checkbox"):
                try:
                    if first_entry[1]:
                        options = [o[0] for o in first_entry[1] if o and o[0]]
                except Exception:
                    pass

            elif q_type == "linear_scale":
                try:
                    low = int(first_entry[3][0])
                    high = int(first_entry[3][1])
                    options = [str(i) for i in range(low, high + 1)]
                except Exception:
                    options = [str(i) for i in range(1, 6)]

            questions.append({
                "text": q_text,
                "type": q_type,
                "type_code": q_type_code,
                "entry_id": str(entry_id),
                "options": options,
                "ratios": [],
                "answers": [],
            })

        except Exception:
            continue

    if not questions:
        raise ValueError("Không tìm thấy câu hỏi nào trong form.")

    return questions
