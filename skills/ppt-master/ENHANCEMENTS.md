# PPT Master Enhancement Suite

Optional layers on top of the main pipeline in [`SKILL.md`](SKILL.md). They remember your preferences, match templates from plain language, fix common SVG issues, and export editable Excel charts — without replacing the core workflow.

## What's New (latest)

- **Phase 6 — CI & documentation:** GitHub Actions runs lint, script smoke tests, and JSON validation on every push/PR to `main`. This file is the end-user changelog for all enhancement phases.
- **Phase 5 — Chart dual-mode:** Export native PowerPoint charts from SVG data (`--chart-mode excel|hybrid`).
- **Phase 4 — SVG auto-fix:** Quality check can repair viewBox, fonts, overflow, and empty groups automatically (`--auto-fix`).
- **Phases 1–3 — Smarter starts:** Saved Eight Confirmations, keyword template matching, and six ready-made scene presets (季度汇报, 学术答辩, …).

Full technical schemas and commands: [`enhancements/README.md`](enhancements/README.md).

---

## Overview

| Phase | Focus | Status |
|-------|--------|--------|
| 0 | Config scaffolding (`user_preferences.json`, `semantic_template_map.json`) | ✅ Shipped |
| 1 | Smart defaults — pre-fill & save Eight Confirmations | ✅ Shipped |
| 2 | Semantic template matching (natural language → layout) | ✅ Shipped |
| 3 | Scene presets library (6 scenarios, exact keyword) | ✅ Shipped |
| 4 | SVG auto debug fix at quality gate | ✅ Shipped |
| 5 | Chart dual-mode export (SVG vs native Excel/PPT charts) | ✅ Shipped |
| 6 | CI/CD + this changelog | ✅ Shipped |

---

## Quick Start (new users)

1. **Use the normal pipeline** — Follow [`SKILL.md`](SKILL.md) (create project → Strategist → Executor → export). Enhancements plug in automatically at the steps below when scripts are run as documented there.

2. **Save your style once** — After you confirm the Eight Confirmations, preferences are stored in `enhancements/user_preferences.json` for the next deck.

3. **Name your scene** — Say 季度汇报, 学术答辩, 产品发布, 融资路演, 培训课件, or 商务洽谈 in your first message to load a full preset (template + confirmations).

4. **Optional: edit JSON** — Tweak `enhancements/user_preferences.json` or `semantic_template_map.json` to adjust defaults or keyword → template mappings. CI validates these files on every change.

5. **Charts in Excel** — When you need editable chart data in PowerPoint, ask for export with `--chart-mode excel` (requires `openpyxl`; see [`requirements.txt`](requirements.txt)).

---

## Phase Summaries

### Phase 0 — Enhancement framework

| | |
|---|---|
| **Commit** | `57013627` |
| **Date** | 2026-05-21 |
| **Problem** | Repeat users re-entered the same canvas, style, and template choices every session. |
| **Key files** | `enhancements/user_preferences.json`, `enhancements/semantic_template_map.json`, `enhancements/README.md` |
| **How to use** | Drop preferences and keyword maps in `enhancements/`; later phases read them per SKILL.md. |

### Phase 1 — Smart defaults

| | |
|---|---|
| **Commit** | `935e9441` |
| **Date** | 2026-05-21 |
| **Problem** | Strategist Eight Confirmations felt repetitive for recurring deck types. |
| **Key files** | `scripts/user_defaults.py`, `enhancements/user_preferences.json` |
| **How to use** | Before confirmations: `user_defaults.py prefill`. After user confirms: `user_defaults.py save`. Wired in SKILL.md Step 4. |

### Phase 2 — Semantic template matching

| | |
|---|---|
| **Commit** | `fe01e720` |
| **Date** | 2026-05-21 |
| **Problem** | Users describe style in natural language but don't know layout template IDs. |
| **Key files** | `scripts/semantic_template_matcher.py`, `enhancements/semantic_template_map.json` |
| **How to use** | `semantic_template_matcher.py match --user-text "…"` before Step 3b; confirm match before copying template. |

### Phase 3 — Scene presets library

| | |
|---|---|
| **Commit** | `0ff1e2d4` |
| **Date** | 2026-05-21 |
| **Problem** | Common scenarios (quarterly report, thesis defense, …) need one-shot bundles. |
| **Key files** | `scripts/scene_preset_loader.py`, `scene_presets` in `semantic_template_map.json` |
| **How to use** | Mention a scene name in your request, or `scene_preset_loader.py list` / `load <scene>`. SKILL.md Step 3c. |

### Phase 4 — SVG auto-fix

| | |
|---|---|
| **Commit** | `73972b8d` |
| **Date** | 2026-05-21 |
| **Problem** | Minor SVG spec drift (viewBox, fonts, overflow) blocked export until manual edits. |
| **Key files** | `scripts/svg_auto_fix.py`, `svg_quality_checker.py --auto-fix` |
| **How to use** | Run quality check with `--auto-fix` in Step 6; up to two repair passes before export. |

### Phase 5 — Chart dual-mode export

| | |
|---|---|
| **Commits** | `b264c6b9`, `7bb1be16` |
| **Date** | 2026-05-21 |
| **Problem** | Decorative SVG charts aren't editable as real chart data in PowerPoint/Excel. |
| **Key files** | `scripts/svg_to_excel_chart.py`, `svg_to_pptx.py --chart-mode`, `svg_quality_checker.py --chart-mode` |
| **How to use** | Step 6: `--chart-mode excel` (or `hybrid`). Step 7.3: same flag on `svg_to_pptx.py`. Install `openpyxl` for excel/hybrid modes. |

### Phase 6 — CI/CD & documentation

| | |
|---|---|
| **Commit** | `feat(phase6): add CI/CD workflow and ENHANCEMENTS.md documentation` |
| **Date** | 2026-05-21 |
| **Problem** | Enhancement JSON and scripts had no automated guardrails or single user-facing changelog. |
| **Key files** | `.github/workflows/ci.yml`, `ENHANCEMENTS.md`, `.flake8`, `.cursor/rules/enhancement-workflow.md` |
| **How to use** | Push or open a PR to `main`; CI runs lint, smoke tests, and JSON validation. Contributors: see [`enhancements/README.md`](enhancements/README.md) Phase 6 section. |

---

## Migration notes

- **No breaking changes to the core pipeline** — Omitting enhancement flags keeps the original SKILL.md behavior (free design, SVG charts, manual quality fixes).
- **`--chart-mode`** — Default remains `svg` (decorative chart shapes). `excel` and `hybrid` need `openpyxl` and extractable numeric labels on chart pages.
- **`--auto-fix`** — Opt-in via `svg_quality_checker.py --auto-fix`; irreversible hard errors (forbidden tags, missing assets) still need human or regenerate.
- **Template / brand gates unchanged** — Semantic match and scene presets still require SKILL.md confirmation; bare template names never auto-apply.
- **JSON schema** — Bump `version` in preference files if you change field meaning; CI only checks valid JSON syntax, not business rules.

---

## Where to go next

- **Daily workflow:** [`SKILL.md`](SKILL.md)
- **Schemas & commands:** [`enhancements/README.md`](enhancements/README.md)
- **Report issues:** GitHub Issues on the ppt-master repository
