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


def _target_counts(weights: list, n: int) -> list:
    if n <= 0 or not weights:
        return [0] * len(weights)

    total = float(sum(weights))
    if total <= 0:
        return [0] * len(weights)

    normalized = [max(0.0, float(w)) / total for w in weights]
    raw_counts = [w * n for w in normalized]
    floors = [int(c) for c in raw_counts]
    deficit = n - sum(floors)

    indices = list(range(len(raw_counts)))
    random.shuffle(indices)
    remainders = sorted(
        indices,
        key=lambda k: raw_counts[k] - floors[k],
        reverse=True,
    )
    for k in remainders[:deficit]:
        floors[k] += 1
    return floors


def _build_exact_pool(items: list, weights: list, n: int) -> list:
    counts = _target_counts(weights, n)
    pool = []
    for item, cnt in zip(items, counts):
        if cnt > 0:
            pool.extend([item] * cnt)
    random.shuffle(pool)
    return pool


def _precompute_checkbox_near_exact(options: list, probs: list, n: int) -> list:
    if n <= 0 or not options or not probs:
        return []

    clamped = [max(0.0, min(1.0, float(p))) for p in probs]

    # Checkbox: mỗi option là xác suất độc lập theo tổng số submit (không chuẩn hóa theo tổng các option).
    target_counts = []
    for p in clamped:
        raw = p * n
        base = int(raw)
        frac = raw - base
        if frac > 0.5 or (frac == 0.5 and random.random() < 0.5):
            base += 1
        target_counts.append(max(0, min(n, base)))

    picked_sets = [set() for _ in range(n)]

    for opt, cnt in zip(options, target_counts):
        if cnt <= 0:
            continue

        idx_order = list(range(n))
        random.shuffle(idx_order)
        idx_order.sort(key=lambda i: len(picked_sets[i]))

        for i in idx_order[:cnt]:
            picked_sets[i].add(opt)

    output = [list(s) for s in picked_sets]
    random.shuffle(output)
    return output


def precompute_answers(questions: list, n: int) -> None:
    """Pre-compute exact answer distribution across n submissions.
    Modifies questions in-place (adds '_precomputed' key).
    Guarantees ratio-exact distribution instead of pure random.
    """
    for q in questions:
        q["_cursor"] = 0
        q_type = q.get("type")
        options = q.get("options", [])
        ratios = q.get("ratios", [])
        answers = q.get("answers", [])

        if q_type in ("multiple_choice", "dropdown", "linear_scale") and options and ratios:
            q["_precomputed"] = _build_exact_pool(options, ratios, n)

        elif q_type == "checkbox" and options and ratios:
            q["_precomputed"] = _precompute_checkbox_near_exact(options, ratios, n)

        elif q_type in ("short_text", "paragraph") and answers and ratios and not q.get("per_submission", False):
            q["_precomputed"] = _build_exact_pool(answers, ratios, n)

        elif q_type in ("date", "time") and answers:
            if ratios and len(ratios) == len(answers):
                q["_precomputed"] = _build_exact_pool(answers, ratios, n)
            else:
                equal = [1.0] * len(answers)
                q["_precomputed"] = _build_exact_pool(answers, equal, n)


def pick_answer(question: dict, idx: int = 0):
    q_type = question.get("type")
    options = question.get("options", [])
    ratios = question.get("ratios", [])
    answers = question.get("answers", [])
    per_submission = question.get("per_submission", False)
    precomputed = question.get("_precomputed")
    cursor = int(question.get("_cursor", 0))

    if q_type in ("multiple_choice", "dropdown", "linear_scale"):
        if precomputed:
            answer = precomputed[cursor % len(precomputed)]
            question["_cursor"] = cursor + 1
            return answer
        if not options or not ratios:
            return None
        return random.choices(options, weights=ratios, k=1)[0]

    elif q_type == "checkbox":
        if precomputed:
            item = precomputed[cursor % len(precomputed)]
            question["_cursor"] = cursor + 1
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
            answer = answers[cursor % len(answers)]
            question["_cursor"] = cursor + 1
            return answer
        if precomputed:
            answer = precomputed[cursor % len(precomputed)]
            question["_cursor"] = cursor + 1
            return answer
        return random.choices(answers, weights=ratios, k=1)[0]

    elif q_type in ("date", "time"):
        if not answers:
            return ""
        if precomputed:
            answer = precomputed[cursor % len(precomputed)]
            question["_cursor"] = cursor + 1
            return answer
        return random.choice(answers)

    return None


def _guess_page_count(questions: list) -> int:
    max_idx = 0
    for q in questions:
        try:
            max_idx = max(max_idx, int(q.get("page_index", 0)))
        except Exception:
            continue

        routes = q.get("option_routes") or {}
        override_routes = q.get("option_routes_override") or {}
        for route in routes.values():
            if isinstance(route, int):
                max_idx = max(max_idx, route)
        for route in override_routes.values():
            if isinstance(route, int):
                max_idx = max(max_idx, route)
    return max(1, max_idx + 1)


def _candidate_page_histories(page_count: int) -> list:
    histories = ["0"]
    for k in range(2, page_count + 3):
        histories.append(",".join(str(i) for i in range(k)))
    return histories


def _pick_answers_for_submission(questions: list, idx: int = 0) -> tuple:
    picked_by_entry = {}
    chosen = {}
    page_count = _guess_page_count(questions)
    visited = [0]
    current_page = 0

    for _ in range(max(1, page_count + 2)):
        page_questions = [
            q for q in questions
            if not q.get("skip") and int(q.get("page_index", 0)) == current_page
        ]

        jump_target = None
        submit_now = False

        for q in page_questions:
            answer = pick_answer(q, idx)
            if answer is None:
                continue

            entry_id = str(q["entry_id"])
            picked_by_entry[entry_id] = answer

            if isinstance(answer, list):
                chosen[q["text"]] = answer if answer else ["(không chọn)"]
            else:
                chosen[q["text"]] = answer

            routes = q.get("option_routes") or {}
            overrides = q.get("option_routes_override") or {}
            active_routes = dict(routes)
            active_routes.update(overrides)
            if not active_routes or isinstance(answer, list):
                continue

            route = active_routes.get(answer)
            if route == "__submit__":
                submit_now = True
                break
            if isinstance(route, int) and jump_target is None:
                jump_target = route

        if submit_now:
            break

        next_page = jump_target if jump_target is not None else current_page + 1
        if next_page >= page_count:
            break
        if visited and visited[-1] == next_page:
            break

        visited.append(next_page)
        current_page = next_page

    return picked_by_entry, chosen, ",".join(str(i) for i in visited)


def _derive_branch_history(questions: list, picked_by_entry: dict, page_count: int) -> str:
    visited = [0]
    current_page = 0

    for _ in range(max(1, page_count + 2)):
        page_questions = [q for q in questions if int(q.get("page_index", 0)) == current_page]

        jump_target = None
        submit_now = False
        for q in page_questions:
            routes = q.get("option_routes") or {}
            overrides = q.get("option_routes_override") or {}
            active_routes = dict(routes)
            active_routes.update(overrides)
            if not active_routes:
                continue

            answer = picked_by_entry.get(str(q["entry_id"]))
            if answer is None or isinstance(answer, list):
                continue

            route = active_routes.get(answer)
            if route == "__submit__":
                submit_now = True
                break
            if isinstance(route, int):
                jump_target = route
                break

        if submit_now:
            break

        next_page = jump_target if jump_target is not None else current_page + 1
        if next_page >= page_count:
            break
        if visited and visited[-1] == next_page:
            break

        visited.append(next_page)
        current_page = next_page

    return ",".join(str(i) for i in visited)


def build_payload(questions: list, picked_by_entry: dict, fbzx: str = None,
                  page_history: str = "0") -> tuple:
    data = {"fvv": "1", "pageHistory": page_history}
    if fbzx:
        data["fbzx"] = fbzx
        data["draftResponse"] = json.dumps([None, None, fbzx], separators=(",", ":"))
    else:
        data["fbzx"] = str(random.randint(-9_000_000_000_000_000_000, 9_000_000_000_000_000_000))

    for q in questions:
        if q.get("skip"):
            continue

        entry_key = f"entry.{q['entry_id']}"
        answer = picked_by_entry.get(str(q["entry_id"]))

        if answer is None:
            continue

        if isinstance(answer, list):
            if answer:
                data[entry_key] = answer
        else:
            data[entry_key] = answer

    return data


def submit_form(form_id: str, questions: list, timeout: int = 15,
                submission_index: int = 0, proxy: str = None,
                fbzx: str = None) -> tuple:
    url = SUBMIT_URL_TEMPLATE.format(form_id=form_id)
    page_count = _guess_page_count(questions)
    picked_by_entry, chosen, picked_history = _pick_answers_for_submission(questions, submission_index)

    histories = []
    if picked_history:
        histories.append(picked_history)
    histories.extend(_candidate_page_histories(page_count))

    dedup_histories = []
    seen = set()
    for h in histories:
        if h not in seen:
            dedup_histories.append(h)
            seen.add(h)

    proxies = None
    if proxy:
        proxies = {"http": proxy, "https": proxy}

    try:
        first_debug = ""
        for page_history in dedup_histories:
            payload = build_payload(
                questions,
                picked_by_entry,
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
