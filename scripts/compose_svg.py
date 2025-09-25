# scripts/compose_svg.py
# Compose two component SVGs into a single glyph: ⿰ (left-right) or ⿱ (top-bottom)
# Usage examples:
#   python compose_svg.py --struct lr --left ../svg/radicals/water.svg --right ../svg/phonetics/qing.svg --out ../svg/out/shui_qing.svg
#   python compose_svg.py --struct tb --top  ../svg/radicals/water.svg --bottom ../svg/phonetics/qing.svg --out ../svg/out/shui_qing_tb.svg

import argparse
import os
import xml.etree.ElementTree as ET

SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)

def parse_viewbox(svg_root):
    vb = svg_root.get("viewBox")
    if not vb:
        # Assume square 1024 if missing
        return (0.0, 0.0, 1024.0, 1024.0)
    parts = [float(x) for x in vb.replace(",", " ").split()]
    if len(parts) == 4:
        return tuple(parts)
    # Fallback
    return (0.0, 0.0, 1024.0, 1024.0)

def load_svg_children(svg_path):
    tree = ET.parse(svg_path)
    root = tree.getroot()
    vb = parse_viewbox(root)

    # Grab all top-level children (skip defs if you like; we’ll keep them)
    # To reduce ID collisions, we wrap everything in a <g>
    children = list(root)
    return children, vb

def make_root_svg(size=1024):
    root = ET.Element("{%s}svg" % SVG_NS, {
        "xmlns": SVG_NS,
        "viewBox": f"0 0 {size} {size}",
        "width": str(size),
        "height": str(size),
    })
    return root

def transform_group(children, translate_xy=(0,0), scale_xy=(1.0,1.0), id_prefix="c"):
    """
    Wrap a list of elements into a <g> with a transform.
    We also clone elements to avoid moving originals.
    """
    tx, ty = translate_xy
    sx, sy = scale_xy
    g = ET.Element("{%s}g" % SVG_NS, {"transform": f"translate({tx},{ty}) scale({sx},{sy})"})
    for el in children:
        g.append(el)  # safe to re-parent in our simple case
    return g

def compose_lr(left_svg, right_svg, out_path, size=1024, gutter_ratio=0.02):
    """
    Left-right layout (⿰): left occupies ~48%, right ~48%, with a small gutter.
    We scale each component to fit its slot, preserving aspect ratio.
    """
    # Load inputs
    left_children, (lx0, ly0, lw, lh) = load_svg_children(left_svg)
    right_children, (rx0, ry0, rw, rh) = load_svg_children(right_svg)

    root = make_root_svg(size=size)

    gutter = size * gutter_ratio
    slot_w = (size - gutter) / 2.0
    slot_h = size

    # Compute scale to fit each component into its slot while preserving aspect
    left_scale = min(slot_w / lw, slot_h / lh)
    right_scale = min(slot_w / rw, slot_h / rh)

    # After scaling, compute actual drawn width/height
    left_draw_w, left_draw_h = lw * left_scale, lh * left_scale
    right_draw_w, right_draw_h = rw * right_scale, rh * right_scale

    # Center vertically within slot, and translate to slot x
    left_tx = 0 + (slot_w - left_draw_w) / 2.0 - lx0 * left_scale
    left_ty = (size - left_draw_h) / 2.0 - ly0 * left_scale

    right_tx = slot_w + gutter + (slot_w - right_draw_w) / 2.0 - rx0 * right_scale
    right_ty = (size - right_draw_h) / 2.0 - ry0 * right_scale

    # Wrap and append
    left_group = transform_group(left_children, (left_tx, left_ty), (left_scale, left_scale), id_prefix="L")
    right_group = transform_group(right_children, (right_tx, right_ty), (right_scale, right_scale), id_prefix="R")

    root.append(left_group)
    root.append(right_group)

    # Ensure output folder exists
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    ET.ElementTree(root).write(out_path, encoding="utf-8", xml_declaration=True)
    print(f"✅ Wrote {out_path}")

def compose_tb(top_svg, bottom_svg, out_path, size=1024, gutter_ratio=0.02):
    """
    Top-bottom layout (⿱): top occupies ~48% height, bottom ~48%, with a small gutter.
    """
    top_children, (tx0, ty0, tw, th) = load_svg_children(top_svg)
    bot_children, (bx0, by0, bw, bh) = load_svg_children(bottom_svg)

    root = make_root_svg(size=size)

    gutter = size * gutter_ratio
    slot_h = (size - gutter) / 2.0
    slot_w = size

    top_scale = min(slot_w / tw, slot_h / th)
    bot_scale = min(slot_w / bw, slot_h / bh)

    top_draw_w, top_draw_h = tw * top_scale, th * top_scale
    bot_draw_w, bot_draw_h = bw * bot_scale, bh * bot_scale

    top_tx = (size - top_draw_w) / 2.0 - tx0 * top_scale
    top_ty = 0 + (slot_h - top_draw_h) / 2.0 - ty0 * top_scale

    bot_tx = (size - bot_draw_w) / 2.0 - bx0 * bot_scale
    bot_ty = slot_h + gutter + (slot_h - bot_draw_h) / 2.0 - by0 * bot_scale

    top_group = transform_group(top_children, (top_tx, top_ty), (top_scale, top_scale), id_prefix="T")
    bot_group = transform_group(bot_children, (bot_tx, bot_ty), (bot_scale, bot_scale), id_prefix="B")

    root.append(top_group)
    root.append(bot_group)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    ET.ElementTree(root).write(out_path, encoding="utf-8", xml_declaration=True)
    print(f"✅ Wrote {out_path}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--struct", choices=["lr","tb"], required=True, help="lr=⿰ (left-right), tb=⿱ (top-bottom)")
    ap.add_argument("--left")
    ap.add_argument("--right")
    ap.add_argument("--top")
    ap.add_argument("--bottom")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    if args.struct == "lr":
        if not (args.left and args.right):
            raise SystemExit("For --struct lr you must provide --left and --right")
        compose_lr(args.left, args.right, args.out)
    else:
        if not (args.top and args.bottom):
            raise SystemExit("For --struct tb you must provide --top and --bottom")
        compose_tb(args.top, args.bottom, args.out)

if __name__ == "__main__":
    main()
