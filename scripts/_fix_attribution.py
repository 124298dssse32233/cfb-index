"""
Fix attribution warnings: prepend fanbase-attribution phrasing to chip.text and delusion.text
values that read as the site's verdict rather than the fanbase's belief.
"""
import os
import re

EC_DIR = "profiles/emotional_core"

# Attribution markers — if any present, already attributed
MARKERS = [
    "fan", "Fan", "they ", "They ", "the room", "The room",
    "the base", "The base", "believe", "Believe", "call ", "Call ",
    " say", " Say", "’", "‘", "“", "”",
    "think", "Think", "see ", "See ", "feel", "Feel",
    "crowd", "Crowd", "faithful", "Faithful", "Fans", "fans",
    "supporters", "Supporters", "faithful", "Faithful",
]

def needs_attribution(text):
    if not text or not isinstance(text, str):
        return False
    text = text.strip()
    if not text or text.lower() in ('none', 'null', ''):
        return False
    for m in MARKERS:
        if m in text:
            return False
    return True


def prepend_attribution(text, field):
    """Add minimal fanbase-attribution prefix."""
    text = text.strip()
    # Capitalize first letter of the body
    body = text[0].lower() + text[1:] if len(text) > 1 else text.lower()
    if field == 'chip':
        return f"Fans here believe {body}"
    else:
        return f"The fanbase believes {body}"


def fix_field_in_raw(raw, field_name, slug):
    """
    Use regex to find and replace the text: value under the_chip or the_delusion
    without re-serializing the entire YAML (preserves all formatting, comments, anchors).
    """
    # Pattern: under the_{field} block, find the text: line
    # Handles quoted and unquoted scalars, and block scalars (>-)
    section_key = 'the_chip' if field_name == 'chip' else 'the_delusion'

    # Find the section
    section_pattern = re.compile(
        r'(?m)^(' + re.escape(section_key) + r':\s*\n)((?:[ \t]+.*\n?)*)',
    )

    def fix_section(m):
        header = m.group(1)
        body = m.group(2)

        # Find text: line within the section
        text_pattern = re.compile(
            r'(?m)([ \t]+text:\s*)(.*?)(\n(?=[ \t]|\Z)|$)',
        )

        def fix_text(tm):
            indent = tm.group(1)
            value = tm.group(2).strip()
            suffix = tm.group(3)

            # Strip surrounding quotes if present
            if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
                inner = value[1:-1]
                quoted = True
            elif len(value) >= 2 and value[0] == "'" and value[-1] == "'":
                inner = value[1:-1]
                quoted = True
            else:
                inner = value
                quoted = False

            if not needs_attribution(inner):
                return tm.group(0)

            new_text = prepend_attribution(inner, field_name)
            print(f"  [{slug}] {field_name}.text: {inner[:60]}...")
            print(f"       -> {new_text[:60]}...")

            if quoted:
                return f'{indent}"{new_text}"{suffix}'
            else:
                return f'{indent}"{new_text}"{suffix}'

        new_body = text_pattern.sub(fix_text, body)
        return header + new_body

    return section_pattern.sub(fix_section, raw)


fixed_count = 0
warn_count = 0

for fname in sorted(os.listdir(EC_DIR)):
    if not fname.endswith('.yaml'):
        continue
    slug = fname[:-5]
    fpath = os.path.join(EC_DIR, fname)

    with open(fpath, 'r', encoding='utf-8') as f:
        raw = f.read()

    original = raw
    raw = fix_field_in_raw(raw, 'chip', slug)
    raw = fix_field_in_raw(raw, 'delusion', slug)

    if raw != original:
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(raw)
        fixed_count += 1

print(f"\nDone. Fixed {fixed_count} files.")
