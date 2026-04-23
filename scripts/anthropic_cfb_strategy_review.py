from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from textwrap import dedent

import requests


DEFAULT_MODEL = "claude-sonnet-4-20250514"
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Send project docs and a strategy question to Anthropic for a college-football product/research review."
    )
    parser.add_argument(
        "--doc",
        action="append",
        required=True,
        help="Path to a project doc to include. Repeat for multiple files.",
    )
    parser.add_argument(
        "--question",
        required=True,
        help="The specific product, research, or storytelling question to answer.",
    )
    parser.add_argument(
        "--focus",
        default="college football fan product strategy, sentiment research design, and storytelling UX",
        help="Optional focus framing for the review.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Anthropic model id. Default: {DEFAULT_MODEL}",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=2200,
        help="Maximum output tokens.",
    )
    parser.add_argument(
        "--doc-char-limit",
        type=int,
        default=18000,
        help="Maximum characters to send per document.",
    )
    parser.add_argument(
        "--output",
        default="output/anthropic-cfb-strategy-review.md",
        help="Where to save the returned review.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    _load_dotenv()
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("Missing ANTHROPIC_API_KEY in the environment. Add it to .env or your shell first.")

    doc_paths = [Path(doc_path) for doc_path in args.doc]
    for doc_path in doc_paths:
        if not doc_path.exists():
            raise SystemExit(f"Document not found: {doc_path}")

    prompt = build_prompt(
        focus=args.focus,
        question=args.question,
        docs=load_docs(doc_paths, args.doc_char_limit),
    )

    payload = {
        "model": args.model,
        "max_tokens": args.max_tokens,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt,
                    }
                ],
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
        print(answer.encode("ascii", "replace").decode("ascii"))


def load_docs(doc_paths: list[Path], doc_char_limit: int) -> str:
    sections: list[str] = []
    for doc_path in doc_paths:
        text = doc_path.read_text(encoding="utf-8")
        excerpt = text.strip()
        if len(excerpt) > doc_char_limit:
            excerpt = excerpt[:doc_char_limit].rstrip() + "\n\n[Truncated]"
        sections.append(f"## {doc_path}\n\n{excerpt}")
    return "\n\n".join(sections)


def build_prompt(focus: str, question: str, docs: str) -> str:
    return dedent(
        f"""
        You are acting as a brutally smart but constructive second-brain collaborator for a college football analytics website.

        Focus:
        {focus}

        Question:
        {question}

        Expectations:
        - Be strategic, opinionated, and concrete.
        - Flag weak premises, fake precision, and questions that sound interesting but will not produce a good product.
        - Prefer ideas that delight a casual but slightly nerdy college football fan.
        - Balance research rigor with product reality, budget constraints, and operational simplicity.
        - Distinguish between what is feasible now versus what should wait for later.
        - Use only the provided project context; if something is uncertain, say so explicitly.

        Please answer in Markdown with these sections:
        1. Bottom line
        2. Strongest questions to ask
        3. Weak or misleading questions to avoid
        4. Best fan-facing outputs
        5. Best chart and data-viz modules
        6. Biggest data or methodology risks
        7. Best v1 scope
        8. Best later-phase extensions
        9. Ruthless top-5 recommendations

        Here are the project docs:

        {docs}
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
