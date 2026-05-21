#!/usr/bin/env python3
"""
PPT Master - SVG Auto-Fix Tool

Conservatively repairs common SVG quality issues detected by svg_quality_checker.py
before finalize_svg.py runs.

Usage:
    python3 scripts/svg_auto_fix.py auto-fix --svg PATH --spec-lock SPEC_LOCK_PATH
    python3 scripts/svg_auto_fix.py auto-fix --svg PATH --spec-lock SPEC_LOCK_PATH --dry-run

Examples:
    python3 scripts/svg_auto_fix.py auto-fix \\
        --svg projects/demo/svg_output/01_cover.svg \\
        --spec-lock projects/demo/spec_lock.md

Dependencies:
    None (standard library only; optional estimate_text_width from svg_to_pptx)
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

try:
    from update_spec import parse_lock as _parse_spec_lock  # noqa: E402
except ImportError:
    _parse_spec_lock = None

try:
    from svg_to_pptx.drawingml_utils import estimate_text_width  # noqa: E402
except ImportError:
    def estimate_text_width(text: str, font_size: float, font_weight: str = '400') -> float:
        """Fallback width estimate when drawingml_utils is unavailable."""
        width = 0.0
        for ch in text:
            if ord(ch) > 0x2E7F:
                width += font_size
            elif ch == ' ':
                width += font_size * 0.3
            else:
                width += font_size * 0.55
        if font_weight in ('bold', '600', '700', '800', '900'):
            width *= 1.05
        return width

SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)

_NUM_RE = re.compile(r"^[\s,]*([+-]?(?:\d+\.?\d*|\d*\.\d+))")
_VISUAL_ATTRS = frozenset({
    "fill", "stroke", "opacity", "fill-opacity", "stroke-opacity",
    "stroke-width", "transform", "filter", "clip-path", "mask",
    "display", "visibility",
})
_POSITION_TAGS = frozenset({"rect", "text", "image", "use", "circle", "ellipse", "line"})


def _local_tag(elem: ET.Element) -> str:
    return elem.tag.split("}", 1)[-1] if "}" in elem.tag else elem.tag


def _parse_float(value: str | None, default: float = 0.0) -> float:
    if not value:
        return default
    m = _NUM_RE.match(value.strip())
    if not m:
        return default
    try:
        return float(m.group(1))
    except ValueError:
        return default


def _format_num(n: float) -> str:
    if abs(n - round(n)) < 1e-6:
        return str(int(round(n)))
    return f"{n:.4f}".rstrip("0").rstrip(".")


def _resolve_spec_lock(svg_path: Path, spec_lock_path: Path | None) -> Path | None:
    if spec_lock_path is not None:
        return spec_lock_path if spec_lock_path.exists() else None
    for candidate in (svg_path.parent / "spec_lock.md",
                      svg_path.parent.parent / "spec_lock.md"):
        if candidate.exists():
            return candidate
    return None


def _load_lock(spec_lock_path: Path | None) -> dict[str, dict[str, str]]:
    if spec_lock_path is None or _parse_spec_lock is None:
        return {}
    try:
        return _parse_spec_lock(spec_lock_path)
    except OSError:
        return {}


def _canvas_size(lock: dict[str, dict[str, str]]) -> tuple[float, float, str]:
    """Return (width, height, viewbox_string)."""
    canvas = lock.get("canvas", {})
    viewbox = canvas.get("viewBox") or canvas.get("viewbox") or "0 0 1280 720"
    parts = viewbox.split()
    if len(parts) == 4:
        return float(parts[2]), float(parts[3]), viewbox
    return 1280.0, 720.0, viewbox


def _default_font_family(lock: dict[str, dict[str, str]]) -> str:
    typo = lock.get("typography", {})
    return (typo.get("font_family") or '"Microsoft YaHei", Arial, sans-serif').strip()


def _body_font_size(lock: dict[str, dict[str, str]]) -> float:
    typo = lock.get("typography", {})
    raw = typo.get("body", "18")
    try:
        return float(str(raw).replace("px", "").strip())
    except ValueError:
        return 18.0


def _text_content(elem: ET.Element) -> str:
    parts: list[str] = []
    if elem.text:
        parts.append(elem.text)
    for child in elem:
        tag = _local_tag(child)
        if tag == "tspan":
            if child.text:
                parts.append(child.text)
            if child.tail:
                parts.append(child.tail)
        elif child.tail:
            parts.append(child.tail)
    return "".join(parts).strip()


def _has_visual_attrs(elem: ET.Element) -> bool:
    for key in elem.attrib:
        local = key.split("}", 1)[-1]
        if local in _VISUAL_ATTRS:
            return True
    return False


def _is_empty_group(elem: ET.Element) -> bool:
    if _local_tag(elem) != "g":
        return False
    if len(elem) > 0:
        return False
    if elem.get("id"):
        return False
    if _has_visual_attrs(elem):
        return False
    if (elem.text or "").strip() or (elem.tail or "").strip():
        return False
    return True


def _build_parent_map(root: ET.Element) -> dict[ET.Element, ET.Element]:
    parent_map: dict[ET.Element, ET.Element] = {}
    for parent in root.iter():
        for child in parent:
            parent_map[child] = parent
    return parent_map


def _find_text_container(
    text_elem: ET.Element,
    parent_map: dict[ET.Element, ET.Element],
) -> tuple[float, float] | None:
    """Return (left_x, max_width) from a sibling rect in the same parent group."""
    parent = parent_map.get(text_elem)
    if parent is None or _local_tag(parent) != "g":
        return None
    tx = _parse_float(text_elem.get("x"))
    ty = _parse_float(text_elem.get("y"))
    best: tuple[float, float] | None = None
    for sibling in parent:
        if sibling is text_elem or _local_tag(sibling) != "rect":
            continue
        rx = _parse_float(sibling.get("x"))
        ry = _parse_float(sibling.get("y"))
        rw = _parse_float(sibling.get("width"))
        rh = _parse_float(sibling.get("height"))
        if rw <= 0 or rh <= 0:
            continue
        if ry - 4 <= ty <= ry + rh + 4:
            if best is None or abs(rx - tx) < abs(best[0] - tx):
                best = (rx, rw)
    return best


def _text_bounds(
    x: float,
    width: float,
    anchor: str,
) -> tuple[float, float]:
    anchor = (anchor or "start").lower()
    if anchor == "middle":
        return x - width / 2, x + width / 2
    if anchor in ("end", "right"):
        return x - width, x
    return x, x + width


def _fix_viewbox(root: ET.Element, lock: dict, report: dict[str, list[str]]) -> bool:
    cw, ch, viewbox = _canvas_size(lock)
    changed = False
    if root.get("viewBox") != viewbox:
        root.set("viewBox", viewbox)
        report["fixed"].append(f"viewBox set to {viewbox}")
        changed = True
    expected_w = _format_num(cw)
    expected_h = _format_num(ch)
    if root.get("width") != expected_w:
        root.set("width", expected_w)
        report["fixed"].append(f"width set to {expected_w}")
        changed = True
    if root.get("height") != expected_h:
        root.set("height", expected_h)
        report["fixed"].append(f"height set to {expected_h}")
        changed = True
    return changed


def _fix_font_family(root: ET.Element, lock: dict, report: dict[str, list[str]]) -> bool:
    default_font = _default_font_family(lock)
    changed = False
    for elem in root.iter():
        if _local_tag(elem) != "text":
            continue
        if elem.get("font-family"):
            continue
        elem.set("font-family", default_font)
        report["fixed"].append("added missing font-family on <text>")
        changed = True
    return changed


def _remove_empty_groups(root: ET.Element, report: dict[str, list[str]]) -> bool:
    changed = False
    for parent in root.iter():
        for child in list(parent):
            if _is_empty_group(child):
                parent.remove(child)
                report["fixed"].append("removed empty <g>")
                changed = True
    return changed


def _clamp_element(elem: ET.Element, cw: float, ch: float, report: dict[str, list[str]]) -> bool:
    tag = _local_tag(elem)
    changed = False

    if tag == "rect":
        x = _parse_float(elem.get("x"))
        y = _parse_float(elem.get("y"))
        w = _parse_float(elem.get("width"))
        h = _parse_float(elem.get("height"))
        nx, ny, nw, nh = x, y, w, h
        if x < 0:
            nw = max(0.0, w + x)
            nx = 0.0
        if y < 0:
            nh = max(0.0, h + y)
            ny = 0.0
        if nx + nw > cw:
            nw = max(0.0, cw - nx)
        if ny + nh > ch:
            nh = max(0.0, ch - ny)
        if (nx, ny, nw, nh) != (x, y, w, h) and nw > 0 and nh > 0:
            elem.set("x", _format_num(nx))
            elem.set("y", _format_num(ny))
            elem.set("width", _format_num(nw))
            elem.set("height", _format_num(nh))
            report["fixed"].append(f"clamped <rect> to canvas ({_format_num(nx)},{_format_num(ny)})")
            changed = True

    elif tag in ("circle", "ellipse"):
        cx = _parse_float(elem.get("cx"))
        cy = _parse_float(elem.get("cy"))
        nx = min(max(cx, 0.0), cw)
        ny = min(max(cy, 0.0), ch)
        if (nx, ny) != (cx, cy):
            elem.set("cx", _format_num(nx))
            elem.set("cy", _format_num(ny))
            report["fixed"].append(f"clamped <{tag}> center to canvas")
            changed = True

    elif tag in ("text", "image", "use"):
        x = _parse_float(elem.get("x"))
        y = _parse_float(elem.get("y"))
        nx = min(max(x, 0.0), cw)
        ny = min(max(y, 0.0), ch)
        if (nx, ny) != (x, y):
            elem.set("x", _format_num(nx))
            elem.set("y", _format_num(ny))
            report["fixed"].append(f"clamped <{tag}> position to canvas")
            changed = True

    return changed


def _clamp_coordinates(root: ET.Element, lock: dict, report: dict[str, list[str]]) -> bool:
    cw, ch, _ = _canvas_size(lock)
    changed = False
    for elem in root.iter():
        tag = _local_tag(elem)
        if tag in _POSITION_TAGS:
            if _clamp_element(elem, cw, ch, report):
                changed = True
    return changed


def _wrap_text_with_tspans(
    text_elem: ET.Element,
    lines: list[str],
    line_height: float,
) -> None:
    for child in list(text_elem):
        text_elem.remove(child)
    text_elem.text = None
    text_elem.tail = None
    base_y = _parse_float(text_elem.get("y"))
    for i, line in enumerate(lines):
        tspan = ET.SubElement(text_elem, f"{{{SVG_NS}}}tspan")
        if i == 0:
            tspan.text = line
        else:
            tspan.set("x", text_elem.get("x", "0"))
            tspan.set("dy", _format_num(line_height))
            tspan.text = line


def _fix_text_overflow(root: ET.Element, lock: dict, report: dict[str, list[str]]) -> bool:
    cw, ch, _ = _canvas_size(lock)
    body_px = _body_font_size(lock)
    min_font = max(8.0, body_px * 0.5)
    margin = 24.0
    changed = False

    parent_map = _build_parent_map(root)

    for elem in root.iter():
        if _local_tag(elem) != "text":
            continue
        if list(elem):
            # Already has tspans — only adjust font-size on the parent when safe.
            if any(_local_tag(c) == "tspan" and c.get("dy") for c in elem):
                continue

        content = _text_content(elem)
        if not content or len(content) < 20:
            continue

        font_size = _parse_float(elem.get("font-size"), body_px)
        font_weight = elem.get("font-weight", "400")
        anchor = elem.get("text-anchor", "start")
        x = _parse_float(elem.get("x"))

        container = _find_text_container(elem, parent_map)
        if container:
            left_x, max_width = container
        else:
            left_x = margin
            max_width = cw - 2 * margin
            if anchor == "middle":
                left_x = max(margin, x - max_width / 2)
            elif anchor in ("end", "right"):
                left_x = max(margin, x - max_width)

        est_width = estimate_text_width(content, font_size, font_weight)
        left, right = _text_bounds(x, est_width, anchor)

        overflow = right > left_x + max_width + 2 or left < left_x - 2
        if not overflow and right <= cw - margin and left >= margin:
            continue

        new_size = font_size
        while new_size > min_font and estimate_text_width(content, new_size, font_weight) > max_width:
            new_size = max(min_font, new_size * 0.9)

        if new_size < font_size - 0.01:
            elem.set("font-size", _format_num(new_size))
            report["fixed"].append(
                f"reduced font-size {_format_num(font_size)}→{_format_num(new_size)} for text overflow"
            )
            changed = True
            font_size = new_size

        if estimate_text_width(content, font_size, font_weight) <= max_width:
            continue

        # Split into wrapped lines only when still overflowing at minimum readable size.
        if font_size > min_font + 0.01:
            report["warnings"].append(
                "text still overflows after font-size reduction; manual review recommended"
            )
            continue

        words = content.split()
        if len(words) < 2:
            report["warnings"].append("single-word text overflow; cannot split safely")
            continue

        lines: list[str] = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if not current or estimate_text_width(candidate, font_size, font_weight) <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)

        if len(lines) > 1:
            line_height = font_size * 1.25
            _wrap_text_with_tspans(elem, lines, line_height)
            report["fixed"].append(f"split overflowing text into {len(lines)} line(s) via <tspan>")
            changed = True
        else:
            report["warnings"].append("text overflow could not be wrapped safely")

    return changed


def auto_fix_svg(
    svg_path: str | Path,
    spec_lock_path: str | Path | None = None,
    *,
    dry_run: bool = False,
) -> dict[str, list[str]]:
    """Apply conservative auto-fixes to one SVG file.

    Returns {"fixed": [...], "warnings": [...], "errors": [...]}.
    """
    report: dict[str, list[str]] = {"fixed": [], "warnings": [], "errors": []}
    path = Path(svg_path)

    if not path.exists():
        report["errors"].append(f"SVG not found: {path}")
        return report

    lock_path = _resolve_spec_lock(path, Path(spec_lock_path) if spec_lock_path else None)
    lock = _load_lock(lock_path)
    if not lock:
        report["warnings"].append(
            "spec_lock.md not found or unreadable — using default canvas 1280×720"
        )

    try:
        content = path.read_text(encoding="utf-8")
        root = ET.fromstring(content)
    except ET.ParseError as exc:
        report["errors"].append(f"Invalid XML — cannot auto-fix: {exc}")
        return report
    except OSError as exc:
        report["errors"].append(f"Failed to read SVG: {exc}")
        return report

    if _local_tag(root) != "svg":
        report["errors"].append("Root element is not <svg>")
        return report

    changed = False
    for fixer in (
        lambda: _fix_viewbox(root, lock, report),
        lambda: _fix_font_family(root, lock, report),
        lambda: _remove_empty_groups(root, report),
        lambda: _clamp_coordinates(root, lock, report),
        lambda: _fix_text_overflow(root, lock, report),
    ):
        try:
            if fixer():
                changed = True
        except Exception as exc:
            report["errors"].append(f"Fix step failed: {exc}")

    if changed and not dry_run:
        tree = ET.ElementTree(root)
        tree.write(str(path), encoding="unicode", xml_declaration=False)

    if dry_run and changed:
        report["warnings"].append("dry-run: changes were planned but not written")

    return report


def _print_report(path: Path, report: dict[str, list[str]]) -> None:
    print(f"\n[AUTO-FIX] {path.name}")
    for item in report["fixed"]:
        print(f"  [FIXED] {item}")
    for item in report["warnings"]:
        print(f"  [WARN] {item}")
    for item in report["errors"]:
        print(f"  [ERROR] {item}")
    if not report["fixed"] and not report["warnings"] and not report["errors"]:
        print("  [OK] No changes needed")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="PPT Master - SVG Auto-Fix Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    fix_parser = sub.add_parser(
        "auto-fix",
        help="Apply conservative fixes to one SVG file",
    )
    fix_parser.add_argument("--svg", required=True, type=Path, help="Path to SVG file")
    fix_parser.add_argument(
        "--spec-lock", type=Path, default=None,
        help="Path to spec_lock.md (auto-detected from project if omitted)",
    )
    fix_parser.add_argument(
        "--dry-run", action="store_true",
        help="Report planned fixes without writing the SVG",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "auto-fix":
        report = auto_fix_svg(args.svg, args.spec_lock, dry_run=args.dry_run)
        _print_report(args.svg, report)
        if report["errors"]:
            return 1
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
