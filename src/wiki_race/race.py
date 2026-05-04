from __future__ import annotations

import re
import time
from datetime import datetime
from typing import Callable

from .constants import MAX_STEPS, MODEL_MAP
from .providers import call_ai
from .wikipedia import article_name, article_url, get_wiki_page, path_to_titles


ProgressCallback = Callable[[dict], None]
CancelCallback = Callable[[], bool]


def build_prompt(current_url: str, page_text: str, links: list[str], history: list[str], target: str) -> str:
    path = " -> ".join(article_name(url) for url in history[-6:])
    visited = set(history)
    fresh_links = [link for link in links if link not in visited][:50]
    seen_links = [link for link in links if link in visited][:10]

    links_section = "Unvisited links:\n" + "\n".join(fresh_links)
    if seen_links:
        links_section += "\n\nPreviously visited links (backtrack here only if truly stuck):\n" + "\n".join(seen_links)

    return (
        f'You are playing Wikipedia Race. Reach "{target}" in as few clicks as possible.\n\n'
        f"Current page: {article_name(current_url)}\n"
        f"Path so far: {path}\n"
        f"Target: {target}\n\n"
        f"Page excerpt:\n{page_text[:1500]}\n\n"
        f"{links_section}\n\n"
        'Rules:\n'
        '- You MUST pick a link from the "Unvisited links" list above. Do not invent URLs.\n'
        f'- If "{target}" appears in any list, pick it immediately.\n'
        '- Navigate through real content articles - avoid meta/hub pages.\n'
        '- You may pick a previously visited link to backtrack only if truly stuck.\n\n'
        "Reply in EXACTLY this format:\n"
        "LINK: <exact URL from the list above>\n"
        f"REASON: <one sentence why this page leads toward {target}>"
    )


def parse_response(response_text: str, links: list[str]) -> str | None:
    match = re.search(r"LINK:\s*(https?://[^\s\n]+)", response_text)
    if match:
        candidate = match.group(1).strip().rstrip(".,)")
        if candidate in links:
            return candidate
        for link in links:
            if candidate in link or link in candidate:
                return link

    for link in links:
        slug = link.split("/wiki/")[-1]
        if len(slug) > 3 and slug.lower() in response_text.lower():
            return link

    return None


def extract_reason(response_text: str) -> str:
    match = re.search(r"REASON:\s*(.+)", response_text, re.DOTALL)
    return match.group(1).strip()[:200] if match else ""


def make_result_record(
    model_id: str,
    start_url: str,
    target: str,
    result: dict,
    *,
    test_id: int | None = None,
    difficulty: str | None = None,
) -> dict:
    record = {
        "model_id": model_id,
        "model_name": MODEL_MAP.get(model_id, {}).get("name", model_id),
        "start": start_url,
        "target": target,
        "steps": result.get("steps", 0),
        "time": result.get("time", 0),
        "score": result.get("score", 0),
        "success": result.get("success", False),
        "timestamp": datetime.now().isoformat(),
        "path": path_to_titles(result.get("path_urls", [])),
        "reasons": result.get("reasons", []),
    }
    if test_id is not None:
        record["test_id"] = test_id
    if difficulty is not None:
        record["difficulty"] = difficulty
    return record


def run_single_race(
    model_id: str,
    start_url: str,
    target: str,
    config: dict[str, str],
    *,
    progress_callback: ProgressCallback | None = None,
    cancel_callback: CancelCallback | None = None,
    step_delay_seconds: float = 1.2,
) -> dict:
    target_url = article_url(target)
    target_slug = target.replace(" ", "_").lower()
    current_url = start_url
    history = [current_url]
    reasons = [""]
    steps = 0
    started_at = time.time()

    def emit(**payload) -> None:
        if progress_callback:
            progress_callback(payload)

    emit(
        status="running",
        current_page=article_name(current_url),
        steps=0,
        path=history[:],
        score=0,
        last_reason="Starting...",
        time=0,
        error="",
    )

    for _ in range(MAX_STEPS):
        if cancel_callback and cancel_callback():
            elapsed = round(time.time() - started_at, 1)
            result = {
                "status": "cancelled",
                "success": False,
                "steps": steps,
                "time": elapsed,
                "score": 0,
                "error": "Cancelled",
                "path_urls": history[:],
                "reasons": reasons[:],
                "current_page": article_name(current_url),
            }
            emit(**result, path=result["path_urls"], last_reason=reasons[-1] if reasons else "")
            return result

        if target_slug in current_url.lower().split("/wiki/")[-1]:
            elapsed = round(time.time() - started_at, 1)
            score = max(0, 1000 - steps * 50 - int(elapsed * 2))
            result = {
                "status": "success",
                "success": True,
                "steps": steps,
                "time": elapsed,
                "score": score,
                "error": "",
                "path_urls": history[:],
                "reasons": reasons[:],
                "current_page": article_name(current_url),
            }
            emit(**result, path=result["path_urls"], last_reason=reasons[-1] if reasons else "")
            return result

        page_text, links = get_wiki_page(current_url)
        if not links:
            elapsed = round(time.time() - started_at, 1)
            result = {
                "status": "failed",
                "success": False,
                "steps": steps,
                "time": elapsed,
                "score": 0,
                "error": "No links found",
                "path_urls": history[:],
                "reasons": reasons[:],
                "current_page": article_name(current_url),
            }
            emit(**result, path=result["path_urls"], last_reason=reasons[-1] if reasons else "")
            return result

        if target_url in links:
            history.append(target_url)
            reasons.append("Direct link to target found on this page.")
            steps += 1
            elapsed = round(time.time() - started_at, 1)
            score = max(0, 1000 - steps * 50 - int(elapsed * 2))
            result = {
                "status": "success",
                "success": True,
                "steps": steps,
                "time": elapsed,
                "score": score,
                "error": "",
                "path_urls": history[:],
                "reasons": reasons[:],
                "current_page": target,
            }
            emit(**result, path=result["path_urls"], last_reason=reasons[-1])
            return result

        prompt = build_prompt(current_url, page_text, links, history, target)
        try:
            response_text = call_ai(model_id, prompt, config)
        except Exception as exc:
            elapsed = round(time.time() - started_at, 1)
            result = {
                "status": "failed",
                "success": False,
                "steps": steps,
                "time": elapsed,
                "score": 0,
                "error": f"AI error: {str(exc)[:120]}",
                "path_urls": history[:],
                "reasons": reasons[:],
                "current_page": article_name(current_url),
            }
            emit(**result, path=result["path_urls"], last_reason=reasons[-1] if reasons else "")
            return result

        chosen_link = parse_response(response_text, links)
        if not chosen_link:
            fresh_links = [link for link in links if link not in history]
            chosen_link = fresh_links[0] if fresh_links else (links[0] if links else None)
        if not chosen_link:
            elapsed = round(time.time() - started_at, 1)
            result = {
                "status": "failed",
                "success": False,
                "steps": steps,
                "time": elapsed,
                "score": 0,
                "error": "No valid link",
                "path_urls": history[:],
                "reasons": reasons[:],
                "current_page": article_name(current_url),
            }
            emit(**result, path=result["path_urls"], last_reason=reasons[-1] if reasons else "")
            return result
        if history.count(chosen_link) >= 2:
            elapsed = round(time.time() - started_at, 1)
            result = {
                "status": "failed",
                "success": False,
                "steps": steps,
                "time": elapsed,
                "score": 0,
                "error": "Loop detected",
                "path_urls": history[:],
                "reasons": reasons[:],
                "current_page": article_name(current_url),
            }
            emit(**result, path=result["path_urls"], last_reason=reasons[-1] if reasons else "")
            return result

        reason = extract_reason(response_text)
        current_url = chosen_link
        history.append(current_url)
        reasons.append(reason)
        steps += 1
        emit(
            status="running",
            current_page=article_name(current_url),
            steps=steps,
            path=history[:],
            score=0,
            last_reason=reason,
            time=round(time.time() - started_at, 1),
            error="",
        )
        time.sleep(step_delay_seconds)

    elapsed = round(time.time() - started_at, 1)
    result = {
        "status": "failed",
        "success": False,
        "steps": steps,
        "time": elapsed,
        "score": 0,
        "error": f"Max {MAX_STEPS} steps reached",
        "path_urls": history[:],
        "reasons": reasons[:],
        "current_page": article_name(current_url),
    }
    emit(**result, path=result["path_urls"], last_reason=reasons[-1] if reasons else "")
    return result
