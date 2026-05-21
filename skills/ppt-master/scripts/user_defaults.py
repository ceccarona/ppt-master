#!/usr/bin/env python3
"""
PPT Master - User Preferences & Smart Defaults

Loads and persists Strategist Eight Confirmation defaults from
enhancements/user_preferences.json. Supports global defaults, per-scene
overrides, and keyword-based scene inference from source content.

Usage:
    python3 scripts/user_defaults.py prefill [--content-file PATH] [--content-text TEXT]
    python3 scripts/user_defaults.py save --from-json JSON [--scene SCENE_NAME]
    python3 scripts/user_defaults.py infer [--content-file PATH] [--content-text TEXT]

Examples:
    python3 scripts/user_defaults.py prefill --content-file projects/foo/sources/report.md
    python3 scripts/user_defaults.py save --scene 季度汇报 --from-json '{"canvas":"ppt169",...}'

Dependencies:
    None (only uses standard library)
"""

from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = Path(__file__).resolve().parent
SKILL_DIR = _SCRIPTS_DIR.parent
PREFERENCES_PATH = SKILL_DIR / "enhancements" / "user_preferences.json"

# Keys persisted at top level or inside scene_defaults (excluding metadata).
PREFERENCE_KEYS = (
	"default_canvas",
	"page_count_range",
	"target_audience",
	"use_case",
	"core_message",
	"style_mode",
	"style_descriptor",
	"default_style",
	"color_scheme",
	"default_color_scheme",
	"icon_approach",
	"icon_library",
	"typography_plan",
	"default_font",
	"image_approach",
)

# Scene inference: ordered by specificity; first match wins.
SCENE_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
	("季度汇报", ("季度汇报", "季报", "季度报告", "quarterly report", "quarterly")),
	("学术答辩", ("学术答辩", "毕业答辩", "论文答辩", "学位答辩", "thesis defense")),
	("学术", ("学术论文", "学术报告", "学术演讲", "academic paper", "academic")),
	("产品发布", ("产品发布", "发布会", "新品发布", "product launch", "launch event")),
	("融资", ("融资路演", "商业计划书", "投资人", "pitch deck", "fundraising", "bp")),
	("培训", ("培训课程", "内训", "讲师", "workshop", "training", "培训")),
]

METADATA_KEYS = frozenset({"version", "last_updated", "scene_defaults", "_schema_notes"})


def _preferences_path(path: Path | None = None) -> Path:
	return path if path is not None else PREFERENCES_PATH


def _empty_preferences() -> dict[str, Any]:
	return {
		"version": "1.0",
		"last_updated": None,
		"default_canvas": "ppt169",
		"default_style": None,
		"default_color_scheme": None,
		"default_font": None,
		"scene_defaults": {},
		"_schema_notes": {},
	}


def _read_text(path: Path | None, text: str | None) -> str:
	if text:
		return text
	if path and path.is_file():
		return path.read_text(encoding="utf-8")
	return ""


def _extract_global_defaults(prefs: dict[str, Any]) -> dict[str, Any]:
	out: dict[str, Any] = {}
	for key in PREFERENCE_KEYS:
		if key in prefs and prefs[key] is not None:
			out[key] = deepcopy(prefs[key])
	# Legacy alias: default_style may mirror style_descriptor when only one is set.
	if out.get("style_descriptor") and not out.get("default_style"):
		out["default_style"] = out["style_descriptor"]
	if out.get("default_style") and not out.get("style_descriptor"):
		out["style_descriptor"] = out["default_style"]
	return out


def load_preferences(path: Path | None = None) -> dict[str, Any]:
	"""Load user preferences JSON; create scaffold if missing."""
	pref_path = _preferences_path(path)
	if not pref_path.is_file():
		return _empty_preferences()
	with pref_path.open(encoding="utf-8") as fh:
		data = json.load(fh)
	if not isinstance(data, dict):
		raise ValueError(f"Invalid preferences file (expected object): {pref_path}")
	data.setdefault("scene_defaults", {})
	return data


def save_preferences(prefs: dict[str, Any], path: Path | None = None) -> Path:
	"""Persist preferences and stamp last_updated (ISO-8601 UTC)."""
	pref_path = _preferences_path(path)
	pref_path.parent.mkdir(parents=True, exist_ok=True)
	prefs = deepcopy(prefs)
	prefs["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
	with pref_path.open("w", encoding="utf-8") as fh:
		json.dump(prefs, fh, ensure_ascii=False, indent=2)
		fh.write("\n")
	return pref_path


def get_scene_defaults(scene_name: str, path: Path | None = None) -> dict[str, Any]:
	"""Return scene-specific overrides, or empty dict if unknown."""
	if not scene_name:
		return {}
	prefs = load_preferences(path)
	scene_defaults = prefs.get("scene_defaults") or {}
	raw = scene_defaults.get(scene_name)
	if not isinstance(raw, dict):
		return {}
	return {k: deepcopy(v) for k, v in raw.items() if k in PREFERENCE_KEYS and v is not None}


def infer_scene_from_content(content_text: str) -> str | None:
	"""Infer scene name from keywords in content; None if no match."""
	if not content_text or not content_text.strip():
		return None
	lowered = content_text.lower()
	for scene_name, keywords in SCENE_KEYWORDS:
		for kw in keywords:
			if kw.lower() in lowered:
				return scene_name
	return None


def merge_defaults(
	global_defaults: dict[str, Any],
	scene_defaults: dict[str, Any],
) -> dict[str, Any]:
	"""Overlay scene on global; scene keys win."""
	merged = deepcopy(global_defaults)
	for key, value in scene_defaults.items():
		if value is not None:
			merged[key] = deepcopy(value)
	return merged


def get_effective_defaults(
	content_text: str = "",
	*,
	path: Path | None = None,
) -> tuple[dict[str, Any], str]:
	"""Return merged defaults and source label (global | scene:<name>)."""
	prefs = load_preferences(path)
	global_defaults = _extract_global_defaults(prefs)
	scene = infer_scene_from_content(content_text)
	if scene:
		scene_defaults = get_scene_defaults(scene, path)
		if scene_defaults:
			return merge_defaults(global_defaults, scene_defaults), f"scene:{scene}"
	return global_defaults, "global"


def defaults_to_eight_confirmations(defaults: dict[str, Any]) -> dict[str, Any]:
	"""Map preference keys to Strategist Eight Confirmation slots a–h."""
	canvas = defaults.get("default_canvas") or defaults.get("canvas") or "ppt169"
	style_mode = defaults.get("style_mode") or ""
	style_descriptor = (
		defaults.get("style_descriptor")
		or defaults.get("default_style")
		or ""
	)
	style_line = ""
	if style_mode and style_descriptor:
		style_line = f"{style_mode} + {style_descriptor}"
	elif style_descriptor:
		style_line = style_descriptor
	elif style_mode:
		style_line = style_mode

	color = defaults.get("color_scheme") or defaults.get("default_color_scheme")
	typography = defaults.get("typography_plan")
	if isinstance(typography, str):
		typography = {"summary": typography}
	elif typography is None and defaults.get("default_font"):
		typography = {"body_stack": defaults.get("default_font")}

	return {
		"a_canvas": canvas,
		"b_page_count_range": defaults.get("page_count_range"),
		"c_target_audience": defaults.get("target_audience"),
		"c_use_case": defaults.get("use_case"),
		"c_core_message": defaults.get("core_message"),
		"d_style": style_line or None,
		"d_style_mode": style_mode or None,
		"d_style_descriptor": style_descriptor or None,
		"e_color_scheme": color,
		"f_icon_approach": defaults.get("icon_approach"),
		"f_icon_library": defaults.get("icon_library"),
		"g_typography_plan": typography,
		"h_image_approach": defaults.get("image_approach"),
	}


def save_after_confirmation(
	confirmed: dict[str, Any],
	scene_name: str | None = None,
	*,
	path: Path | None = None,
) -> Path:
	"""Auto-save confirmed Eight Confirmation values after user approval."""
	prefs = load_preferences(path)
	payload: dict[str, Any] = {}
	for key in PREFERENCE_KEYS:
		if key in confirmed and confirmed[key] is not None:
			payload[key] = confirmed[key]

	# Accept confirmation-shaped keys from CLI / agent.
	aliases = {
		"canvas": "default_canvas",
		"page_count_range": "page_count_range",
		"target_audience": "target_audience",
		"use_case": "use_case",
		"core_message": "core_message",
		"style_mode": "style_mode",
		"style_descriptor": "style_descriptor",
		"color_scheme": "color_scheme",
		"icon_approach": "icon_approach",
		"icon_library": "icon_library",
		"typography_plan": "typography_plan",
		"image_approach": "image_approach",
	}
	for src, dest in aliases.items():
		if src in confirmed and confirmed[src] is not None:
			payload[dest] = confirmed[src]
	if confirmed.get("d_style") and not payload.get("style_descriptor"):
		payload["style_descriptor"] = confirmed["d_style"]
	if confirmed.get("e_color_scheme") and not payload.get("color_scheme"):
		payload["color_scheme"] = confirmed["e_color_scheme"]

	if not payload:
		return save_preferences(prefs, path)

	if scene_name:
		scene_defaults = prefs.setdefault("scene_defaults", {})
		existing = scene_defaults.get(scene_name) or {}
		if not isinstance(existing, dict):
			existing = {}
		existing.update(payload)
		scene_defaults[scene_name] = existing
	else:
		for key, value in payload.items():
			prefs[key] = value

	return save_preferences(prefs, path)


def cmd_prefill(args: argparse.Namespace) -> int:
	content = _read_text(args.content_file, args.content_text)
	defaults, source = get_effective_defaults(content)
	prefill = defaults_to_eight_confirmations(defaults)
	out = {
		"source": source,
		"scene": infer_scene_from_content(content),
		"defaults": defaults,
		"prefill": prefill,
		"provenance_line": f"Using defaults from: {source}",
	}
	print(json.dumps(out, ensure_ascii=False, indent=2))
	return 0


def cmd_infer(args: argparse.Namespace) -> int:
	content = _read_text(args.content_file, args.content_text)
	scene = infer_scene_from_content(content)
	print(json.dumps({"scene": scene}, ensure_ascii=False))
	return 0


def cmd_save(args: argparse.Namespace) -> int:
	try:
		confirmed = json.loads(args.from_json)
	except json.JSONDecodeError as exc:
		print(f"Invalid --from-json: {exc}", file=sys.stderr)
		return 1
	if not isinstance(confirmed, dict):
		print("--from-json must be a JSON object", file=sys.stderr)
		return 1
	path = save_after_confirmation(confirmed, args.scene or None)
	print(json.dumps({"saved": str(path), "scene": args.scene}, ensure_ascii=False))
	return 0


def build_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(
		description="Load/save Strategist Eight Confirmation smart defaults.",
		formatter_class=argparse.RawDescriptionHelpFormatter,
	)
	sub = parser.add_subparsers(dest="command", required=True)

	prefill = sub.add_parser("prefill", help="Merge defaults and emit Eight Confirmation prefill JSON")
	prefill.add_argument("--content-file", type=Path, default=None, help="Source markdown/text path")
	prefill.add_argument("--content-text", default=None, help="Inline content for scene inference")
	prefill.set_defaults(func=cmd_prefill)

	infer_cmd = sub.add_parser("infer", help="Infer scene name from content keywords")
	infer_cmd.add_argument("--content-file", type=Path, default=None)
	infer_cmd.add_argument("--content-text", default=None)
	infer_cmd.set_defaults(func=cmd_infer)

	save_cmd = sub.add_parser("save", help="Persist confirmed values after Eight Confirmations")
	save_cmd.add_argument("--from-json", required=True, help="JSON object of confirmed fields")
	save_cmd.add_argument("--scene", default=None, help="Scene name to update scene_defaults")
	save_cmd.set_defaults(func=cmd_save)

	return parser


def main(argv: list[str] | None = None) -> int:
	parser = build_parser()
	args = parser.parse_args(argv)
	return int(args.func(args))


if __name__ == "__main__":
	raise SystemExit(main())
