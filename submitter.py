import random
import requests
import time

SUBMIT_URL_TEMPLATE = "https://docs.google.com/forms/d/e/{form_id}/formResponse"

HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Referer": "https://docs.google.com/",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}

# Các chuỗi xuất hiện trong trang cảm ơn của Google Forms
SUCCESS_MARKERS = [
    "freebirdFormviewerViewResponseConfirmationMessage",
    "Your response has been recorded",
    "Phản hồi của bạn đã được ghi lại",
    "submitSuccessMessage",
    "fbzx",  # fallback: nếu có fbzx mà không có input form = đã submit xong
]

ERROR_MARKERS = [
    "freebirdFormviewerViewItemList",  # còn trang form = chưa submit được
    "Is required",
    "required",
]


def is_success(html: str) -> bool:
    """Detect if response HTML is the confirmation page."""
    # Trang xác nhận thành công có chứa marker này
    if "freebirdFormviewerViewResponseConfirmationMessage" in html:
        return True
    # Nếu vẫn còn trang form (có list câu hỏi) = thất bại
    if "freebirdFormviewerViewItemList" in html:
        return False
    # Fallback: status 200 và không có dấu hiệu lỗi
    return True


def pick_answer(question: dict, idx: int = 0):
    q_type = question.get("type")
    options = question.get("options", [])
    ratios = question.get("ratios", [])
    answers = question.get("answers", [])
    per_submission = question.get("per_submission", False)

    if q_type in ("multiple_choice", "dropdown", "linear_scale"):
        if not options or not ratios:
            return None
        return random.choices(options, weights=ratios, k=1)[0]

    elif q_type == "checkbox":
        if not options or not ratios:
            return []
        selected = [opt for opt, prob in zip(options, ratios) if random.random() < prob]
        if not selected and options:
            selected = [random.choice(options)]
        return selected

    elif q_type in ("short_text", "paragraph"):
        if not answers:
            return ""
        if per_submission:
            return answers[idx % len(answers)]
        return random.choices(answers, weights=ratios, k=1)[0]

    elif q_type in ("date", "time"):
        if not answers:
            return ""
        return random.choice(answers)

    return None


def build_payload(questions: list, idx: int = 0) -> tuple:
    data = {}
    chosen = {}

    for q in questions:
        if q.get("skip"):
            continue

        entry_key = f"entry.{q['entry_id']}"
        answer = pick_answer(q, idx)

        if answer is None:
            continue

        if isinstance(answer, list):
            if answer:
                data[entry_key] = answer
            chosen[q["text"]] = answer if answer else ["(không chọn)"]
        else:
            data[entry_key] = answer
            chosen[q["text"]] = answer

    return data, chosen


def submit_form(form_id: str, questions: list, timeout: int = 15,
                submission_index: int = 0, proxy: str = None) -> tuple:
    url = SUBMIT_URL_TEMPLATE.format(form_id=form_id)
    payload, chosen = build_payload(questions, submission_index)

    proxies = None
    if proxy:
        proxies = {"http": proxy, "https": proxy}

    try:
        resp = requests.post(
            url, data=payload, headers=HEADERS,
            timeout=timeout, allow_redirects=True,
            proxies=proxies
        )
        if resp.status_code != 200:
            return False, chosen
        success = is_success(resp.text)
        return success, chosen

    except requests.exceptions.Timeout:
        return False, chosen
    except requests.exceptions.ConnectionError:
        return False, chosen
    except Exception:
        return False, chosen
