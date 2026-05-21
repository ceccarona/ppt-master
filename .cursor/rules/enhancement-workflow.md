# PPT Master enhancement workflow

When the user wants to **make a PPT**, **generate a deck**, or **continue a project** under `skills/ppt-master/` or `projects/`:

## Before Strategist (Steps 3–4)

1. **Scene preset (Step 3c)** — If the user names a known scene (季度汇报, 学术答辩, 产品发布, 融资路演, 培训课件, 商务洽谈), run `scene_preset_loader.py detect` / `load` first. Scene preset prefill overrides `user_defaults.py` for that session.
2. **Semantic template (Step 3b)** — If no explicit template path and no scene preset matched, run `semantic_template_matcher.py match` on user text + source content. Present match and wait for confirmation before copying a layout template.
3. **Smart defaults (Step 4)** — Unless Step 3c already supplied prefill, run `user_defaults.py prefill` from source markdown or user description. After Eight Confirmations are confirmed, run `user_defaults.py save`.

## During quality check & export (Steps 6–7)

4. **SVG auto-fix** — Use `svg_quality_checker.py <project> --auto-fix` when quality issues are likely fixable (viewBox, fonts, overflow).
5. **Charts** — If the user wants **editable chart data** in PowerPoint, use `--chart-mode excel` or `hybrid` on both quality check (Step 6) and `svg_to_pptx.py` (Step 7.3). Verify `openpyxl` is installed.

## Configuration

- Read/write: `skills/ppt-master/enhancements/user_preferences.json`, `semantic_template_map.json`
- User-facing changelog: `skills/ppt-master/ENHANCEMENTS.md`
- **SKILL.md always wins** over enhancement defaults on conflicts or explicit user choices.

## Do not

- Auto-apply layout templates without Step 3a path or Step 3b/3c confirmation gates.
- Create `animations.json` unless the user asked for custom object-level animations.
- Run `visual-review` unless the user explicitly requested per-page visual self-check.
