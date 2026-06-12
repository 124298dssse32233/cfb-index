# 47 — Fan-Ledger Detectors (Lexicons + Signals + Thresholds)

_Status: DETECTOR SPEC (v1). Created 2026-06-11. Turns the five Fan Ledgers ([[43-cfb-native-content-model]] §1) from concepts into buildable detectors. Lexicons are grounded in real corpus frequencies (194,967 docs queried 2026-06-11), not guessed. **Method is HYBRID — a target-based stance/emotion classifier (the encoder/LLM stack already in the repo) with the lexicons as the interpretable feature/seed/explanation layer, per 2026 best practice (§1).** Not yet implemented._

---

## 0. Why grounded lexicons

Textbook fan phrases don't match real fan language. In this corpus: "nobody believes" appears **0** times and "could be special" **1**; meanwhile "doubt" (611), "joke" (324), "underrated" (208) carry the Grievance signal. The lexicons below are pulled from actual frequencies, so the detectors fire on words your fans really use.

---

## 1. Method — 2026 best practice (hybrid stance, NOT a pure-lexicon counter)

The 2026 literature is unambiguous: **pure lexicon counting is a weak baseline** — fine-tuned transformers beat lexicon labels (VADER/TextBlob) by 38–72%, and lexicons misfire on exactly what CFB discourse is full of (sarcasm, irony, brigading). So a ledger is a **target-based stance/emotion classification** — *does this doc express Hope / Grievance / … toward THIS player?* — run on the **encoder/LLM stack already in the repo** (CardiffNLP emotion encoders + Qwen3 for aspect/stance), with the grounded lexicons as the **hybrid interpretable layer**, never the sole signal.

Lexicons earn their place three ways (the LexiRoBERTaNet pattern): **(a) features** fed alongside the transformer, **(b) weak-supervision seeds** to bootstrap labels for a fine-tune, and **(c) the human-readable "why this ledger fired" trace** (so you — and skeptical fans — can audit a call).

Per doc, per player-target:

```
1. docs = conversation_document_targets WHERE player_id=P, window W,
          relevance-filtered (relevance_ml_score) — off-topic noise out.
2. TARGET-STANCE classify each doc toward P, per ledger:
     primary = encoder / Qwen3 zero-shot stance (zero-shot > few-shot on
               2026 cost/accuracy; a fine-tuned small encoder is competitive);
     features += lexicon hits (§2) + directionality (§3) + sarcasm_score.
3. Aggregate to a RATE per ledger (hits/mentions — stars don't dominate),
   scored vs the player's rolling baseline + cohort prior
   (empirical-Bayes shrinkage — cold-start safe).
4. FIRE only if above noise floor AND representativeness met
   (>= MIN_DOCS docs from >= MIN_SOURCES independent sources).
5. confidence = model agreement × source diversity × (1 - sarcasm risk).
6. Write player_ledger_scores(player_external_id, week, ledger, score,
   direction, confidence, evidence_doc_ids, top_lexical_trace).
```

Output feeds salience ([[42-player-narrative-engine]] §4) and composition (§4b); the `confidence` drives the card's confidence meter ([[49-pragmatic-v1-critique-corrected]] C1). The lexicons in §2 are the *seed/feature/explanation* set — not a standalone detector.

---

## 2. The lexicons (grounded; corpus counts in parentheses)

> Counts are corpus-wide substring frequency — directional/contextual gating (§3) refines them. Curate to word-boundary + lemma at build time; the counts establish which terms are real signal vs dead weight.

### 2.1 Grievance — *disrespect as fuel* (direction: US)
Core: `doubt`(611) · `joke`(324) · `underrated`(208) · `screwed`(153) · `snub`(130) · `disrespect`(127) · `biased`(91) · `robbed`(39).
Variants/phrases: `slept on`, `no love`, `count us out`, `prove them wrong`, `bulletin board`, `chip on`, `written off`.
Villain-tag (who's disrespecting): `media`, `espn`, `committee`, `pollsters`, `analysts`.
**Drop:** "nobody believes"(0).

### 2.2 Hope — *potential > production* (the dominant register)
Core: `future`(5522) · `potential`(3912) · `next year`(1095) · `breakout`(507) · `ceiling`(292) · `dawg`(290) · `sleeper`(69).
Variants: `wait till`, `just wait`, `if he develops`, `upside`, `franchise`, `the guy of the future`, `buy stock`, `glue`, `special`.
**Gate:** `him`(5236) and `future` are noisy — require player-target proximity + word boundary; never count corpus-wide.

### 2.3 Belonging — *love orthogonal to talent* (direction: US)
Core: `loyal`(2084) · `culture`(982) · `stayed`(241) · `hometown`(155) · `our guy`(121) · `one of us`(60) · `homegrown`(41) · `bleeds`(25).
Variants: `four-year`, `never left`, `turned down the bag`, `local kid`, `in-state`, `program guy`, `dog`, `warrior`, `glue guy`.
Signal pairs with structured Belonging (tenure from `roster_entries`, in-state from recruiting geo).

### 2.4 Judgment — *fans as jury* (direction: contested)
Core: `deserve`(2484) · `legit`(571) · `resume`(400) · `strength of schedule`(64) · `eye test`(16) · `overrated`(78).
Variants: `system`, `stat padder`, `empty stats`, `hasn't played anyone`, `should be ranked`, `not elite`, `mid`, `washed`, `proven`.
This is the eye-test-vs-résumé argument; surface the *disagreement*, don't resolve it.

### 2.5 Grudge — *rooting against > for* (direction: THEM / rival audience)
Core: `rival`(2370) · `hate`(2154) · `owned`(441) · `cope`(184) · `beat them`(98) · `fraud`(92) · `overrated`(78) · `choke`(56) · `rent free`(17).
Variants: `seething`, `clown`, `bust`, `washed`, `gets exposed`, `cooked`, `L`, `down bad`.
**Direction is everything:** the same word (`overrated`) is Grievance when local fans defend "us" vs Grudge when rivals mock "them."

---

## 3. Directionality (the polysemy fix)

Several terms cross ledgers; **audience + person disambiguate**:

| Term | local + 1st person ("we/us") | rival + 3rd person ("they/he") |
|---|---|---|
| overrated / underrated | Grievance (we're underrated) | Grudge / Judgment (he's overrated) |
| fraud / washed | (rare, self-doubt) | Grudge |
| deserve | Grievance (we deserve better) | Judgment (does he deserve it?) |

Use `audience_bucket` (local/rival) + a light first/second/third-person check. No direction signal → assign to Judgment (the neutral "is he good" argument).

---

## 4. Thresholds (start here, tune against labels)

| Param | Default | Why |
|---|---|---|
| `MIN_DOCS` | 5 distinct tagged docs in window | representativeness ([[42-player-narrative-engine]] §6) |
| `MIN_SOURCES` | 2 independent origins | one troll/bot ≠ a narrative |
| `FIRE_THRESHOLD` | rate > cohort 75th pct **or** z > 1.0 | above noise |
| `LEAD_THRESHOLD` | z > 2.0 | strong enough to lead the card |
| `sarcasm guard` | down-weight when `sarcasm_score` high | existing signal; avoids ironic false-fires |

Long-tail players below `MIN_DOCS` get **no ledger** (→ low-data strip), distinguishing "no story" from "no data" ([[42-player-narrative-engine]] §10).

---

## 5. Structured pairing (ledgers aren't discourse-only)

Each ledger fuses discourse with a structured anchor, so it fires even when chatter is thin and grounds the claim:

| Ledger | Structured anchor |
|---|---|
| Hope | recruiting stars/rank, NIL, award watch |
| Grievance | ranking position vs résumé/WEPA (the measurable respect gap) |
| Belonging | tenure (roster years), in-state (recruiting geo), lifer-vs-portal |
| Judgment | advanced stats vs qualitative claims; SOS |
| Grudge | rivalry results/margins, rival-audience sentiment |

This is the engine's "compile, don't adjudicate" stance ([[42-player-narrative-engine]] §1): the structured anchor is fact; the lexicon hit is *observed conversation*, always attributed.

---

## 6. Honest limits

- Lexicons need iteration against a small labeled set (the gold benchmark, [[42-player-narrative-engine]] §11) — these are v1 seeds, not final.
- Sarcasm/irony: do NOT strip it — CFB discourse *is* sarcasm, and stripping it is itself adjudication. Handle it the 2026 way: the context-aware classifier + `sarcasm_score` as a feature + topic-guided representation (which reduces reliance on the sentiment cues that cause errors), and surface residual uncertainty in the confidence meter rather than deleting the doc.
- Slang drifts season to season ("him," "dawg," "cooked") — schedule a periodic keyness re-mine to refresh the variant lists from the live corpus.
- Same-name players need entity resolution before counting (the player tagger already handles this).

## 7. Provenance

Lexicons grounded in real corpus frequencies (194,967 docs, queried 2026-06-11). **Method validated against 2026 best practice** (web research 2026-06-11): hybrid transformer+lexicon (LexiRoBERTaNet), target-based stance detection (cross-target survey 2026), zero-shot LLM > few-shot on cost/accuracy (Chae & Davidson 2026), topic-guided/context-aware sarcasm handling (not stripping). Pure-lexicon labels are beaten 38–72% by fine-tuned transformers — hence lexicons are the interpretable layer, not the classifier. Reuses the repo's existing stack (CardiffNLP encoders + Qwen3 ABSA + `sarcasm_score`). Detection design from [[42-player-narrative-engine]] §1/§4/§6 + [[43-cfb-native-content-model]] §1. Reads the live discourse plane (`conversation_document_targets`, `audience_bucket`, `relevance_ml_score`, `sarcasm_score`) + the keyness engine.
