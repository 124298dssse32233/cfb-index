from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
from pathlib import Path
from textwrap import dedent

import requests


# claude-sonnet-4-20250514 retires from API 2026-06-15 — migrated to 4-6.
DEFAULT_MODEL = "claude-sonnet-4-6"
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Send a player-page stats section to Anthropic for a front-end / UX critique."
    )
    parser.add_argument("--html", required=True, help="Path to the rendered HTML page to review.")
    parser.add_argument(
        "--image",
        action="append",
        default=[],
        help="Optional screenshot path(s). Repeat the flag to include multiple images.",
    )
    parser.add_argument(
        "--focus",
        default="Current Season Production section on a college football player page",
        help="Specific page area or UX problem to focus the critique on.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Anthropic model id. Default: {DEFAULT_MODEL}",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=1800,
        help="Maximum output tokens.",
    )
    parser.add_argument(
        "--output",
        default="output/anthropic-stats-page-review.md",
        help="Where to save the returned critique.",
    )
    parser.add_argument(
        "--html-char-limit",
        type=int,
        default=50000,
        help="Max HTML characters to send after extraction and trimming.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    _load_dotenv()
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("Missing ANTHROPIC_API_KEY in the environment. Add it to .env or your shell first.")

    html_path = Path(args.html)
    if not html_path.exists():
        raise SystemExit(f"HTML file not found: {html_path}")

    image_paths = [Path(image_path) for image_path in args.image]
    for image_path in image_paths:
        if not image_path.exists():
            raise SystemExit(f"Image file not found: {image_path}")

    html_text = html_path.read_text(encoding="utf-8")
    html_excerpt = extract_relevant_html(html_text, args.focus, args.html_char_limit)

    content_blocks: list[dict[str, object]] = []
    for image_path in image_paths:
        content_blocks.append(build_image_block(image_path))

    prompt = build_prompt(
        focus=args.focus,
        html_path=html_path,
        html_excerpt=html_excerpt,
        image_count=len(image_paths),
    )
    content_blocks.append({"type": "text", "text": prompt})

    payload = {
        "model": args.model,
        "max_tokens": args.max_tokens,
        "messages": [
            {
                "role": "user",
                "content": content_blocks,
            }
        ],
    }

    response = requests.post(
        ANTHROPIC_API_URL,
        headers={
            "x-api-key": api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        },
        data=json.dumps(payload),
        timeout=180,
    )
    response.raise_for_status()
    data = response.json()
    answer = extract_text_response(data)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(answer, encoding="utf-8")

    print(f"Saved Anthropic review to {output_path}")
    print()
    try:
        print(answer)
    except UnicodeEncodeError:
        print(answer.encode('ascii', 'replace').decode('ascii'))


def build_image_block(image_path: Path) -> dict[str, object]:
    media_type = detect_media_type(image_path)
    image_bytes = image_path.read_bytes()
    image_base64 = base64.b64encode(image_bytes).decode("ascii")
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": media_type,
            "data": image_base64,
        },
    }


def detect_media_type(image_path: Path) -> str:
    media_type, _ = mimetypes.guess_type(image_path.name)
    if media_type in {"image/png", "image/jpeg", "image/webp", "image/gif"}:
        return media_type
    suffix = image_path.suffix.lower()
    fallback = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }.get(suffix)
    if fallback:
        return fallback
    raise SystemExit(f"Unsupported image type for Anthropic vision input: {image_path}")


def extract_relevant_html(html_text: str, focus: str, html_char_limit: int) -> str:
    start_token = "Current Season Production"
    end_tokens = [
        "Identity &amp; Role",
        "Identity & Role",
        "Recruiting Pedigree",
    ]

    start_index = html_text.find(start_token)
    if start_index == -1:
        excerpt = html_text[:html_char_limit]
    else:
        end_index = len(html_text)
        for token in end_tokens:
            token_index = html_text.find(token, start_index + len(start_token))
            if token_index != -1:
                end_index = min(end_index, token_index)
        excerpt = html_text[start_index:end_index]

    excerpt = excerpt.strip()
    if len(excerpt) > html_char_limit:
        excerpt = excerpt[:html_char_limit]

    return excerpt or html_text[:html_char_limit]


def build_prompt(focus: str, html_path: Path, html_excerpt: str, image_count: int) -> str:
    return dedent(
        f"""
        You are acting as a senior front-end and product design critic reviewing a college football player stats page.

        Focus area:
        {focus}

        Context:
        - This is a custom stats experience for a college football player card.
        - The goal is to become best-in-class among popular CFB stats products.
        - The user cares about clarity, scanability, sortable stats, position-aware design, and premium information density.
        - Review both the information architecture and the actual front-end UX.
        - {image_count} screenshot(s) are attached before this text block.
        - The rendered page source came from: {html_path}

        Please respond in Markdown with these sections:
        1. Overall verdict
        2. What works already
        3. Biggest UX weaknesses
        4. How elite sports stats pages usually solve this
        5. Specific UI changes to make next
        6. Specific interaction changes to make next
        7. Revised layout recommendation
        8. A ruthless prioritized top-5 list

        Be concrete. Prefer actionable interface advice over generic commentary.
        Call out hierarchy, spacing, table design, sortability, mobile ergonomics, stat grouping, comparability, and whether the page feels like a real stats tool versus a marketing block.

        Here is the relevant HTML excerpt:

        ```html
        {html_excerpt}
        ```
        """
    ).strip()


def extract_text_response(payload: dict[str, object]) -> str:
    content = payload.get("content")
    if not isinstance(content, list):
        return json.dumps(payload, indent=2)
    texts: list[str] = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            text = block.get("text")
            if isinstance(text, str):
                texts.append(text)
    return "\n\n".join(texts).strip() or json.dumps(payload, indent=2)


def _load_dotenv() -> None:
    env_path = Path.cwd() / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


if __name__ == "__main__":
    main()
