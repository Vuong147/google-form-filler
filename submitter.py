import random
import json
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


def precompute_answers(questions: list, n: int) -> None:
    """Pre-compute exact answer distribution across n submissions.
    Modifies questions in-place (adds '_precomputed' key).
    Guarantees ratio-exact distribution instead of pure random.
    """
    for q in questions:
        q_type = q.get("type")
        options = q.get("options", [])
        ratios = q.get("ratios", [])

        if q_type in ("multiple_choice", "dropdown", "linear_scale") and options and ratios:
            raw_counts = [r * n for r in ratios]
            floors = [int(c) for c in raw_counts]
            deficit = n - sum(floors)
            remainders = sorted(
                range(len(raw_counts)),
                key=lambda k: raw_counts[k] - floors[k],
                reverse=True
            )
            for k in remainders[:deficit]:
                floors[k] += 1
            pool = []
            for opt, cnt in zip(options, floors):
                pool.extend([opt] * cnt)
            random.shuffle(pool)
            q["_precomputed"] = pool

        elif q_type == "checkbox" and options and ratios:
            q["_precomputed"] = [
                [opt for opt, prob in zip(options, ratios) if random.random() < prob] or [random.choice(options)]
                for _ in range(n)
            ]


def pick_answer(question: dict, idx: int = 0):
    q_type = question.get("type")
    options = question.get("options", [])
    ratios = question.get("ratios", [])
    answers = question.get("answers", [])
    per_submission = question.get("per_submission", False)
    precomputed = question.get("_precomputed")

    if q_type in ("multiple_choice", "dropdown", "linear_scale"):
        if precomputed:
            return precomputed[idx % len(precomputed)]
        if not options or not ratios:
            return None
        return random.choices(options, weights=ratios, k=1)[0]

    elif q_type == "checkbox":
        if precomputed:
            item = precomputed[idx % len(precomputed)]
            return item if isinstance(item, list) else [item]
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


def _guess_page_count(questions: list) -> int:
    max_idx = 0
    for q in questions:
        try:
            max_idx = max(max_idx, int(q.get("page_index", 0)))
        except Exception:
            continue
    return max(1, max_idx + 1)


def _candidate_page_histories(page_count: int) -> list:
    histories = ["0"]
    for k in range(2, page_count + 3):
        histories.append(",".join(str(i) for i in range(k)))
    return histories


def build_payload(questions: list, idx: int = 0, fbzx: str = None,
                  page_history: str = "0") -> tuple:
    data = {"fvv": "1", "pageHistory": page_history}
    if fbzx:
        data["fbzx"] = fbzx
        data["draftResponse"] = json.dumps([None, None, fbzx], separators=(",", ":"))
    else:
        data["fbzx"] = str(random.randint(-9_000_000_000_000_000_000, 9_000_000_000_000_000_000))
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
                submission_index: int = 0, proxy: str = None,
                fbzx: str = None) -> tuple:
    url = SUBMIT_URL_TEMPLATE.format(form_id=form_id)
    page_count = _guess_page_count(questions)
    histories = _candidate_page_histories(page_count)
    chosen = {}

    proxies = None
    if proxy:
        proxies = {"http": proxy, "https": proxy}

    try:
        first_debug = ""
        for page_history in histories:
            payload, chosen = build_payload(
                questions,
                submission_index,
                fbzx=fbzx,
                page_history=page_history,
            )
            resp = requests.post(
                url, data=payload, headers=HEADERS,
                timeout=timeout, allow_redirects=True,
                proxies=proxies
            )

            if resp.status_code != 200:
                if not first_debug:
                    first_debug = f"HTTP {resp.status_code} (pageHistory={page_history})"
                continue

            success = is_success(resp.text)
            if success:
                return True, chosen, ""

            if not first_debug:
                first_debug = f"pageHistory={page_history}\n" + resp.text[:600]

        return False, chosen, first_debug or "Submit failed for all pageHistory candidates"

    except requests.exceptions.Timeout:
        return False, chosen, "Timeout"
    except requests.exceptions.ConnectionError as e:
        return False, chosen, f"ConnectionError: {e}"
    except Exception as e:
        return False, chosen, str(e)
