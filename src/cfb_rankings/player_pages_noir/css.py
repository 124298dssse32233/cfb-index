"""Noir player-page CSS (plan doc 61 §5).

RAW CSS string — no <style> tags. EVERY selector is nested under `.theme-noir`
and ALL `--noir-*` tokens are declared on `.theme-noir` (never `:root`), so this
can never leak into the other ~69k site pages. The reused legacy modules are
repainted in-place by aliasing their `--pp-*`/`--psc-*` consumption to Noir tokens
inside the wrapper — the module code is NOT edited (preservation rule, §2).

Anton overrides the global Bebas ONLY inside `.theme-noir` (the global token is
untouched — [[60]] §9.1 "no global font swap").
"""
from __future__ import annotations


def noir_player_css() -> str:
    return _NOIR_CSS


_NOIR_CSS = """
/* ============================ NOIR PLAYER ROUTE ============================ */
.theme-noir{
  --noir-ground:#101418; --noir-surface:#1B2128; --noir-surface-2:#242C35;
  --noir-text:#EDE6D6; --noir-receipt:#B8B2A4; --noir-hairline:rgba(237,230,214,.10);
  --noir-up:#2EE07C; --noir-down:#FF4E42; --noir-aura:#B794FF; --noir-aura-graphic:#9D6BFF;
  --noir-market:#3D91FF; --noir-neutral:#A8A294;
  --noir-gold:#ECC15C; --noir-silver:#C7CBD1; --noir-bronze:#B08D57;
  --noir-font-display:'Anton','Bebas Neue',sans-serif;
  --noir-font-serif:'Source Serif 4','Source Serif Pro',Georgia,serif;
  --noir-font-sans:'Inter',system-ui,sans-serif;
  --noir-font-mono:'IBM Plex Mono',ui-monospace,monospace;
  /* repaint the reused legacy modules in-place (no module edit) */
  --font-display:var(--noir-font-display);
  --psc-gold:var(--noir-gold); --psc-aura:var(--noir-aura);
  --psc-up:var(--noir-up); --psc-down:var(--noir-down);
  --pp-surface:var(--noir-surface); --pp-surface-raised:var(--noir-surface-2);
  --pp-text-bright:var(--noir-text); --pp-text-soft:var(--noir-receipt);
  --accolade-gold-base:var(--noir-gold);
  background:var(--noir-ground); color:var(--noir-text);
  font-family:var(--noir-font-sans); max-width:760px; margin:0 auto; padding:0 18px 64px;
}
.theme-noir .nz{padding:34px 0 8px; border-top:1px solid var(--noir-hairline)}
.theme-noir .nz--first{border-top:0; padding-top:30px}
.theme-noir .nz__eyebrow{font-family:var(--noir-font-mono); font-size:11px; letter-spacing:.18em;
  color:var(--noir-receipt); text-transform:uppercase; margin:0 0 12px}
.theme-noir .nz__h{font-family:var(--noir-font-sans); font-weight:800; font-size:15px;
  letter-spacing:.04em; text-transform:uppercase; margin:0 0 10px}
.theme-noir .nreceipt{font-family:var(--noir-font-mono); font-size:11px; color:var(--noir-receipt); margin:8px 0 0}
/* HERO */
.theme-noir .nhero{display:flex; gap:18px; align-items:flex-start}
.theme-noir .nhero__rail{width:4px; align-self:stretch; border-radius:2px;
  background:linear-gradient(var(--noir-gold),#FFCB05)}
.theme-noir .nhero[data-tier="t1"] .nhero__rail{background:linear-gradient(var(--noir-silver),#E9ECF1)}
.theme-noir .nhero[data-tier="t2"] .nhero__rail{background:linear-gradient(var(--noir-bronze),#CBA978)}
.theme-noir .nhero[data-tier="t3"] .nhero__rail{background:var(--noir-hairline)}
.theme-noir .nhero__mono{width:64px;height:64px;border-radius:50%;border:2px solid var(--noir-gold);
  display:flex;align-items:center;justify-content:center;font-family:var(--noir-font-display);
  font-size:28px;color:var(--noir-gold);background:var(--noir-surface)}
.theme-noir .nhero__name{font-family:var(--noir-font-display); font-size:clamp(38px,8vw,54px);
  line-height:.92; letter-spacing:.01em; margin:2px 0 6px; text-transform:uppercase}
.theme-noir .nhero__eye{font-family:var(--noir-font-mono); font-size:12px; letter-spacing:.1em;
  color:var(--noir-receipt); text-transform:uppercase}
.theme-noir .nhero__score{display:flex; gap:22px; margin-top:14px; flex-wrap:wrap}
.theme-noir .nchip{display:flex; flex-direction:column}
.theme-noir .nchip b{font-family:var(--noir-font-sans); font-weight:700; font-size:22px; font-variant-numeric:tabular-nums}
.theme-noir .nchip span{font-family:var(--noir-font-mono); font-size:10px; letter-spacing:.1em;
  color:var(--noir-receipt); text-transform:uppercase; margin-top:2px}
/* reused-module wrapper: give every placed module a little breathing room */
.theme-noir .nmod{margin:14px 0 0}
/* VERDICT */
.theme-noir .nverdict{background:var(--noir-surface-2); border:1px solid var(--noir-hairline);
  padding:26px 22px; text-align:center; margin-top:6px}
.theme-noir .nverdict__w{font-family:var(--noir-font-display); font-size:clamp(26px,6vw,34px);
  text-transform:uppercase; letter-spacing:.02em}
.theme-noir .nverdict__k{font-family:var(--noir-font-serif); font-size:18px; font-style:italic; margin:8px 0 0}
/* FOOTER */
.theme-noir .nfoot{font-family:var(--noir-font-mono); font-size:11px; color:var(--noir-receipt); padding-top:24px}
@media (prefers-reduced-motion: reduce){ .theme-noir *{animation:none!important; transition:none!important} }
"""
