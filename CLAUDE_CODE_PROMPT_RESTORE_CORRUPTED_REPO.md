# Claude Code Prompt — Recover Corrupted Source Tree

The user is a beginner. Do not assume technical context. Explain choices in
plain language and ask before doing anything destructive.

## What's wrong (verified, not theoretical)

Most of `src/cfb_rankings/*.py` is corrupted. A diagnostic on
`C:\Users\kevin\Downloads\Sports Website` found:

- **14 files fail `python -m py_compile`** — outright syntax errors:
  `audit.py`, `cli.py`, `clients/reddit.py`, `conversation_utils.py`,
  `fan_intelligence.py`, `hub_page.py`, `ingest/archetypes.py`,
  `ingest/conversation.py`, `ingest/hub_data.py`, `integrity.py`,
  `migrations.py`, `models/features.py`, `models/power.py`, `reporting.py`,
  `storage.py`.
- **3 files end in literal null bytes** (`\x00\x00...`):
  `storage.py`, `models/features.py`, `models/power.py`. Textbook signature
  of a partial write or crash mid-flush leaving zero-padded tails.
- **~17 more files end mid-statement** with no trailing newline — they were
  truncated.
- **All 42 `.pyc` files under `__pycache__/` are intact** (Python 3.14 magic
  numbers, sizes consistent with the *original* source, not the truncated
  current source). They are the only surviving record of the pre-corruption
  code.

### How this happened (relevant to recovery)

The user's recent edits to this codebase were made by **ChatGPT Codex**, an
LLM-based code editor. The corruption pattern — files ending mid-statement,
some with trailing null bytes, mtimes preserved in some cases — is
consistent with Codex's apply-patch tool partially writing files and either
running out of output tokens, getting interrupted, or rewriting a file with
a truncated version of its earlier output.

Practical consequences:

- The `.pyc` files in `__pycache__/` were written by Python during an
  *earlier successful run*, before Codex's bad rewrites. They reflect the
  last source code that actually compiled. This is the only canonical copy
  of the original.
- Mtimes are unreliable: Codex can rewrite a file with content that's
  byte-shorter than the original, and the previous mtime may persist or
  reset depending on the tool.
- Do not assume "the latest edit is right." For these 14 files, the latest
  edit is the corrupt one. The bytecode is the source of truth.

## Backup situation — do NOT waste time on these

The user has confirmed:

- **No OneDrive / iCloud / Dropbox / Google Drive sync** on this folder.
  Do NOT instruct them to check Version History in File Explorer. It will
  not exist.
- **No `.git` directory** in the folder. Do NOT run any `git` commands and
  do NOT ask about GitHub/GitLab/Bitbucket remotes.
- **No second machine** with a copy of this project.
- **VS Code Local History was already checked and is empty** — `reporting.py`
  exceeds the 256 KB default size cap, so VS Code never tracked it. Don't
  ask the user to look there again.

That leaves exactly one recovery path: **decompile from the `.pyc` files in
`__pycache__/`**. Skip directly to Step 2.

## Hard rules

1. **No improvising code from scratch.** You must not invent function bodies,
   CSS strings, SQL, or any other content "based on what it probably looked
   like." If you cannot recover a function from bytecode, leave it broken
   and say so.
2. **No bulk edits before recovery.** Do not edit `*.py` files until a clean
   source has been restored. Editing the corrupted files will just make the
   damage harder to undo.
3. **Read large files with `offset`/`limit`** — `reporting.py` is 762 KB.
   Never read it whole.
4. **Don't trust file mtimes.** The corruption preserved the original mtimes
   on at least `reporting.py`. Use file *content* checks (py_compile, null
   bytes, size vs .pyc), never mtime, to assess damage.
5. **Be quiet.** Each step should produce one short status line; do not
   narrate. The user is overwhelmed.

## Step 1 — Re-run the diagnostic and confirm scope

Run this in PowerShell (the user is on Windows). Paste the result back to the
user before doing anything else.

```python
# save as diag.py in the workspace root, then: py -3 diag.py
import os, py_compile
from pathlib import Path

src = Path('src/cfb_rankings')
broken_compile, null_byte_files, truncated_no_newline, pyc_larger = [], [], [], []
for py in sorted(src.rglob('*.py')):
    py_size = py.stat().st_size
    pyc_dir = py.parent / '__pycache__'
    pyc_size = max((p.stat().st_size for p in pyc_dir.glob(py.stem + '.cpython-*.pyc')), default=0)
    data = py.read_bytes()
    try:
        py_compile.compile(str(py), doraise=True)
    except py_compile.PyCompileError as e:
        broken_compile.append((str(py), str(e).splitlines()[0][:160]))
    if b'\x00' in data:
        null_byte_files.append((str(py), data.count(b'\x00')))
    if data and data[-1:] not in (b'\n', b'\r'):
        truncated_no_newline.append(str(py))
    if pyc_size > py_size and py_size > 1000:
        pyc_larger.append((str(py), py_size, pyc_size))

print(f'Broken compile: {len(broken_compile)}')
for p, e in broken_compile: print(f'  {p}\n     {e}')
print(f'\nNull bytes:     {len(null_byte_files)}')
for p, n in null_byte_files: print(f'  {p}  ({n} nulls)')
print(f'\nTruncated (no trailing newline): {len(truncated_no_newline)}')
for p in truncated_no_newline: print(f'  {p}')
print(f'\nWhere .pyc > .py size: {len(pyc_larger)}')
for p, s, ps in pyc_larger: print(f'  {p}  py={s/1024:.1f}KB  pyc={ps/1024:.1f}KB')
```

If this confirms the same picture (≥10 broken-compile files, null bytes in
3 files, etc.), proceed.

If the `__pycache__` files are also gone or mismatched (zero or near-zero
`.pyc` sizes, or `.pyc` files matching the *truncated* source size rather
than the original), **STOP**. Tell the user the bytecode is also lost and
that recovery is no longer possible from this folder. Do not attempt
anything else.

## Step 2 — Decompile from `.pyc` bytecode

The user already has Python 3.14 installed locally (the
`__pycache__/*.cpython-314.pyc` files prove it). That means decompilation
is feasible.

Tell the user, in plain language:

> Open PowerShell (Start menu → type "PowerShell" → press Enter). Then paste each line below one at a time and press Enter after each:
>
> ```
> cd "C:\Users\kevin\Downloads\Sports Website"
> py -3.14 -m pip install --user pylingual
> ```
>
> Tell me what you see after each one before continuing.

`pylingual` is the Python decompiler that supports 3.12+. It's the only
mainstream tool that handles 3.14 bytecode. (`uncompyle6` and `decompyle3`
do not.)

If `pylingual` install fails, fall back in this order:

1. `py -3.14 -m pip install --user pycdc-py` (older but sometimes works on 3.14)
2. Direct the user to download the standalone `pycdc.exe` from
   https://github.com/zrax/pycdc/releases and run it from PowerShell.
3. If all decompilers fail on Python 3.14 bytecode, stop and tell the user.
   Do NOT fall back to "writing the file by hand."

Once a decompiler is installed, recover each broken file. For each one in
the broken-compile list from Step 1:

```
py -3.14 -m pylingual src/cfb_rankings/__pycache__/<basename>.cpython-314.pyc -o recovered/<basename>.py
```

(Replace `<basename>` with the actual file stem, e.g. `reporting`.)

Before overwriting the broken file, diff the recovered file against it and
confirm all three:

- The recovered file is larger than the broken one.
- The recovered file ends with a complete `def` or `class` block plus a
  trailing newline.
- `py -3.14 -m py_compile recovered/<basename>.py` passes.

If all three checks pass, copy the recovered file over the broken one.
Decompiler output is not always perfectly identical to the original
(especially for f-strings, complex comprehensions, and chained ternaries);
when in doubt, show the user a short diff of a representative section and
get their OK before overwriting.

After every restore, re-run the Step 1 diagnostic. The "broken compile"
count must decrease monotonically. If it doesn't, stop and tell the user.

## Step 3 — Once the source tree compiles cleanly

Only after **every** file in `src/cfb_rankings/*.py` passes `py_compile`,
return to the original work that was blocked. One follow-up bug was
identified before the corruption was discovered:

- **Bug B (OG SVG truncation):** all 635 team OG share-cards in
  `output/site/teams/*-og.svg` were truncated to 1141–1189 bytes mid-base64
  during the prior build (instead of ~32 KB with a complete `<image>` tag
  and `</svg>` close). Diagnosis steps for this bug were captured in a
  previous brief that has since been deleted; ask the user if they want
  this bug investigated *after* the source tree is restored. Don't try to
  fix it before — the corrupted source can't be rebuilt to test against.

## Deliverable

A final status report in this exact shape. No narrative.

```
Diagnostic at start: {N broken_compile} / {M null_byte} / {K truncated_no_newline}
Recovery path used: {pylingual decompile | pycdc decompile | mixed | failed}
Files restored: {list with paths}
Files unrecoverable: {list with paths, or "none"}
Diagnostic at end:   {N broken_compile} / {M null_byte} / {K truncated_no_newline}
py_compile across src/cfb_rankings: {pass | fail with N remaining}
Bug B (OG truncation) status: {investigated | deferred per user | n/a}
Brief deleted: {yes if all clean}
```

If the report's "at end" numbers are not all zero, leave this brief on disk
and tell the user what's still broken.
