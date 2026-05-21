#!/usr/bin/env python3
"""
PPT Master - Scene Preset Loader

Load complete scene presets (Eight Confirmations + layout template) from
enhancements/semantic_template_map.json by exact keyword match.

Usage:
    python3 scripts/scene_preset_loader.py list
    python3 scripts/scene_preset_loader.py load SCENE_NAME
    python3 scripts/scene_preset_loader.py detect --user-text TEXT

Examples:
    python3 scripts/scene_preset_loader.py load 季度汇报
    python3 scripts/scene_preset_loader.py detect --user-text "用融资路演场景做BP"

Dependencies:
    None (only uses standard library)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
	sys.path.insert(0, str(_SCRIPTS_DIR))

from user_defaults import defaults_to_eight_confirmations
SKILL_DIR = _SCRIPTS_DIR.parent
SEMANTIC_MAP_PATH = SKILL_DIR / "enhancements" / "semantic_template_map.json"
LAYOUTS_DIR = SKILL_DIR / "templates" / "layouts"

# User-facing scene names (exact keyword triggers for Step 3c / SKILL.md).
SCENE_PRESET_NAMES: tuple[str, ...] = (
	"季度汇报",
	"学术答辩",
	"产品发布",
	"融资路演",
	"培训课件",
	"商务洽谈",
)

# Exact keywords in user text → scene preset key (longer phrases first).
SCENE_TRIGGER_KEYWORDS: tuple[tuple[str, str], ...] = (
	("融资路演", "融资路演"),
	("学术答辩", "学术答辩"),
	("产品发布", "产品发布"),
	("季度汇报", "季度汇报"),
	("商务洽谈", "商务洽谈"),
	("培训", "培训课件"),
)


def _semantic_map_path(path: Path | None = None) -> Path:
	return path if path is not None else SEMANTIC_MAP_PATH


def load_semantic_map(path: Path | None = None) -> dict[str, Any]:
	"""Load semantic template map JSON."""
	map_path = _semantic_map_path(path)
	if not map_path.is_file():
		raise FileNotFoundError(f"Semantic map not found: {map_path}")
	with map_path.open(encoding="utf-8") as fh:
		data = json.load(fh)
	if not isinstance(data, dict):
		raise ValueError(f"Invalid semantic map (expected object): {map_path}")
	return data


def list_available_scenes() -> list[str]:
	"""Return user-facing scene preset names."""
	return list(SCENE_PRESET_NAMES)


def layout_template_exists(template_id: str) -> bool:
	"""True when templates/layouts/<template_id>/ exists."""
	if not template_id:
		return False
	layout_dir = LAYOUTS_DIR / template_id
	return layout_dir.is_dir() and (layout_dir / "design_spec.md").is_file()


def validate_preset_layout_templates(preset: dict[str, Any]) -> list[str]:
	"""Return list of missing layout_template IDs referenced by the preset."""
	missing: list[str] = []
	primary = preset.get("layout_template")
	if isinstance(primary, str) and not layout_template_exists(primary):
		missing.append(primary)
	alt = preset.get("layout_template_alt")
	if isinstance(alt, str) and not layout_template_exists(alt):
		missing.append(alt)
	return missing


def load_scene_preset(scene_name: str, *, map_path: Path | None = None) -> dict[str, Any]:
	"""Load a complete scene preset by name; raises KeyError if unknown."""
	if not scene_name:
		raise KeyError("Scene name is required")
	data = load_semantic_map(map_path)
	scene_presets = data.get("scene_presets") or {}
	if not isinstance(scene_presets, dict):
		raise KeyError(f"Scene preset not found: {scene_name}")
	preset = scene_presets.get(scene_name)
	if not isinstance(preset, dict):
		raise KeyError(f"Scene preset not found: {scene_name}")
	missing = validate_preset_layout_templates(preset)
	if missing:
		raise ValueError(
			f"Scene preset '{scene_name}' references missing layout templates: {', '.join(missing)}"
		)
	return dict(preset)


def detect_scene_from_text(user_text: str) -> str | None:
	"""Exact keyword match; first hit wins. Returns scene preset key or None."""
	if not user_text:
		return None
	for keyword, scene_key in SCENE_TRIGGER_KEYWORDS:
		if keyword in user_text:
			return scene_key
	return None


def template_dir_for_preset(preset: dict[str, Any]) -> Path | None:
	"""Resolve primary layout template directory from a preset."""
	template_id = preset.get("layout_template")
	if not isinstance(template_id, str) or not layout_template_exists(template_id):
		return None
	return LAYOUTS_DIR / template_id


def preset_to_prefill(preset: dict[str, Any]) -> dict[str, Any]:
	"""Map scene preset fields to Strategist Eight Confirmation prefill keys."""
	return defaults_to_eight_confirmations(preset)


def load_result_payload(scene_name: str, *, map_path: Path | None = None) -> dict[str, Any]:
	"""Build JSON-serializable load result for CLI and agent consumption."""
	preset = load_scene_preset(scene_name, map_path=map_path)
	template_id = preset.get("layout_template")
	template_dir = template_dir_for_preset(preset)
	prefill = preset_to_prefill(preset)
	return {
		"scene": scene_name,
		"preset": preset,
		"prefill": prefill,
		"layout_template": template_id,
		"layout_template_dir": str(template_dir) if template_dir else None,
		"provenance_line": f"Using defaults from: scene:{scene_name}",
	}


def detect_result_payload(user_text: str, *, map_path: Path | None = None) -> dict[str, Any]:
	"""Detect scene from text and return full load payload when matched."""
	scene = detect_scene_from_text(user_text)
	if not scene:
		return {"matched": False, "scene": None}
	try:
		payload = load_result_payload(scene, map_path=map_path)
	except (KeyError, ValueError) as exc:
		return {"matched": False, "scene": scene, "error": str(exc)}
	payload["matched"] = True
	return payload


def cmd_list(_args: argparse.Namespace) -> int:
	print(json.dumps({"scenes": list_available_scenes()}, ensure_ascii=False, indent=2))
	return 0


def cmd_load(args: argparse.Namespace) -> int:
	try:
		payload = load_result_payload(args.scene_name, map_path=args.map_file)
	except KeyError as exc:
		print(str(exc), file=sys.stderr)
		return 1
	except ValueError as exc:
		print(str(exc), file=sys.stderr)
		return 1
	print(json.dumps(payload, ensure_ascii=False, indent=2))
	return 0


def cmd_detect(args: argparse.Namespace) -> int:
	payload = detect_result_payload(args.user_text or "", map_path=args.map_file)
	print(json.dumps(payload, ensure_ascii=False, indent=2))
	return 0


def build_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(
		description="Load scene presets with complete Eight Confirmation bundles.",
		formatter_class=argparse.RawDescriptionHelpFormatter,
	)
	sub = parser.add_subparsers(dest="command", required=True)

	list_cmd = sub.add_parser("list", help="List available user-facing scene names")
	list_cmd.set_defaults(func=cmd_list)

	load_cmd = sub.add_parser("load", help="Load a scene preset by name")
	load_cmd.add_argument("scene_name", help="Scene preset key, e.g. 季度汇报")
	load_cmd.add_argument(
		"--map-file",
		type=Path,
		default=None,
		help="Override path to semantic_template_map.json",
	)
	load_cmd.set_defaults(func=cmd_load)

	detect_cmd = sub.add_parser("detect", help="Detect scene from user text (exact keywords)")
	detect_cmd.add_argument("--user-text", default="", help="User's initial request")
	detect_cmd.add_argument(
		"--map-file",
		type=Path,
		default=None,
		help="Override path to semantic_template_map.json",
	)
	detect_cmd.set_defaults(func=cmd_detect)

	return parser


def main(argv: list[str] | None = None) -> int:
	parser = build_parser()
	args = parser.parse_args(argv)
	return int(args.func(args))


if __name__ == "__main__":
	raise SystemExit(main())
