#!/usr/bin/env python3
"""
PPT Master - Semantic Template Matcher

Match natural-language style descriptions to layout templates using
enhancements/semantic_template_map.json keyword mappings.

Usage:
    python3 scripts/semantic_template_matcher.py match --user-text TEXT [--content-file PATH]

Examples:
    python3 scripts/semantic_template_matcher.py match --user-text "毕业答辩PPT" --content-file projects/foo/sources/thesis.md

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
SKILL_DIR = _SCRIPTS_DIR.parent
SEMANTIC_MAP_PATH = SKILL_DIR / "enhancements" / "semantic_template_map.json"
LAYOUTS_INDEX_PATH = SKILL_DIR / "templates" / "layouts" / "layouts_index.json"
DEFAULT_THRESHOLD = 0.6


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


def load_layouts_index(path: Path | None = None) -> dict[str, Any]:
	"""Load layouts index for template validation and display names."""
	index_path = path if path is not None else LAYOUTS_INDEX_PATH
	if not index_path.is_file():
		return {}
	with index_path.open(encoding="utf-8") as fh:
		data = json.load(fh)
	return data if isinstance(data, dict) else {}


def _build_template_keyword_index(keywords_to_template: dict[str, str]) -> dict[str, list[str]]:
	index: dict[str, list[str]] = {}
	for keyword, template_id in keywords_to_template.items():
		if not keyword or not template_id:
			continue
		index.setdefault(template_id, []).append(keyword)
	return index


def _keyword_in_text(keyword: str, lowered_text: str) -> bool:
	if not keyword:
		return False
	return keyword.lower() in lowered_text


def match_template(
	user_text: str = "",
	project_content: str = "",
	*,
	threshold: float = DEFAULT_THRESHOLD,
	map_path: Path | None = None,
) -> tuple[str | None, float, list[str]]:
	"""Match user text and project content to a layout template.

	Returns:
		(template_id, confidence, matched_keywords)
		template_id is None when confidence is below threshold.
	"""
	combined = f"{user_text or ''}\n{project_content or ''}".strip()
	if not combined:
		return None, 0.0, []

	data = load_semantic_map(map_path)
	keywords_to_template = data.get("keywords_to_template") or {}
	if not isinstance(keywords_to_template, dict):
		return None, 0.0, []

	template_keywords = _build_template_keyword_index(keywords_to_template)
	lowered = combined.lower()

	matched_by_template: dict[str, list[str]] = {}
	for keyword, template_id in keywords_to_template.items():
		if not isinstance(keyword, str) or not isinstance(template_id, str):
			continue
		if _keyword_in_text(keyword, lowered):
			matched_by_template.setdefault(template_id, []).append(keyword)

	best_id: str | None = None
	best_conf = 0.0
	best_keywords: list[str] = []

	for template_id, matched in matched_by_template.items():
		total = len(template_keywords.get(template_id, []))
		if total == 0:
			continue
		confidence = len(matched) / total
		if confidence > best_conf or (confidence == best_conf and len(matched) > len(best_keywords)):
			best_conf = confidence
			best_id = template_id
			best_keywords = sorted(set(matched))

	if best_conf >= threshold and best_id:
		return best_id, best_conf, best_keywords
	return None, best_conf, best_keywords


def template_dir_for_id(template_id: str) -> Path:
	"""Resolve built-in layout template directory from template ID."""
	return SKILL_DIR / "templates" / "layouts" / template_id


def match_result_payload(
	user_text: str = "",
	project_content: str = "",
	*,
	threshold: float = DEFAULT_THRESHOLD,
	map_path: Path | None = None,
) -> dict[str, Any]:
	"""Build JSON-serializable match result for CLI and agent consumption."""
	template_id, confidence, matched_keywords = match_template(
		user_text,
		project_content,
		threshold=threshold,
		map_path=map_path,
	)
	layouts_index = load_layouts_index()
	summary = ""
	if template_id and template_id in layouts_index:
		entry = layouts_index[template_id]
		if isinstance(entry, dict):
			summary = str(entry.get("summary") or "")

	template_dir = template_dir_for_id(template_id) if template_id else None
	return {
		"template_id": template_id,
		"confidence": round(confidence, 4),
		"matched_keywords": matched_keywords,
		"threshold": threshold,
		"matched": template_id is not None,
		"template_summary": summary,
		"template_dir": str(template_dir) if template_dir else None,
	}


def cmd_match(args: argparse.Namespace) -> int:
	content = ""
	if args.content_file:
		if not args.content_file.is_file():
			print(f"Content file not found: {args.content_file}", file=sys.stderr)
			return 1
		content = args.content_file.read_text(encoding="utf-8")

	payload = match_result_payload(
		args.user_text or "",
		content,
		threshold=args.threshold,
		map_path=args.map_file,
	)
	print(json.dumps(payload, ensure_ascii=False, indent=2))
	return 0


def build_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(
		description="Match natural-language descriptions to layout templates.",
		formatter_class=argparse.RawDescriptionHelpFormatter,
	)
	sub = parser.add_subparsers(dest="command", required=True)

	match_cmd = sub.add_parser("match", help="Match user text (+ optional content) to a template")
	match_cmd.add_argument("--user-text", default="", help="User's initial request or style description")
	match_cmd.add_argument("--content-file", type=Path, default=None, help="Project source markdown path")
	match_cmd.add_argument(
		"--threshold",
		type=float,
		default=DEFAULT_THRESHOLD,
		help=f"Minimum confidence to accept a match (default {DEFAULT_THRESHOLD})",
	)
	match_cmd.add_argument(
		"--map-file",
		type=Path,
		default=None,
		help="Override path to semantic_template_map.json",
	)
	match_cmd.set_defaults(func=cmd_match)

	return parser


def main(argv: list[str] | None = None) -> int:
	parser = build_parser()
	args = parser.parse_args(argv)
	return int(args.func(args))


if __name__ == "__main__":
	raise SystemExit(main())
