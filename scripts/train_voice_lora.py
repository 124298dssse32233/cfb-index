#!/usr/bin/env python
"""Voice LoRA training on Mistral Nemo 12B via Unsloth.

Usage:
    python scripts/train_voice_lora.py \\
        --corpus data/voice_corpus.jsonl \\
        --base-model unsloth/Mistral-Nemo-Instruct-2407-bnb-4bit \\
        --output-dir loras/cfb-index-voice-v1 \\
        --epochs 2 --rank 32 --lr 5e-5

This script REQUIRES the Alienware GPU. Will not run on this development
machine. Validation runs (--dry-run) check imports + corpus format without
loading the model.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--corpus", type=Path, required=True)
    p.add_argument("--base-model", default="unsloth/Mistral-Nemo-Instruct-2407-bnb-4bit")
    p.add_argument("--output-dir", type=Path, default=Path("loras/cfb-index-voice-v1"))
    p.add_argument("--epochs", type=int, default=2)
    p.add_argument("--rank", type=int, default=32)
    p.add_argument("--alpha", type=int, default=32)
    p.add_argument("--dropout", type=float, default=0.05)
    p.add_argument("--lr", type=float, default=5e-5)
    p.add_argument("--batch-size", type=int, default=1)
    p.add_argument("--grad-accum", type=int, default=4)
    p.add_argument("--max-seq-length", type=int, default=4096)
    p.add_argument("--save-steps", type=int, default=100)
    p.add_argument("--logging-steps", type=int, default=10)
    p.add_argument("--warmup-ratio", type=float, default=0.03)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--dry-run", action="store_true", help="Validate without training")
    return p.parse_args()


def validate_environment(args: argparse.Namespace) -> None:
    """Check imports + corpus + output dir without loading model."""
    log = logging.getLogger("validate")

    # Verify corpus exists and is well-formed
    if not args.corpus.exists():
        log.error("Corpus not found: %s", args.corpus)
        sys.exit(1)

    line_count = 0
    sentinel_count = 0
    bad_lines: list[int] = []
    with args.corpus.open(encoding="utf-8") as fh:
        for idx, raw in enumerate(fh, start=1):
            line_count += 1
            if not raw.strip():
                continue
            try:
                obj = json.loads(raw)
                if "[CFB-INDEX-VOICE]" in obj.get("text", ""):
                    sentinel_count += 1
            except json.JSONDecodeError:
                bad_lines.append(idx)
    log.info("Corpus: %d lines, %d with sentinel", line_count, sentinel_count)
    if bad_lines:
        log.warning("Invalid JSON on %d lines (first 5): %s", len(bad_lines), bad_lines[:5])
    if sentinel_count == 0:
        log.error("No lines contain the [CFB-INDEX-VOICE] sentinel — refusing to train.")
        sys.exit(1)

    # Check unsloth importability only when we're going to actually train.
    if not args.dry_run:
        try:
            import unsloth  # noqa: F401
            import torch

            if not torch.cuda.is_available():
                log.error("CUDA not available — cannot train.")
                sys.exit(1)
            log.info("GPU: %s", torch.cuda.get_device_name(0))
            log.info("VRAM: %.1f GB", torch.cuda.get_device_properties(0).total_memory / 1e9)
        except ImportError as exc:
            log.error("Required imports missing: %s", exc)
            log.error("Install: pip install 'unsloth[cu121] @ git+https://github.com/unslothai/unsloth.git'")
            sys.exit(1)

    args.output_dir.mkdir(parents=True, exist_ok=True)


def train(args: argparse.Namespace) -> None:
    """Train the LoRA. Imports unsloth lazily inside this function."""
    log = logging.getLogger("train")
    from unsloth import FastLanguageModel
    from transformers import TrainingArguments
    from trl import SFTTrainer
    from datasets import load_dataset

    log.info("Loading base model in 4-bit: %s", args.base_model)
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=args.base_model,
        max_seq_length=args.max_seq_length,
        load_in_4bit=True,
    )

    log.info("Attaching LoRA adapters (rank=%d, alpha=%d, dropout=%.2f)",
             args.rank, args.alpha, args.dropout)
    model = FastLanguageModel.get_peft_model(
        model,
        r=args.rank,
        lora_alpha=args.alpha,
        lora_dropout=args.dropout,
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ],
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=args.seed,
    )

    log.info("Loading corpus: %s", args.corpus)
    dataset = load_dataset("json", data_files=str(args.corpus), split="train")
    log.info("Corpus loaded: %d examples", len(dataset))

    def formatting_func(example: dict) -> str:
        # CPT: emit raw text. No instruction templating, no chat formatting.
        return example["text"]

    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset,
        formatting_func=formatting_func,
        max_seq_length=args.max_seq_length,
        args=TrainingArguments(
            output_dir=str(args.output_dir),
            num_train_epochs=args.epochs,
            per_device_train_batch_size=args.batch_size,
            gradient_accumulation_steps=args.grad_accum,
            learning_rate=args.lr,
            optim="adamw_8bit",
            warmup_ratio=args.warmup_ratio,
            lr_scheduler_type="cosine",
            logging_steps=args.logging_steps,
            save_steps=args.save_steps,
            save_total_limit=3,
            bf16=True,
            seed=args.seed,
            report_to="none",
        ),
    )

    log.info("Training start.")
    trainer.train()

    log.info("Saving LoRA adapters to %s", args.output_dir)
    model.save_pretrained(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)

    print(f"\nTraining complete. LoRA saved to {args.output_dir}")
    print("To use with llama.cpp:")
    print(f"  1. Convert to GGUF: python convert_lora.py {args.output_dir}")
    print(f"  2. Apply at runtime: llama-server --lora {args.output_dir}/cfb_voice.gguf ...")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    args = parse_args()
    validate_environment(args)
    if args.dry_run:
        print("Dry-run complete. Environment + corpus look good.")
        return
    train(args)


if __name__ == "__main__":
    main()
