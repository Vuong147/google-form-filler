import random
import json
import requests
import time
import re
from itertools import combinations

SUBMIT_URL_TEMPLATE = "https://docs.google.com/forms/d/e/{form_id}/formResponse"
VIEW_URL_TEMPLATE = "https://docs.google.com/forms/d/e/{form_id}/viewform"

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
    required = bool(question.get("required", False))
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
            if required and not answer and options:
                return options[0]
            return answer
        if not options or not ratios:
            return options[0] if (required and options) else None
        answer = random.choices(options, weights=ratios, k=1)[0]
        if required and not answer and options:
            return options[0]
        return answer

    elif q_type == "checkbox":
        if precomputed:
            item = precomputed[cursor % len(precomputed)]
            question["_cursor"] = cursor + 1
            result = item if isinstance(item, list) else [item]
            if required and not result and options:
                return [options[0]]
            return result
        if not options or not ratios:
            return [options[0]] if (required and options) else []
        selected = [opt for opt, prob in zip(options, ratios) if random.random() < prob]
        if (required or not selected) and not selected and options:
            selected = [random.choice(options)]
        return selected

    elif q_type in ("short_text", "paragraph"):
        if not answers:
            return "N/A" if required else ""
        if per_submission:
            answer = answers[cursor % len(answers)]
            question["_cursor"] = cursor + 1
            if required and not str(answer).strip():
                for a in answers:
                    if str(a).strip():
                        return a
                return "N/A"
            return answer
        if precomputed:
            answer = precomputed[cursor % len(precomputed)]
            question["_cursor"] = cursor + 1
            if required and not str(answer).strip():
                for a in answers:
                    if str(a).strip():
                        return a
                return "N/A"
            return answer
        answer = random.choices(answers, weights=ratios, k=1)[0]
        if required and not str(answer).strip():
            for a in answers:
                if str(a).strip():
                    return a
            return "N/A"
        return answer

    elif q_type in ("date", "time"):
        if not answers:
            return "" if not required else None
        if precomputed:
            answer = precomputed[cursor % len(precomputed)]
            question["_cursor"] = cursor + 1
            if required and not str(answer).strip():
                for a in answers:
                    if str(a).strip():
                        return a
                return None
            return answer
        answer = random.choice(answers)
        if required and not str(answer).strip():
            for a in answers:
                if str(a).strip():
                    return a
            return None
        return answer

    return None


def _pick_answer_with_forbidden(question: dict, idx: int = 0, forbidden_options=None):
    forbidden = {str(x) for x in (forbidden_options or set()) if x is not None}
    if not forbidden:
        return pick_answer(question, idx)

    q_type = question.get("type")
    if q_type not in ("multiple_choice", "dropdown", "linear_scale"):
        return pick_answer(question, idx)

    options = question.get("options", [])
    if not options:
        return pick_answer(question, idx)

    allowed_idx = [i for i, opt in enumerate(options) if str(opt) not in forbidden]
    if not allowed_idx:
        return pick_answer(question, idx)

    required = bool(question.get("required", False))
    ratios = question.get("ratios", [])
    precomputed = question.get("_precomputed")
    cursor = int(question.get("_cursor", 0))

    if precomputed:
        answer = precomputed[cursor % len(precomputed)]
        question["_cursor"] = cursor + 1
        if str(answer) in forbidden:
            return options[allowed_idx[0]]
        if required and not answer:
            return options[allowed_idx[0]]
        return answer

    filtered_options = [options[i] for i in allowed_idx]
    if ratios and len(ratios) == len(options):
        filtered_weights = [max(0.0, float(ratios[i])) for i in allowed_idx]
        if sum(filtered_weights) > 0:
            answer = random.choices(filtered_options, weights=filtered_weights, k=1)[0]
            if required and not answer:
                return filtered_options[0]
            return answer

    return filtered_options[0]


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
    if page_count <= 1:
        return ["0"]

    histories = ["0"]
    tail_pages = list(range(1, page_count))

    # Cover non-consecutive paths too (e.g. 0,2,4) for branched multi-page forms.
    # Keep a soft cap to avoid too many retries on very large forms.
    max_candidates = 512
    for r in range(1, len(tail_pages) + 1):
        for combo in combinations(tail_pages, r):
            histories.append(",".join(["0", *[str(i) for i in combo]]))
            if len(histories) >= max_candidates:
                return histories
    return histories


def _pick_answers_for_submission(questions: list, idx: int = 0, logic_rules: list = None) -> tuple:
    picked_by_entry = {}
    chosen = {}
    page_count = _guess_page_count(questions)
    visited = [0]
    current_page = 0
    forced_answers = {}
    forbidden_by_target = {}

    rules_by_source = {}
    for r in (logic_rules or []):
        try:
            src = str(r.get("source_entry_id", "")).strip()
            if not src:
                continue
            rules_by_source.setdefault(src, []).append(r)
        except Exception:
            continue

    for _ in range(max(1, page_count + 2)):
        page_questions = [
            q for q in questions
            if not q.get("skip") and int(q.get("page_index", 0)) == current_page
        ]

        jump_target = None
        submit_now = False

        for q in page_questions:
            entry_id = str(q["entry_id"])

            if entry_id in forced_answers:
                if q.get("_precomputed") or q.get("per_submission"):
                    _ = pick_answer(q, idx)
                answer = forced_answers[entry_id]
            else:
                answer = _pick_answer_with_forbidden(
                    q,
                    idx,
                    forbidden_options=forbidden_by_target.get(entry_id, set()),
                )

            if answer is None:
                continue

            picked_by_entry[entry_id] = answer

            if isinstance(answer, list):
                chosen[q["text"]] = answer if answer else ["(không chọn)"]
            else:
                chosen[q["text"]] = answer

            src_rules = rules_by_source.get(entry_id, [])
            if src_rules and not isinstance(answer, list):
                for rule in src_rules:
                    if answer != rule.get("source_answer"):
                        continue
                    target_id = str(rule.get("target_entry_id", "")).strip()
                    forbidden_answer = rule.get("forbidden_answer")
                    if target_id and forbidden_answer is not None:
                        forbidden_by_target.setdefault(target_id, set()).add(forbidden_answer)
                    target_answer = rule.get("target_answer")
                    if target_id and target_answer is not None and target_id not in picked_by_entry:
                        forced_answers[target_id] = target_answer

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
                  page_history: str = "0", include_page_history: bool = True,
                  include_draft_response: bool = True) -> tuple:
    data = {"fvv": "1"}
    if include_page_history:
        data["pageHistory"] = page_history
    if fbzx:
        data["fbzx"] = fbzx
        if include_draft_response:
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
                fbzx: str = None, logic_rules: list = None) -> tuple:
    url = SUBMIT_URL_TEMPLATE.format(form_id=form_id)
    view_url = VIEW_URL_TEMPLATE.format(form_id=form_id)
    page_count = _guess_page_count(questions)
    picked_by_entry, chosen, picked_history = _pick_answers_for_submission(
        questions,
        submission_index,
        logic_rules=logic_rules,
    )

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
        tried_debugs = []
        session = requests.Session()
        session.headers.update(dict(HEADERS))
        session.headers["Origin"] = "https://docs.google.com"
        session.headers["Referer"] = view_url

        fresh_fbzx = None
        try:
            vr = session.get(view_url, timeout=timeout, allow_redirects=True, proxies=proxies)
            if vr.status_code == 200 and vr.text:
                m = re.search(r'name="fbzx"\s+value="([^"]+)"', vr.text)
                if not m:
                    m = re.search(r'"fbzx"\s*,\s*"([^"]+)"', vr.text)
                if m:
                    fresh_fbzx = m.group(1)
        except Exception:
            pass

        token_candidates = []
        if fresh_fbzx:
            token_candidates.append((fresh_fbzx, "fresh_fbzx"))
        if fbzx and fbzx != fresh_fbzx:
            token_candidates.append((fbzx, "parsed_fbzx"))
        token_candidates.append((None, "no_fbzx"))

        def _try_payload(token, page_history="0", include_page_history=True, include_draft_response=True, tag=""):
            payload = build_payload(
                questions,
                picked_by_entry,
                fbzx=token,
                page_history=page_history,
                include_page_history=include_page_history,
                include_draft_response=include_draft_response,
            )
            resp = session.post(
                url, data=payload,
                timeout=timeout, allow_redirects=True,
                proxies=proxies
            )
            if resp.status_code == 200 and is_success(resp.text):
                return True, ""
            if resp.status_code != 200:
                body = (resp.text or "")[:400]
                if body:
                    return False, f"HTTP {resp.status_code} ({tag})\n{body}"
                return False, f"HTTP {resp.status_code} ({tag})"
            return False, f"{tag}\n" + resp.text[:600]

        for token, token_tag in token_candidates:
            # Mode 1: safest payload (no pageHistory, no draftResponse)
            ok, dbg = _try_payload(
                token,
                include_page_history=False,
                include_draft_response=False,
                tag=f"{token_tag},no_pageHistory,no_draft",
            )
            if ok:
                return True, chosen, ""
            tried_debugs.append(dbg)
            if not first_debug:
                first_debug = dbg

            # Mode 2: pageHistory without draftResponse
            for page_history in dedup_histories:
                ok, dbg = _try_payload(
                    token,
                    page_history=page_history,
                    include_page_history=True,
                    include_draft_response=False,
                    tag=f"{token_tag},pageHistory={page_history},no_draft",
                )
                if ok:
                    return True, chosen, ""
                tried_debugs.append(dbg)
                if not first_debug:
                    first_debug = dbg

            # Mode 3: strict mode with draftResponse
            for page_history in dedup_histories:
                ok, dbg = _try_payload(
                    token,
                    page_history=page_history,
                    include_page_history=True,
                    include_draft_response=True,
                    tag=f"{token_tag},pageHistory={page_history}",
                )
                if ok:
                    return True, chosen, ""
                tried_debugs.append(dbg)
                if not first_debug:
                    first_debug = dbg

        debug_summary = "\n---\n".join(tried_debugs[:12])
        if first_debug and debug_summary:
            return False, chosen, first_debug + "\n\n[All tried modes]\n" + debug_summary
        return False, chosen, first_debug or debug_summary or "Submit failed for all retry strategies"

    except requests.exceptions.Timeout:
        return False, chosen, "Timeout"
    except requests.exceptions.ConnectionError as e:
        return False, chosen, f"ConnectionError: {e}"
    except Exception as e:
        return False, chosen, str(e)
