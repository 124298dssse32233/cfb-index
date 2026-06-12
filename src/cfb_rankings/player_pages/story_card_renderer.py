"""Player Story Card ("Dossier Noir") — pure renderer.

Turns a fully-built StoryCard payload (see the contract dataclasses in
``story_card.py``) into the Noir Dossier HTML described in
``docs/design-system/41-player-story-card.md``. This module does NOT query the
DB and NEVER raises into the page — every path degrades to "".

Mental model (doc 41 §1, anatomy §4):
  - identity anchor (team-color touch on ring + name underline only)
  - mixed-case Source Serif logline
  - ONE big number (BAN) in Bebas Neue welded to its label + a receipt
  - key-stat chips, visible while collapsed (the stats fan wins here)
  - a fanbase dominant-take line with a confidence meter (compile, don't adjudicate)
  - a native <details>/<summary> expand using grid-template-rows:0fr->1fr
  - a low-data "stats-strip" fallback variant (doc 41 §5) — motionless, no drama

Discipline (doc 41 §8.5): 1-2 animated elements per view; the BAN is the single
numeric hero, everything else is static (static-vs-animated does semantic work).
prefers-reduced-motion kills all motion; the stats-strip is motionless always.

CSS is exposed as the RAW constant STORY_CARD_CSS — NO <style> tags. The player
page concatenates module CSS into ONE outer <style> block, and a nested <style>
tag would close that block early (the ERA_CHAPTER bug, doc 46 §4). Do NOT wrap it.

Public API:
    render_story_card(card) -> str   # full card HTML, or "" when None/omit rung
    render_stats_strip(card) -> str  # the low-data factual bio strip (doc 41 §5)
    STORY_CARD_CSS                   -> str   # module-scoped RAW css (.psc-*)
"""

from __future__ import annotations

import json
import re
from html import escape
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:  # pragma: no cover - type hints only, no runtime dependency
    from .story_card import Ban, DominantTake, Receipt, StoryCard, SuccessionRead


# ---------------------------------------------------------------------------
# Tier -> rail data-attribute (CSS owns the actual colors; tier-is-texture §1/§4)
# ---------------------------------------------------------------------------
_VALID_TIERS = ("s", "t1", "t2", "t3")


def _tier_rail(card: Any) -> str:
    raw = str(_attr(card, "tier_rail", "t3") or "t3").strip().lower()
    return raw if raw in _VALID_TIERS else "t3"


def _attr(obj: Any, name: str, default: Any = None) -> Any:
    """Duck-typed attribute read so the renderer never hard-depends on the
    dataclass module at import time and tolerates partial/None payloads."""
    if obj is None:
        return default
    val = getattr(obj, name, default)
    return default if val is None else val


def _safe_str(value: Any) -> str:
    """escape() any dynamic text; coerce None/non-str defensively."""
    if value is None:
        return ""
    return escape(str(value))


def _clamp01(value: Any) -> float:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return 0.0
    if f < 0.0:
        return 0.0
    if f > 1.0:
        return 1.0
    return f


def _confidence_band(confidence: float) -> str:
    """3-band semantics per doc 33 confidence-signaling."""
    if confidence >= 0.66:
        return "high"
    if confidence >= 0.33:
        return "medium"
    return "low"


def _team_color_style(card: Any) -> str:
    """Inline --psc-team injection (doc 41 §2/§9). Accepts an optional
    team_color on the card; only a strict #hex passes (identity touch only,
    never data ink). Silently dropped when absent or unsafe."""
    raw = _attr(card, "team_color", None)
    if not raw:
        return ""
    candidate = str(raw).strip()
    if re.fullmatch(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})", candidate):
        return f' style="--psc-team:{candidate}"'
    return ""


# ---------------------------------------------------------------------------
# Sub-renderers (each returns "" when its slice is absent)
# ---------------------------------------------------------------------------
def _render_receipt(receipt: Any, *, inline: bool = False) -> str:
    """A hoverable/tappable source marker pointing at the DB origin (doc 41 §1.3)."""
    if receipt is None:
        return ""
    detail = _safe_str(_attr(receipt, "detail", ""))
    if not detail:
        return ""
    table = _safe_str(_attr(receipt, "table", ""))
    url = _attr(receipt, "url", None)
    cls = "psc-receipt psc-receipt--inline" if inline else "psc-receipt"
    title = f"{table} · {detail}" if table else detail
    body = f'<span class="psc-receipt__mark" aria-hidden="true">src</span>{detail}'
    if url:
        href = _safe_str(url)
        return (
            f'<a class="{cls}" href="{href}" target="_blank" rel="noopener noreferrer" '
            f'title="{_safe_str(title)}">{body}</a>'
        )
    return f'<span class="{cls}" title="{_safe_str(title)}">{body}</span>'


def _render_identity(card: Any) -> str:
    """Identity anchor — team-color ring + name underline (doc 41 §4)."""
    name = _safe_str(_attr(card, "player_name", "") or _attr(card, "player_external_id", ""))
    meta = _safe_str(_attr(card, "identity_meta", ""))  # "QB · UCLA · Jr · #9"
    if not name:
        # External-id-only fallback keeps the anchor honest rather than blank.
        name = _safe_str(_attr(card, "player_external_id", "Player"))
    meta_html = f'<p class="psc-identity__meta">{meta}</p>' if meta else ""
    return (
        '<div class="psc-identity">'
        '<span class="psc-identity__crest" aria-hidden="true"></span>'
        '<div class="psc-identity__text">'
        f'<p class="psc-identity__name">{name}</p>'
        f'{meta_html}'
        '</div>'
        '</div>'
    )


def _render_chapter(card: Any) -> str:
    """Chapter chip + freshness (doc 41 §4/§7)."""
    label = _safe_str(_attr(card, "chapter_label", ""))
    number = _attr(card, "chapter_number", None)
    as_of = _safe_str(_attr(card, "as_of_date", ""))
    if not label and number is None and not as_of:
        return ""
    chip = ""
    if label or number is not None:
        try:
            num_txt = f"CH.{int(number)} · " if number is not None else ""
        except (TypeError, ValueError):
            num_txt = ""
        chip = f'<span class="psc-chapter__chip">{num_txt}{label}</span>'
    fresh = f'<span class="psc-chapter__fresh">as of {as_of}</span>' if as_of else ""
    return f'<div class="psc-chapter">{chip}{fresh}</div>'


def _render_chips(card: Any) -> str:
    """Key-stat chips — visible while collapsed; STATIC (reads as fact, §8.5)."""
    chips = _attr(card, "key_stat_chips", []) or []
    cells = ""
    for chip in chips:
        if not isinstance(chip, dict):
            continue
        value = _safe_str(chip.get("value", ""))
        label = _safe_str(chip.get("label", ""))
        if not value and not label:
            continue
        cells += (
            '<span class="psc-chip">'
            f'<span class="psc-chip__value">{value}</span>'
            f'<span class="psc-chip__label">{label}</span>'
            '</span>'
        )
    if not cells:
        return ""
    return f'<div class="psc-chips">{cells}</div>'


def _render_ban(card: Any) -> str:
    """The single big honest number — number welded to its label + receipt (§6).
    The ONE animated numeric hero in the view (§8.5)."""
    ban = _attr(card, "ban", None)
    if ban is None:
        return ""
    number = _safe_str(_attr(ban, "number", ""))
    label = _safe_str(_attr(ban, "label", ""))
    if not number or not label:
        # Never a bare number; never a label with no number. Drop the block.
        return ""
    kind = str(_attr(ban, "kind", "rank") or "rank").strip().lower()
    kind = kind if kind in ("rank", "magnitude") else "rank"
    receipt_html = _render_receipt(_attr(ban, "receipt", None))
    receipt_block = (
        f'<p class="psc-ban__receipt">{receipt_html}</p>' if receipt_html else ""
    )
    return (
        f'<div class="psc-ban" data-ban-kind="{kind}">'
        f'<p class="psc-ban__label">{label}</p>'
        f'<p class="psc-ban__number">{number}</p>'
        f'{receipt_block}'
        '</div>'
    )


def _render_dominant_take(card: Any) -> str:
    """Fanbase dominant-take line + confidence meter (doc 42 §1, doc 49 C1).
    COMPILE, do not adjudicate — attribute to the fanbase; dissent is a labeled
    minority, never suppressed."""
    take = _attr(card, "dominant_take", None)
    if take is None:
        return ""
    text = _safe_str(_attr(take, "text", ""))
    if not text:
        return ""
    confidence = _clamp01(_attr(take, "confidence", 0.0))
    band = _confidence_band(confidence)
    pct = int(round(confidence * 100))
    try:
        source_count = int(_attr(take, "source_count", 0) or 0)
    except (TypeError, ValueError):
        source_count = 0
    src_label = "source" if source_count == 1 else "sources"
    src_html = (
        f'<span class="psc-take__sources">{source_count} {src_label}</span>'
        if source_count > 0 else ""
    )
    minority = _attr(take, "minority_take", None)
    minority_html = ""
    if minority:
        minority_html = (
            '<p class="psc-take__minority">'
            '<span class="psc-take__minority-tag">Minority view</span>'
            f'{_safe_str(minority)}'
            '</p>'
        )
    return (
        '<div class="psc-take">'
        f'<p class="psc-take__text">{text}</p>'
        '<div class="psc-take__meter-row">'
        '<span class="psc-take__meter" role="img" '
        f'aria-label="Fanbase agreement: {band} confidence, {pct} percent">'
        f'<span class="psc-take__meter-fill" data-band="{band}" '
        f'style="width:{pct}%"></span>'
        '</span>'
        f'<span class="psc-take__meter-label" data-band="{band}">{band} confidence</span>'
        f'{src_html}'
        '</div>'
        f'{minority_html}'
        '</div>'
    )


def _render_tension(card: Any) -> str:
    """Tension line (serif italic) — perception vs production (doc 41 §4)."""
    tension = _safe_str(_attr(card, "tension_text", ""))
    if not tension:
        return ""
    return f'<p class="psc-tension">{tension}</p>'


def _render_succession(card: Any) -> str:
    """Filling-the-Shoes + the Clock inside the expanded panel (doc 44)."""
    succ = _attr(card, "succession", None)
    if succ is None:
        return ""
    role = _safe_str(_attr(succ, "role", ""))
    pred = _safe_str(_attr(succ, "predecessor_name", ""))
    heir = _safe_str(_attr(succ, "heir_name", ""))
    shoes = _safe_str(_attr(succ, "shoes_read", ""))
    tone = _safe_str(_attr(succ, "tone", ""))
    clock = _safe_str(_attr(succ, "clock_line", ""))
    if not (pred or heir or clock):
        return ""

    def _stars(value: Any) -> str:
        try:
            n = int(value)
        except (TypeError, ValueError):
            return ""
        if n <= 0:
            return ""
        return f' <span class="psc-succ__stars">{n}★</span>'

    lines = ""
    if pred:
        lines += (
            '<li class="psc-succ__line">'
            '<span class="psc-succ__role">Inherited from</span>'
            f'<span class="psc-succ__name">{pred}{_stars(_attr(succ, "predecessor_stars", None))}</span>'
            '</li>'
        )
    if heir:
        lines += (
            '<li class="psc-succ__line">'
            '<span class="psc-succ__role">Pushed by</span>'
            f'<span class="psc-succ__name">{heir}{_stars(_attr(succ, "heir_stars", None))}</span>'
            '</li>'
        )
    if clock:
        lines += (
            '<li class="psc-succ__line psc-succ__line--clock">'
            f'<span class="psc-succ__clock">{clock}</span>'
            '</li>'
        )
    read_chip = ""
    if shoes:
        tone_attr = f' data-tone="{tone}"' if tone else ""
        read_chip = (
            f'<span class="psc-succ__read"{tone_attr}>{shoes.replace("_", " ")}</span>'
        )
    role_label = f"{role} succession" if role else "Succession"
    return (
        '<div class="psc-succ">'
        '<div class="psc-succ__head">'
        f'<span class="psc-succ__eyebrow">{_safe_str(role_label)}</span>'
        f'{read_chip}'
        '</div>'
        f'<ul class="psc-succ__list">{lines}</ul>'
        '</div>'
    )


# ---------------------------------------------------------------------------
# Tribal-Lens POV toggle (doc 49 §2). Static-site safe: NO extra pages, NO
# server — the lens texts ship as a small INLINE JSON payload + a tiny vanilla
# JS toggle (_LENS_TOGGLE_SCRIPT below; emitted inline next to the payload by
# _render_lens_toggle so the card is self-contained — build_card returns it and
# reporting.py needs no injection). When only ONE lens qualifies, render the card
# plainly with NO toggle AND NO script — never a 3x-empty tab bar, never dead JS.
# The National lens IS the existing top-level prose (today's behavior).
# ---------------------------------------------------------------------------
# Human-facing label per lens key (doc 49 C1: the take is ATTRIBUTED — "what
# rivals say" — never the site's own opinion; the confidence meter stays on
# National, which is the deterministic meta-claim).
_LENS_LABELS = {
    "national": "National",
    "rival": "What rivals say",
    "home": "Home crowd",
}
# Render order; any lens not in this list is appended after (defensive).
_LENS_ORDER = ("national", "rival", "home")
# Only these per-lens prose fields are carried in the payload / swapped by JS.
_LENS_FIELDS = ("logline", "dominant_take", "minority_take", "body", "kicker")


def _lens_has_content(lens: Any) -> bool:
    """A lens qualifies for the toggle only if it carries at least a logline
    or a take/body to swap to — an empty dict must never produce a dead tab."""
    if not isinstance(lens, dict):
        return False
    for key in ("logline", "dominant_take", "body"):
        val = lens.get(key)
        if val is not None and str(val).strip():
            return True
    return False


def _qualifying_lenses(card: Any) -> "list[tuple[str, dict]]":
    """Return ordered (key, lens_dict) pairs that have content. National is
    listed first; any unknown keys are appended last. Floor + eval gating is
    decided upstream (compute_story_cards only attaches a lens that cleared the
    representativeness floor + eval) — here we only drop empties defensively."""
    lenses = _attr(card, "lenses", None)
    if not isinstance(lenses, dict) or not lenses:
        return []
    pairs: list[tuple[str, dict]] = []
    seen: set[str] = set()
    for key in _LENS_ORDER:
        lens = lenses.get(key)
        if _lens_has_content(lens):
            pairs.append((key, lens))
            seen.add(key)
    for key, lens in lenses.items():
        if key not in seen and _lens_has_content(lens):
            pairs.append((str(key), lens))
    return pairs


def _lens_payload_dict(pairs: "list[tuple[str, dict]]") -> dict:
    """Build the per-lens prose map the JS swaps into the card. Only known prose
    fields are carried (coerced to str); nothing here is trusted as HTML — the
    client writes it to textContent only, mirroring the escape discipline."""
    out: dict[str, dict] = {}
    for key, lens in pairs:
        slot: dict[str, str] = {}
        for field_name in _LENS_FIELDS:
            val = lens.get(field_name)
            if val is not None and str(val).strip():
                slot[field_name] = str(val)
        out[key] = slot
    return out


def _render_lens_toggle(card: Any) -> "tuple[str, str]":
    """Return ``(toggle_bar_html, payload_script_html)``.

    Emits BOTH only when >= 2 lenses qualify; otherwise returns ("", "") and the
    card renders plainly (the dominant case — rival discourse is genuinely scarce
    DB-wide, so National-only-with-NO-toggle is the default path, not the edge).
    The payload is a ``<script type="application/json">`` block keyed to the
    card's uid so the (separate) toggle script scopes to one card.
    """
    pairs = _qualifying_lenses(card)
    if len(pairs) < 2:
        return "", ""

    uid = _safe_str(_attr(card, "player_external_id", "") or "")

    tabs = ""
    for idx, (key, _lens) in enumerate(pairs):
        label = _LENS_LABELS.get(key, key.replace("_", " ").title())
        selected = "true" if idx == 0 else "false"
        tabs += (
            f'<button type="button" class="psc-lens__tab" '
            f'data-lens-tab="{escape(key)}" aria-selected="{selected}">'
            f'{escape(label)}</button>'
        )
    toggle_bar = (
        f'<div class="psc-lens" role="tablist" aria-label="Whose take are you reading">'
        f'{tabs}'
        '</div>'
    )

    # json.dumps escapes the data; the renderer never trusts it as markup (the
    # JS writes to textContent only). Defuse "</script>" just in case a lens
    # text contains it, so the inline JSON block can't be closed early.
    payload_json = json.dumps(_lens_payload_dict(pairs), ensure_ascii=False)
    payload_json = payload_json.replace("</", "<\\/")
    uid_attr = f' data-psc-lens-payload="{uid}"' if uid else ' data-psc-lens-payload=""'
    payload_script = (
        f'<script type="application/json"{uid_attr}>{payload_json}</script>'
        # The vanilla-JS toggle that wires the tabs ships inline next to the
        # payload (self-contained card — build_card returns it, no reporting.py
        # injection needed). Only emitted here, where >= 2 lenses qualify, so a
        # single-lens card carries NO toggle and NO script.
        + _LENS_TOGGLE_SCRIPT
    )
    return toggle_bar, payload_script


# The Tribal-Lens toggle behavior (doc 49 §2). Vanilla JS, no framework. One IIFE
# scoped per card via the card's data-psc-card-uid, so multiple cards on a page
# never collide. Fully defensive: every lookup no-ops when its element/payload is
# absent, so a malformed card can never throw. It reads the inline JSON payload
# (written to textContent only — never injected as HTML), swaps the lens-scoped
# prose fields on tab click, and moves the active/aria-selected state. A field the
# selected lens does not carry FALLS BACK to the National (default/first) lens so a
# partial lens never blanks a slot. NOTE: keep this a raw string with NO surrounding
# <style>; it is a <script> block concatenated straight into the card HTML.
_LENS_TOGGLE_SCRIPT = """
<script>
(function(){
  var cards = document.querySelectorAll('.psc-card--narrative[data-psc-card-uid]');
  if(!cards || !cards.length) return;
  for(var c=0;c<cards.length;c++){ wire(cards[c]); }
  function wire(card){
    try{
      if(!card || card.getAttribute('data-psc-lens-wired')==='1') return;
      var uid = card.getAttribute('data-psc-card-uid') || '';
      var tabs = card.querySelectorAll('[data-lens-tab]');
      if(!tabs || tabs.length < 2) return;
      var payloadEl = card.querySelector('script[type="application/json"][data-psc-lens-payload]');
      if(!payloadEl) return;
      var data;
      try{ data = JSON.parse(payloadEl.textContent || '{}'); }catch(e){ return; }
      if(!data || typeof data !== 'object') return;
      // The first tab is National (the default already in the DOM); capture it as
      // the fallback so a partial lens never blanks a field.
      var baseKey = tabs[0].getAttribute('data-lens-tab') || '';
      function fieldFor(key, name){
        var lens = data[key];
        if(lens && typeof lens === 'object' && lens[name] != null && String(lens[name]).length) return String(lens[name]);
        var base = data[baseKey];
        if(base && typeof base === 'object' && base[name] != null && String(base[name]).length) return String(base[name]);
        return null;
      }
      function setText(sel, value){
        if(value == null) return;
        var el = card.querySelector(sel);
        if(el) el.textContent = value;
      }
      function setMinority(value){
        // The minority line keeps its 'Minority view' tag span; swap only the
        // trailing text node so the tag is preserved.
        var el = card.querySelector('.psc-take__minority');
        if(!el) return;
        if(value == null){ return; }
        var tag = el.querySelector('.psc-take__minority-tag');
        // Remove every node after the tag, then append the new text.
        while(el.lastChild && el.lastChild !== tag){ el.removeChild(el.lastChild); }
        el.appendChild(document.createTextNode(value));
      }
      function setBody(value){
        if(value == null) return;
        var paras = card.querySelectorAll('.psc-recap__para');
        if(!paras || !paras.length) return;
        // Collapse to the first paragraph (lens body is a single block); hide the
        // rest so a shorter lens body never leaves stale National paragraphs.
        paras[0].textContent = value;
        for(var i=1;i<paras.length;i++){ paras[i].style.display = 'none'; }
      }
      function applyLens(key){
        setText('.psc-logline', fieldFor(key, 'logline'));
        setText('.psc-take__text', fieldFor(key, 'dominant_take'));
        setMinority(fieldFor(key, 'minority_take'));
        setBody(fieldFor(key, 'body'));
        setText('.psc-recap__kicker', fieldFor(key, 'kicker'));
      }
      for(var t=0;t<tabs.length;t++){
        (function(tab){
          tab.addEventListener('click', function(){
            var key = tab.getAttribute('data-lens-tab') || '';
            for(var k=0;k<tabs.length;k++){
              tabs[k].setAttribute('aria-selected', tabs[k]===tab ? 'true' : 'false');
            }
            applyLens(key);
          });
        })(tabs[t]);
      }
      card.setAttribute('data-psc-lens-wired','1');
    }catch(e){ /* never throw into the page */ }
  }
})();
</script>
"""


def _render_changelog(card: Any) -> str:
    """The "how this story shifted" heartbeat (doc 49 EKG). Reads the recent
    snapshot deltas attached by ``_attach_changelog`` as ``card.changelog`` —
    a list of ``{"as_of","week","delta"}`` (newest-first, already capped). This
    is supporting context, not the lead, so it lives inside the expand panel.

    GRACEFUL-EMPTY: returns "" when there is no changelog (a brand-new or
    never-shifted player). Silence is correct — no "no changes" placeholder.
    Every dynamic value is escaped; never injects raw HTML.
    """
    entries = _attr(card, "changelog", []) or []
    if not isinstance(entries, (list, tuple)):
        return ""
    rows = ""
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        delta = str(entry.get("delta", "") or "").strip()
        if not delta:  # a snapshot with no human-readable delta is not a row
            continue
        as_of = str(entry.get("as_of", "") or "").strip()
        week = entry.get("week", None)
        # Prefer the date; fall back to "Wk N" when only the week is known.
        if as_of:
            date_txt = as_of
        elif week not in (None, ""):
            try:
                date_txt = f"Wk {int(week)}"
            except (TypeError, ValueError):
                date_txt = str(week)
        else:
            date_txt = ""
        date_html = (
            f'<span class="psc-ekg__date">{escape(date_txt)}</span>' if date_txt else ""
        )
        rows += (
            '<li class="psc-ekg__row">'
            f'{date_html}'
            f'<span class="psc-ekg__delta">{escape(delta)}</span>'
            '</li>'
        )
    if not rows:
        return ""
    return (
        '<div class="psc-ekg">'
        '<span class="psc-ekg__eyebrow">How this story shifted</span>'
        f'<ul class="psc-ekg__list">{rows}</ul>'
        '</div>'
    )


def _render_citations(card: Any) -> str:
    """The AI-disclosure / provenance footer receipts (doc 41 §8)."""
    citations = _attr(card, "citations", []) or []
    items = ""
    for receipt in citations:
        rec = _render_receipt(receipt)
        if rec:
            items += f'<li class="psc-cite">{rec}</li>'
    if not items:
        return ""
    return f'<ul class="psc-cites">{items}</ul>'


def _render_expanded(card: Any) -> str:
    """The collapsed-by-default expand panel (doc 41 §4 bottom). Contains the
    6-beat recap, kicker, succession, why-now, and the changelog heartbeat."""
    body = _attr(card, "body", "")
    kicker = _safe_str(_attr(card, "kicker", ""))
    why_now = _safe_str(_attr(card, "why_now", ""))
    succession_html = _render_succession(card)
    changelog_html = _render_changelog(card)
    citations_html = _render_citations(card)

    body_html = ""
    if body:
        # body is deterministic templated copy in v1; split paragraphs on blank
        # lines (or newlines), escape each, never inject raw HTML.
        paras = [p.strip() for p in re.split(r"\n\s*\n|\r\n\r\n", str(body)) if p.strip()]
        if not paras:
            paras = [str(body).strip()]
        body_html = "".join(
            f'<p class="psc-recap__para">{escape(p)}</p>' for p in paras
        )

    why_now_html = (
        '<div class="psc-whynow">'
        '<span class="psc-whynow__tag">Why now</span>'
        f'<span class="psc-whynow__text">{why_now}</span>'
        '</div>'
        if why_now else ""
    )
    kicker_html = f'<p class="psc-recap__kicker">{kicker}</p>' if kicker else ""

    if not (
        body_html
        or kicker_html
        or why_now_html
        or succession_html
        or changelog_html
        or citations_html
    ):
        return ""

    # grid-template-rows:0fr->1fr expand — the inner wrapper is the animated row.
    # Order: recap -> kicker -> succession -> why-now -> changelog ("how this
    # story shifted", supporting context) -> citations.
    return (
        '<div class="psc-expand">'
        '<div class="psc-expand__inner">'
        f'{body_html}'
        f'{kicker_html}'
        f'{succession_html}'
        f'{why_now_html}'
        f'{changelog_html}'
        f'{citations_html}'
        '</div>'
        '</div>'
    )


# ---------------------------------------------------------------------------
# Low-data fallback (doc 41 §5) — REQUIRED. Motionless, no drama.
# ---------------------------------------------------------------------------
def render_stats_strip(card: "StoryCard") -> str:
    """The low-data factual bio strip (doc 41 §5). Bio + one real stat, no
    logline / BAN / chapter. Honest > dramatic. Always motionless."""
    if card is None:
        return ""
    name = _safe_str(_attr(card, "player_name", "") or _attr(card, "player_external_id", "Player"))
    meta = _safe_str(_attr(card, "identity_meta", ""))
    meta_html = f'<p class="psc-identity__meta">{meta}</p>' if meta else ""

    # One real stat: prefer the first key-stat chip, else a generic note.
    chips = _attr(card, "key_stat_chips", []) or []
    stat_html = ""
    bits = []
    for chip in chips:
        if not isinstance(chip, dict):
            continue
        value = str(chip.get("value", "")).strip()
        label = str(chip.get("label", "")).strip()
        if value and label:
            bits.append(f"{escape(value)} {escape(label)}")
        elif value:
            bits.append(escape(value))
        if len(bits) >= 3:
            break
    if bits:
        stat_html = (
            '<p class="psc-strip__stat">'
            f'{" · ".join(bits)}'
            '</p>'
        )
    note = _safe_str(
        _attr(card, "fallback_reason", "")
        or "Limited signal — not enough coverage for a story yet."
    )
    team_style = _team_color_style(card)
    return (
        f'<section class="psc-card psc-card--strip" data-tier="t3"{team_style} '
        'data-module="player-story-card" data-state="stats-strip" '
        'aria-label="Player bio">'
        '<div class="psc-card__rail" aria-hidden="true"></div>'
        '<div class="psc-card__inner">'
        '<div class="psc-identity">'
        '<span class="psc-identity__crest" aria-hidden="true"></span>'
        '<div class="psc-identity__text">'
        f'<p class="psc-identity__name">{name}</p>'
        f'{meta_html}'
        '</div>'
        '</div>'
        f'<p class="psc-strip__note">{note}</p>'
        f'{stat_html}'
        '</div>'
        '</section>'
    )


# ---------------------------------------------------------------------------
# Top-level render
# ---------------------------------------------------------------------------
def render_story_card(card: "Optional[StoryCard]") -> str:
    """Render the full StoryCard payload to Noir Dossier HTML.

    Returns "" when card is None or the fallback rung is 'omit'. Routes to the
    motionless stats-strip when tier is 'stats-strip' (the low-data path).
    NEVER raises — any unexpected shape degrades to "".
    """
    if card is None:
        return ""
    try:
        rung = str(_attr(card, "fallback_rung", "") or "").strip().lower()
        if rung == "omit":
            return ""

        tier = str(_attr(card, "tier", "stats-strip") or "stats-strip").strip().lower()
        if tier != "narrative":
            return render_stats_strip(card)

        logline = _safe_str(_attr(card, "logline", ""))
        # A narrative card with no logline has no lead — fall back to the strip
        # rather than ship a headless dossier (doc 41 §1 "story on intent").
        if not logline:
            return render_stats_strip(card)

        rail = _tier_rail(card)
        team_style = _team_color_style(card)
        archetype = str(_attr(card, "archetype_slug", "") or "")
        archetype_attr = f' data-archetype="{escape(archetype)}"' if archetype else ""

        identity_html = _render_identity(card)
        chapter_html = _render_chapter(card)
        chips_html = _render_chips(card)
        ban_html = _render_ban(card)
        take_html = _render_dominant_take(card)
        tension_html = _render_tension(card)
        expand_html = _render_expanded(card)
        # Tribal-Lens POV toggle (doc 49 §2). Emits a toggle bar + inline JSON
        # payload ONLY when >= 2 lenses qualify; otherwise both are "" and the
        # card renders in its single (National) voice exactly as before.
        lens_toggle_html, lens_payload_html = _render_lens_toggle(card)
        uid = _safe_str(_attr(card, "player_external_id", "") or "")
        uid_attr = f' data-psc-card-uid="{uid}"' if uid else ""

        as_of = _safe_str(_attr(card, "as_of_date", ""))
        disclosure = (
            '<p class="psc-disclosure">'
            'AI narrative'
            + (f' · updated {as_of}' if as_of else "")
            + ' · compiled from your data'
            '</p>'
        )

        # The expand affordance is a native <details>/<summary> (works SSR / no-JS).
        if expand_html:
            expand_block = (
                '<details class="psc-details">'
                '<summary class="psc-summary">'
                '<span class="psc-summary__label">Read the story so far</span>'
                '<span class="psc-summary__chevron" aria-hidden="true"></span>'
                '</summary>'
                f'{expand_html}'
                f'{disclosure}'
                '</details>'
            )
        else:
            expand_block = f'<div class="psc-foot">{disclosure}</div>'

        return (
            f'<section class="psc-card psc-card--narrative" data-tier="{rail}"'
            f'{team_style}{archetype_attr}{uid_attr} '
            'data-module="player-story-card" data-state="narrative" '
            'aria-label="Player story card">'
            '<div class="psc-card__rail" aria-hidden="true"></div>'
            '<div class="psc-card__inner">'
            '<div class="psc-card__head">'
            f'{identity_html}'
            f'{chapter_html}'
            '</div>'
            f'<p class="psc-logline">{logline}</p>'
            f'{lens_toggle_html}'
            f'{chips_html}'
            f'{ban_html}'
            f'{take_html}'
            f'{tension_html}'
            f'{expand_block}'
            f'{lens_payload_html}'
            '</div>'
            '</section>'
        )
    except Exception:
        # Defense in depth — a render error must never blank the page.
        return ""


# ---------------------------------------------------------------------------
# RAW CSS — NO <style> tags (concatenated into the player-page outer <style>).
# Scoped under .psc-* ; tokens taken verbatim from doc 41 §2/§8.5.
# ---------------------------------------------------------------------------
STORY_CARD_CSS = """
/* Player Story Card ("Dossier Noir") — doc 41. Raw css; the player page wraps it. */
.psc-card {
  /* Locked Noir tokens (doc 41 §2) — card-scoped, WCAG-checked dark palette. */
  --psc-ink-900: #0A0A0D;
  --psc-ink-850: #101015;
  --psc-ink-800: #16161C;
  --psc-hairline: #2A2A33;
  --psc-hairline-strong: #3A3A45;
  --psc-gold: #ECC15C;
  --psc-gold-deep: #CA8A04;
  --psc-text-hi: #F4EFE7;
  --psc-text-body: #DAD4C9;
  --psc-text-mut: #ABA59B;
  --psc-team: var(--psc-gold);
  /* Motion tokens (doc 41 §8.5) */
  --psc-ease-out: cubic-bezier(.22,.61,.36,1);
  --psc-ease-in: cubic-bezier(.55,.06,.68,.19);
  --psc-ease-spring: cubic-bezier(.34,1.56,.64,1);
  --psc-t-micro: 120ms;
  --psc-t-state: 320ms;
  --psc-t-entrance: 450ms;
  --psc-t-ban: 420ms;

  position: relative;
  display: flex;
  margin: 0 0 clamp(16px, 2.5vw, 24px) 0;
  background: var(--psc-ink-800);
  border: 1px solid var(--psc-hairline);
  border-radius: 14px;
  overflow: hidden;
  color: var(--psc-text-body);
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
}
.psc-card--narrative {
  opacity: 0;
  transform: translateY(8px);
  animation: psc-card-in var(--psc-t-entrance) var(--psc-ease-out) forwards;
}
@keyframes psc-card-in {
  to { opacity: 1; transform: translateY(0); }
}

/* Tier rail (tier-is-texture, §1/§4) */
.psc-card__rail {
  flex: 0 0 4px;
  align-self: stretch;
  background: var(--psc-hairline);
}
.psc-card[data-tier="s"]  .psc-card__rail { background: var(--psc-gold); }
.psc-card[data-tier="t1"] .psc-card__rail { background: #C7CBD1; }
.psc-card[data-tier="t2"] .psc-card__rail { background: #B08D57; }
.psc-card[data-tier="t3"] .psc-card__rail { background: var(--psc-hairline); }
/* S-tier one-time top->bottom sweep, tied to the entrance gesture. */
.psc-card--narrative[data-tier="s"] .psc-card__rail {
  background: linear-gradient(180deg,
    var(--psc-gold-deep) 0%, var(--psc-gold) 50%, var(--psc-gold-deep) 100%);
  background-size: 100% 220%;
  background-position: 0 100%;
  animation: psc-rail-sweep var(--psc-t-entrance) var(--psc-ease-out) forwards;
}
@keyframes psc-rail-sweep { to { background-position: 0 0; } }

.psc-card__inner {
  flex: 1 1 auto;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: clamp(12px, 1.8vw, 16px);
  padding: clamp(16px, 2.2vw, 22px) clamp(16px, 2.4vw, 24px);
}
.psc-card__head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  flex-wrap: wrap;
}

/* Identity anchor (team-color touch only) */
.psc-identity { display: flex; align-items: center; gap: 12px; min-width: 0; }
.psc-identity__crest {
  flex: 0 0 auto;
  width: 40px; height: 40px;
  border-radius: 50%;
  background: var(--psc-ink-850);
  border: 2px solid var(--psc-team);
}
.psc-identity__text { min-width: 0; }
.psc-identity__name {
  margin: 0;
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: clamp(16px, 2.4vw, 19px);
  font-weight: 700;
  line-height: 1.15;
  color: var(--psc-text-hi);
  letter-spacing: -0.01em;
  border-bottom: 2px solid var(--psc-team);
  display: inline-block;
  padding-bottom: 2px;
  overflow-wrap: anywhere;
}
.psc-identity__meta {
  margin: 4px 0 0 0;
  font-size: 12px;
  letter-spacing: 0.04em;
  color: var(--psc-text-mut);
  font-variant-numeric: tabular-nums;
  font-feature-settings: 'tnum' 1;
}

/* Chapter chip + freshness */
.psc-chapter {
  display: flex; align-items: center; gap: 10px;
  flex-wrap: wrap; justify-content: flex-end;
}
.psc-chapter__chip {
  font-size: 11px; font-weight: 700;
  letter-spacing: 0.10em; text-transform: uppercase;
  color: var(--psc-gold);
  padding: 4px 10px;
  border: 1px solid var(--psc-hairline-strong);
  border-radius: 999px;
  white-space: nowrap;
}
.psc-chapter__fresh {
  font-size: 12px; color: var(--psc-text-mut);
  letter-spacing: 0.02em; white-space: nowrap;
  font-variant-numeric: tabular-nums;
}

/* Logline — mixed-case serif (NEVER all-caps) */
.psc-logline {
  margin: 0;
  font-family: var(--font-serif, 'Source Serif Pro', Georgia, serif);
  font-size: clamp(18px, 3.2vw, 23px);
  line-height: 1.35;
  color: var(--psc-text-hi);
  overflow-wrap: anywhere;
}

/* Key-stat chips — STATIC (reads as fact, §8.5) */
.psc-chips { display: flex; flex-wrap: wrap; gap: 8px; }
.psc-chip {
  display: inline-flex; align-items: baseline; gap: 6px;
  padding: 6px 12px;
  background: var(--psc-ink-850);
  border: 1px solid var(--psc-hairline);
  border-radius: 9px;
  transition: transform var(--psc-t-micro) var(--psc-ease-out),
              border-color var(--psc-t-micro) var(--psc-ease-out);
}
.psc-chip:hover { transform: translateY(-1px); border-color: var(--psc-hairline-strong); }
.psc-chip__value {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 15px; font-weight: 700;
  color: var(--psc-text-hi);
  font-variant-numeric: tabular-nums;
  font-feature-settings: 'tnum' 1;
}
.psc-chip__label {
  font-size: 10px; font-weight: 600;
  letter-spacing: 0.10em; text-transform: uppercase;
  color: var(--psc-text-mut);
}

/* BAN — the single big honest number, number welded to label (§6) */
.psc-ban {
  background: var(--psc-ink-850);
  border: 1px solid var(--psc-hairline);
  border-radius: 12px;
  padding: clamp(14px, 2vw, 18px) clamp(16px, 2.2vw, 20px);
}
.psc-ban__label {
  margin: 0;
  font-size: 11px; font-weight: 700;
  letter-spacing: 0.14em; text-transform: uppercase;
  color: var(--psc-text-mut);
}
.psc-ban__number {
  margin: 4px 0 0 0;
  font-family: var(--font-display, 'Bebas Neue', sans-serif);
  font-size: clamp(44px, 9vw, 68px);
  line-height: 0.92;
  color: var(--psc-gold);
  font-variant-numeric: tabular-nums;
  font-feature-settings: 'tnum' 1;
  letter-spacing: 0.01em;
}
/* The BAN is the ONE animated numeric hero in the view (§8.5). */
.psc-card--narrative .psc-ban__number {
  transform: scale(1.1);
  opacity: 0;
  animation: psc-ban-settle var(--psc-t-ban) var(--psc-ease-spring) 150ms forwards;
}
@keyframes psc-ban-settle { to { transform: scale(1); opacity: 1; } }
.psc-ban__receipt { margin: 8px 0 0 0; }

/* Receipts — hoverable source markers (doc 41 §1.3) */
.psc-receipt {
  display: inline-flex; align-items: baseline; gap: 6px;
  font-size: 12px; color: var(--psc-text-mut);
  text-decoration: none;
  letter-spacing: 0.02em;
}
.psc-receipt__mark {
  font-size: 9px; font-weight: 700;
  letter-spacing: 0.10em; text-transform: uppercase;
  color: var(--psc-gold);
  border: 1px solid var(--psc-hairline-strong);
  border-radius: 4px;
  padding: 1px 4px;
}
a.psc-receipt:hover { color: var(--psc-text-body); text-decoration: underline; }

/* Dominant take + confidence meter (compile, don't adjudicate) */
.psc-take {
  display: flex; flex-direction: column; gap: 8px;
  padding-top: clamp(10px, 1.6vw, 14px);
  border-top: 1px solid var(--psc-hairline);
}
.psc-take__text {
  margin: 0;
  font-family: var(--font-serif, 'Source Serif Pro', Georgia, serif);
  font-size: clamp(14px, 2.2vw, 16px);
  line-height: 1.45;
  color: var(--psc-text-body);
}
.psc-take__meter-row {
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
}
.psc-take__meter {
  flex: 1 1 120px; min-width: 100px; max-width: 220px;
  height: 6px; border-radius: 999px;
  background: var(--psc-ink-850);
  border: 1px solid var(--psc-hairline);
  overflow: hidden;
}
.psc-take__meter-fill {
  display: block; height: 100%;
  background: var(--psc-gold);
  border-radius: 999px;
}
.psc-take__meter-fill[data-band="medium"] { background: var(--psc-gold-deep); }
.psc-take__meter-fill[data-band="low"]    { background: var(--psc-hairline-strong); }
.psc-take__meter-label {
  font-size: 11px; font-weight: 700;
  letter-spacing: 0.08em; text-transform: uppercase;
  color: var(--psc-text-mut);
}
.psc-take__meter-label[data-band="high"] { color: var(--psc-gold); }
.psc-take__sources {
  font-size: 11px; color: var(--psc-text-mut);
  letter-spacing: 0.04em;
  font-variant-numeric: tabular-nums;
}
.psc-take__minority {
  margin: 0;
  font-size: 13px; line-height: 1.45;
  color: var(--psc-text-mut);
  font-family: var(--font-serif, 'Source Serif Pro', Georgia, serif);
}
.psc-take__minority-tag {
  display: inline-block; margin-right: 6px;
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 10px; font-weight: 700;
  letter-spacing: 0.10em; text-transform: uppercase;
  color: var(--psc-text-mut);
  border: 1px solid var(--psc-hairline-strong);
  border-radius: 4px;
  padding: 1px 6px;
}

/* Tension line — serif italic */
.psc-tension {
  margin: 0;
  font-family: var(--font-serif, 'Source Serif Pro', Georgia, serif);
  font-style: italic;
  font-size: clamp(14px, 2.2vw, 16px);
  line-height: 1.5;
  color: var(--psc-text-body);
}

/* Expand affordance — native <details>/<summary>, ≥44px target */
.psc-details { margin: 0; }
.psc-summary {
  display: flex; align-items: center; justify-content: space-between;
  gap: 10px;
  min-height: 44px;
  padding: 10px 14px;
  margin-top: clamp(8px, 1.4vw, 12px);
  background: var(--psc-ink-850);
  border: 1px solid var(--psc-hairline-strong);
  border-radius: 10px;
  cursor: pointer;
  list-style: none;
  color: var(--psc-gold);
  user-select: none;
  transition: transform var(--psc-t-micro) var(--psc-ease-out);
}
.psc-summary::-webkit-details-marker { display: none; }
.psc-summary:active { transform: scale(.98); }
.psc-summary:focus-visible {
  outline: 2px solid var(--psc-gold);
  outline-offset: 2px;
}
.psc-summary__label {
  font-size: 13px; font-weight: 700;
  letter-spacing: 0.06em; text-transform: uppercase;
}
.psc-summary__chevron {
  flex: 0 0 auto;
  width: 10px; height: 10px;
  border-right: 2px solid currentColor;
  border-bottom: 2px solid currentColor;
  transform: rotate(45deg);
  transition: transform var(--psc-t-micro) var(--psc-ease-out);
}
.psc-details[open] .psc-summary__chevron { transform: rotate(-135deg); }

/* Expand panel — grid-template-rows:0fr->1fr (intrinsic height, no magic number) */
.psc-expand {
  display: grid;
  grid-template-rows: 1fr;       /* open state; details[open] reveals this node */
  transition: grid-template-rows var(--psc-t-state) var(--psc-ease-out);
}
.psc-expand__inner {
  overflow: hidden;
  min-height: 0;
  display: flex; flex-direction: column;
  gap: clamp(10px, 1.6vw, 14px);
  padding-top: clamp(12px, 1.8vw, 16px);
  opacity: 1;
  animation: psc-reveal var(--psc-t-state) var(--psc-ease-out);
}
@keyframes psc-reveal {
  from { opacity: 0; transform: translateY(6px); }
  to   { opacity: 1; transform: translateY(0); }
}

.psc-recap__para {
  margin: 0;
  font-family: var(--font-serif, 'Source Serif Pro', Georgia, serif);
  font-size: 15px; line-height: 1.6;
  color: var(--psc-text-body);
}
.psc-recap__kicker {
  margin: 0;
  font-family: var(--font-serif, 'Source Serif Pro', Georgia, serif);
  font-size: 15px; font-style: italic; line-height: 1.5;
  color: var(--psc-text-hi);
}

/* Succession (Filling-the-Shoes + the Clock) */
.psc-succ {
  background: var(--psc-ink-850);
  border: 1px solid var(--psc-hairline);
  border-radius: 10px;
  padding: 12px 14px;
}
.psc-succ__head {
  display: flex; align-items: center; justify-content: space-between;
  gap: 8px; margin-bottom: 8px;
}
.psc-succ__eyebrow {
  font-size: 10px; font-weight: 700;
  letter-spacing: 0.12em; text-transform: uppercase;
  color: var(--psc-text-mut);
}
.psc-succ__read {
  font-size: 11px; font-weight: 700;
  letter-spacing: 0.06em; text-transform: capitalize;
  color: var(--psc-gold);
  border: 1px solid var(--psc-hairline-strong);
  border-radius: 999px;
  padding: 2px 10px;
}
.psc-succ__list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
.psc-succ__line { display: flex; align-items: baseline; gap: 8px; }
.psc-succ__role {
  font-size: 10px; font-weight: 700;
  letter-spacing: 0.08em; text-transform: uppercase;
  color: var(--psc-text-mut);
  flex: 0 0 auto;
}
.psc-succ__name {
  font-size: 14px; color: var(--psc-text-body);
}
.psc-succ__stars { color: var(--psc-gold); font-variant-numeric: tabular-nums; }
.psc-succ__line--clock { margin-top: 2px; }
.psc-succ__clock {
  font-size: 13px; font-style: italic;
  font-family: var(--font-serif, 'Source Serif Pro', Georgia, serif);
  color: var(--psc-text-hi);
}

/* Why-now heartbeat */
.psc-whynow {
  display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap;
  padding-top: 4px;
}
.psc-whynow__tag {
  font-size: 10px; font-weight: 700;
  letter-spacing: 0.10em; text-transform: uppercase;
  color: var(--psc-gold);
  border: 1px solid var(--psc-hairline-strong);
  border-radius: 4px;
  padding: 1px 6px;
}
.psc-whynow__text {
  font-size: 14px; line-height: 1.45; color: var(--psc-text-body);
}

/* Provenance footer */
.psc-cites { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: 8px 14px; }
.psc-cite { display: inline-flex; }
.psc-foot { padding-top: clamp(8px, 1.4vw, 12px); }
.psc-disclosure {
  margin: clamp(8px, 1.4vw, 12px) 0 0 0;
  font-size: 11px; color: var(--psc-text-mut);
  letter-spacing: 0.04em;
}

/* Tribal-Lens POV toggle (doc 49 §2) — sits just under the logline. A Noir
   pill row; only rendered when >= 2 lenses qualify (else no toggle at all).
   Static text swap (no animation beyond the micro border transition). */
.psc-lens {
  display: flex; flex-wrap: wrap; gap: 8px;
  margin: 0;
}
.psc-lens__tab {
  appearance: none;
  display: inline-flex; align-items: center;
  min-height: 32px;
  padding: 4px 14px;
  background: var(--psc-ink-850);
  border: 1px solid var(--psc-hairline);
  border-radius: 999px;
  cursor: pointer;
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 11px; font-weight: 700;
  letter-spacing: 0.08em; text-transform: uppercase;
  color: var(--psc-text-mut);
  transition: border-color var(--psc-t-micro) var(--psc-ease-out),
              color var(--psc-t-micro) var(--psc-ease-out);
}
.psc-lens__tab:hover { border-color: var(--psc-hairline-strong); color: var(--psc-text-body); }
.psc-lens__tab[aria-selected="true"] {
  color: var(--psc-gold);
  border-color: var(--psc-gold);
}
.psc-lens__tab:focus-visible {
  outline: 2px solid var(--psc-gold);
  outline-offset: 2px;
}

/* Changelog / EKG ("how this story shifted") — inside the expand panel; small,
   static, motionless. Hairline left-border per row, tabular date. */
.psc-ekg {
  display: flex; flex-direction: column; gap: 6px;
  padding-top: 4px;
}
.psc-ekg__eyebrow {
  font-size: 10px; font-weight: 700;
  letter-spacing: 0.12em; text-transform: uppercase;
  color: var(--psc-text-mut);
}
.psc-ekg__list {
  list-style: none; margin: 0; padding: 0;
  display: flex; flex-direction: column; gap: 6px;
}
.psc-ekg__row {
  display: flex; align-items: baseline; gap: 10px;
  padding-left: 10px;
  border-left: 2px solid var(--psc-hairline-strong);
}
.psc-ekg__date {
  flex: 0 0 auto;
  font-size: 11px; color: var(--psc-text-mut);
  letter-spacing: 0.02em;
  font-variant-numeric: tabular-nums;
  font-feature-settings: 'tnum' 1;
  white-space: nowrap;
}
.psc-ekg__delta {
  font-size: 13px; line-height: 1.45;
  color: var(--psc-text-body);
  overflow-wrap: anywhere;
}

/* Low-data stats strip (§5) — motionless always */
.psc-card--strip { animation: none; opacity: 1; transform: none; }
.psc-card--strip .psc-card__inner { gap: 8px; }
.psc-strip__note {
  margin: 0;
  font-family: var(--font-serif, 'Source Serif Pro', Georgia, serif);
  font-size: 14px; line-height: 1.5;
  color: var(--psc-text-body);
}
.psc-strip__stat {
  margin: 0;
  font-size: 13px; color: var(--psc-text-mut);
  letter-spacing: 0.02em;
  font-variant-numeric: tabular-nums;
  font-feature-settings: 'tnum' 1;
}

/* Mobile-first: stack head when narrow */
@media (max-width: 520px) {
  .psc-card__head { flex-direction: column; gap: 8px; }
  .psc-chapter { justify-content: flex-start; }
}

/* prefers-reduced-motion: kill ALL motion (entrance, BAN, sweep, reveal) */
@media (prefers-reduced-motion: reduce) {
  .psc-card--narrative,
  .psc-card--narrative[data-tier="s"] .psc-card__rail,
  .psc-card--narrative .psc-ban__number,
  .psc-expand,
  .psc-expand__inner,
  .psc-chip,
  .psc-lens__tab,
  .psc-summary,
  .psc-summary__chevron {
    animation: none !important;
    transition: none !important;
  }
  .psc-card--narrative { opacity: 1; transform: none; }
  .psc-card--narrative .psc-ban__number { opacity: 1; transform: none; }
}

/* prefers-contrast: more — bump borders + text (doc 41 §2) */
@media (prefers-contrast: more) {
  .psc-card { border-color: var(--psc-hairline-strong); }
  .psc-chip, .psc-ban, .psc-succ, .psc-take__meter { border-color: var(--psc-hairline-strong); }
  .psc-identity__meta, .psc-take__meter-label, .psc-chip__label,
  .psc-ban__label, .psc-receipt, .psc-disclosure, .psc-strip__stat {
    color: var(--psc-text-hi);
  }
}

/* Print ink-saver (doc 41 §2): white bg, near-black ink, gold -> #8a6d10 */
@media print {
  .psc-card {
    --psc-ink-900: #ffffff;
    --psc-ink-850: #f4f2ec;
    --psc-ink-800: #ffffff;
    --psc-text-hi: #14130f;
    --psc-text-body: #2a2823;
    --psc-text-mut: #4a463d;
    --psc-gold: #8a6d10;
    --psc-gold-deep: #8a6d10;
    --psc-hairline: #cfcabd;
    --psc-hairline-strong: #aaa494;
    border-color: #cfcabd;
    color: #2a2823;
    animation: none;
    opacity: 1; transform: none;
  }
  .psc-card--narrative .psc-ban__number { animation: none; opacity: 1; transform: none; }
  .psc-details[open] .psc-expand,
  .psc-details:not([open]) .psc-expand__inner { display: block; }
}
"""

__all__ = ["render_story_card", "render_stats_strip", "STORY_CARD_CSS"]
