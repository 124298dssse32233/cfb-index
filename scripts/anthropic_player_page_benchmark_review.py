from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
from pathlib import Path
from textwrap import dedent

import requests


DEFAULT_MODEL = "claude-sonnet-4-20250514"
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare a custom CFB player page against benchmark screenshots using Anthropic vision."
    )
    parser.add_argument("--html", required=True, help="Path to the rendered custom player page HTML.")
    parser.add_argument(
        "--image",
        action="append",
        default=[],
        metavar="LABEL=PATH",
        help="Attach an image with a label. Repeat for your page and benchmark screenshots in the order you want reviewed.",
    )
    parser.add_argument(
        "--focus",
        default="Compare these college football player pages like a real fan who cares about readability, stats discoverability, trust, and overall UX quality.",
        help="Specific benchmark framing for the review.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Anthropic model id. Default: {DEFAULT_MODEL}",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=2400,
        help="Maximum output tokens.",
    )
    parser.add_argument(
        "--output",
        default="output/anthropic-player-page-benchmark.md",
        help="Where to save the returned critique.",
    )
    parser.add_argument(
        "--html-char-limit",
        type=int,
        default=42000,
        help="Max HTML characters to send after trimming.",
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

    labeled_images = [parse_labeled_image(value) for value in args.image]
    for label, image_path in labeled_images:
        if not image_path.exists():
            raise SystemExit(f"Image file not found for {label}: {image_path}")

    html_text = html_path.read_text(encoding="utf-8")
    html_excerpt = extract_relevant_html(html_text, args.html_char_limit)

    content_blocks: list[dict[str, object]] = []
    image_manifest_lines: list[str] = []
    for index, (label, image_path) in enumerate(labeled_images, start=1):
        image_manifest_lines.append(f"{index}. {label} -> {image_path}")
        content_blocks.append(build_image_block(image_path))

    prompt = build_prompt(
        focus=args.focus,
        html_path=html_path,
        html_excerpt=html_excerpt,
        image_manifest="\n".join(image_manifest_lines) or "No screenshots were attached.",
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

    print(f"Saved Anthropic benchmark review to {output_path}")
    print()
    try:
        print(answer)
    except UnicodeEncodeError:
        print(answer.encode("ascii", "replace").decode("ascii"))


def parse_labeled_image(raw_value: str) -> tuple[str, Path]:
    if "=" not in raw_value:
        raise SystemExit(f"Image argument must use LABEL=PATH format. Received: {raw_value}")
    label, raw_path = raw_value.split("=", 1)
    label = label.strip()
    image_path = Path(raw_path.strip())
    if not label:
        raise SystemExit(f"Image label cannot be empty: {raw_value}")
    return label, image_path


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
    fallback = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }.get(image_path.suffix.lower())
    if fallback:
        return fallback
    raise SystemExit(f"Unsupported image type for Anthropic vision input: {image_path}")


def extract_relevant_html(html_text: str, html_char_limit: int) -> str:
    start_tokens = [
        "Current Heisman Lens",
        "Current Season Production",
    ]
    end_tokens = [
        "Player Card Blueprint",
        "</main>",
    ]
    start_index = 0
    for token in start_tokens:
        token_index = html_text.find(token)
        if token_index != -1:
            start_index = token_index
            break
    end_index = len(html_text)
    for token in end_tokens:
        token_index = html_text.find(token, start_index + 1)
        if token_index != -1:
            end_index = min(end_index, token_index)
    excerpt = html_text[start_index:end_index].strip()
    if len(excerpt) > html_char_limit:
        excerpt = excerpt[:html_char_limit]
    return excerpt or html_text[:html_char_limit]


def build_prompt(focus: str, html_path: Path, html_excerpt: str, image_manifest: str) -> str:
    return dedent(
        f"""
        You are acting as a ruthless but constructive product critic comparing college football player pages.

        Focus:
        {focus}

        Important context:
        - The goal is to build the best college football player page on the planet for real fans.
        - Judge the pages like an engaged human CFB fan would, not like a generic design reviewer.
        - Care about stats readability, speed of understanding, perceived trust, traditional sports-page expectations, mobile ergonomics, and whether the page feels like a real daily-use product.
        - The attached screenshots are ordered exactly like this:

        {image_manifest}

        - The rendered custom page source came from: {html_path}

        Please answer in Markdown with these sections:
        1. Bottom line
        2. Overall ranking of the pages shown
        3. Where the custom page is clearly better
        4. Where the major sites still win
        5. Readability verdict for a real fan
        6. Highest-leverage UI changes to make next
        7. Highest-leverage interaction changes to make next
        8. Ruthless top-5 recommendations

        Be concrete and specific. Call out:
        - information hierarchy
        - trust signals
        - stats density vs clarity
        - mobile scanability
        - traditional sports-page familiarity
        - table UX
        - how fast a fan can tell what kind of player this is

        Here is the relevant HTML excerpt from the custom page:

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
