# PPT Master Enhancement Framework

Optional, layered improvements that sit **alongside** the main pipeline in [`../SKILL.md`](../SKILL.md). Enhancements never replace or override SKILL.md execution discipline — they supply defaults, mappings, and preferences that downstream phases (and the Strategist) may read when explicitly wired in.

## Purpose

The core pipeline is fixed and serial:

`Source Document → Create Project → [Template] → Strategist → [Image_Generator] → Executor → Quality Check → Post-processing → Export`

Enhancements add **persistent, reusable configuration** so repeat users and scene-specific workflows do not re-enter the same choices every session. Examples:

- Remember default canvas, style, color scheme, and font across projects
- Map user keywords or scene names (e.g. 季度汇报, 学术答辩) to layout templates and preset bundles
- Apply scene-level defaults before Strategist Eight Confirmations

## Directory Layout

| File | Role |
|------|------|
| [`user_preferences.json`](./user_preferences.json) | User-wide defaults and per-scene overrides |
| [`semantic_template_map.json`](./semantic_template_map.json) | Keyword → template ID mapping and full scene presets |
| `README.md` | This document — framework contract and schema reference |

Future enhancement phases may add scripts, workflow hooks, or additional JSON registries under this directory. Each phase should extend this README with integration points and gate conditions.

## Integration Rules

1. **SKILL.md wins** — If an enhancement conflicts with a BLOCKING gate or explicit user choice in the current session, the pipeline follows SKILL.md.
2. **Explicit paths only** — Template and brand application still require explicit paths (see SKILL.md Step 3). Semantic maps produce *recommendations*; they do not auto-apply bare template names.
3. **Opt-in consumption** — Phases that read these files must document which keys they consume and at which pipeline step.
4. **Valid JSON** — All `*.json` files must parse with standard `json.load`. Field semantics and examples live in this README and in `_schema_notes` keys inside each file.

## Schemas

### `user_preferences.json`

User-level defaults persisted across projects.

| Field | Type | Description |
|-------|------|-------------|
| `version` | string | Schema version (currently `"1.0"`) |
| `last_updated` | string \| null | ISO-8601 timestamp of last edit, or `null` if never set |
| `default_canvas` | string | Canvas format ID (e.g. `ppt169`) — see [`../references/canvas-formats.md`](../references/canvas-formats.md) |
| `default_style` | string \| null | Preferred visual style label or template family |
| `default_color_scheme` | string \| null | Preferred palette or brand color preset reference |
| `default_font` | string \| null | Preferred primary font family |
| `page_count_range` | string \| null | Recommended page band for confirmation **b** |
| `target_audience` | string \| null | Confirmation **c** — audience |
| `use_case` | string \| null | Confirmation **c** — occasion |
| `core_message` | string \| null | Confirmation **c** — core message |
| `style_mode` | string \| null | Confirmation **d** layer 1 (`A/B/C` labels per strategist.md) |
| `style_descriptor` | string \| null | Confirmation **d** layer 2 — visual descriptor |
| `color_scheme` | object \| null | Confirmation **e** — HEX roles (`primary`, `secondary`, `accent`, `background`, `text`) |
| `icon_approach` | string \| null | Confirmation **f** — A/B/C/D option label |
| `icon_library` | string \| null | Confirmation **f** detail when approach is built-in library |
| `typography_plan` | object \| null | Confirmation **g** — `title_stack`, `body_stack`, `body_baseline_px` |
| `image_approach` | string \| null | Confirmation **h** — image strategy label or mixed description |
| `scene_defaults` | object | Keyed by scene name (e.g. `"季度汇报"`, `"学术答辩"`). Each value is a partial preference object with the same keys as the top level |

Example `scene_defaults` entry (abbreviated):

```json
"学术答辩": {
  "default_canvas": "ppt169",
  "style_mode": "A) General Versatile",
  "style_descriptor": "academic defense, clean minimal",
  "typography_plan": {
    "title_stack": "Cambria, SimSun, serif",
    "body_stack": "\"Microsoft YaHei\", \"PingFang SC\", sans-serif",
    "body_baseline_px": 24
  }
}
```

### `semantic_template_map.json`

Keyword and scene-level routing to layout templates. Template IDs must exist in [`../templates/layouts/layouts_index.json`](../templates/layouts/layouts_index.json).

| Field | Type | Description |
|-------|------|-------------|
| `version` | string | Schema version (currently `"1.0"`) |
| `keywords_to_template` | object | Maps keyword substring or tag → layout template ID (e.g. `"学术"` → `"academic_defense"`, `"招商"` → `"china_telecom_template"`) |
| `scene_presets` | object | Full scene configurations: canvas, template, brand path, style hints, and other fields consumed by future enhancement phases |

Example entries:

```json
"keywords_to_template": {
  "学术": "academic_defense",
  "招商": "china_telecom_template"
},
"scene_presets": {
  "季度汇报": {
    "canvas": "ppt169",
    "layout_template": "general_business",
    "notes": "Dense data slides; prefer chart templates"
  }
}
```

## Phase 1 — Smart Defaults System

**Status:** Active  
**Consumption:** SKILL.md **Step 4** (Strategist), before the Eight Confirmations ⛔ BLOCKING presentation.

### Behavior

1. **Load** — `user_defaults.py` reads `enhancements/user_preferences.json` via `load_preferences()`.
2. **Infer scene** — `infer_scene_from_content()` scans source markdown or the user's description for keywords (e.g. 季度汇报, 学术, 答辩, 产品发布, 融资, 培训). First match wins; no match → global defaults only.
3. **Merge** — `get_scene_defaults(scene)` overlays scene keys on global keys when a scene matches and has entries in `scene_defaults`.
4. **Pre-fill** — Strategist presents confirmations a–h using `prefill` output; `null` slots still get Strategist recommendations from source analysis.
5. **Provenance** — Every confirmation bundle includes: `Using defaults from: global` or `Using defaults from: scene:<name>`.
6. **Auto-save** — After the user **confirms** the eight items, run `user_defaults.py save` so the next deck remembers. Scene-specific saves go under `scene_defaults.<scene>`; omit `--scene` to update global top-level fields.

### Commands

```bash
# Before Eight Confirmations (prefill JSON on stdout)
python3 skills/ppt-master/scripts/user_defaults.py prefill \
  --content-file projects/<name>/sources/<main>.md

# After user confirms
python3 skills/ppt-master/scripts/user_defaults.py save \
  --scene 季度汇报 \
  --from-json '{"default_canvas":"ppt169","page_count_range":"15-20",...}'
```

### Example `user_preferences.json`

See the committed file [`user_preferences.json`](./user_preferences.json). It includes `_schema_notes` (field semantics, valid JSON only) and a full sample `scene_defaults["季度汇报"]` with all eight confirmation fields populated.

## Phase Roadmap

| Phase | Focus | Status |
|-------|-------|--------|
| 0 | Directory scaffolding and schema files | Active |
| 1 | Smart defaults loader + Strategist pre-fill + auto-save | Active |
| 2+ | Semantic template routing, preference UI | Planned |

When implementing later phases, update the table above and add a **Consumption** subsection describing which SKILL.md step reads which file.

## Editing Guidelines

- Bump `version` when breaking schema changes occur
- Set `last_updated` in `user_preferences.json` when modifying user defaults
- Keep `keywords_to_template` keys short and high-signal; prefer scene names in `scene_presets` for full bundles
- Do not store secrets or API keys in these files
