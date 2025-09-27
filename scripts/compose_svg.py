# scripts/compose_svg.py
# Compose two component SVGs into a single glyph: ⿰ (left-right) or ⿱ (top-bottom)

import argparse
import os
import xml.etree.ElementTree as ET

SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)

def parse_viewbox(svg_root):
    vb = svg_root.get("viewBox")
    if not vb:
        return (0.0, 0.0, 1024.0, 1024.0)
    parts = [float(x) for x in vb.replace(",", " ").split()]
    if len(parts) == 4:
        return tuple(parts)
    return (0.0, 0.0, 1024.0, 1024.0)

def load_svg_children(svg_path):
    tree = ET.parse(svg_path)
    root = tree.getroot()
    vb = parse_viewbox(root)
    children = list(root)  # keep top-level nodes (incl. <defs>)
    return children, vb

def make_root_svg(size=1024):
    root = ET.Element("{%s}svg" % SVG_NS, {
        "xmlns": SVG_NS,
        "viewBox": f"0 0 {size} {size}",
        "width": str(size),
        "height": str(size),
    })
    return root

def transform_group(children, translate_xy=(0, 0), scale_xy=(1.0, 1.0), id_prefix=None):
    """
    Wrap a list of elements into a <g> with translate+scale.
    `id_prefix` is accepted for API compatibility but unused.
    """
    tx, ty = translate_xy
    sx, sy = scale_xy
    g = ET.Element("{%s}g" % SVG_NS, {"transform": f"translate({tx},{ty}) scale({sx},{sy})"})
    for el in children:
        g.append(el)  # re-parent into group
    return g

def compose_lr(
    left_svg,
    right_svg,
    out_path,
    size=1024,
    gutter_ratio=0.02,     # space between left & right
    left_width_ratio=0.35, # share of usable width for LEFT
    height_ratio=0.82,     # vertical margin (shorter than canvas)
    outer_margin_ratio=0.1,  # NEW: margin on both outer edges (left & right)
    slot_inset_ratio=0.06,    # NEW: shrink each slot internally (padding inside slots)
    align="center"            # "center" or "baseline"
):
    """
    ⿰ with NON-UNIFORM scaling (keep height, squeeze width) and horizontal padding.
    - outer_margin_ratio adds equal margins at the very left/right of the canvas.
    - slot_inset_ratio adds internal padding within each slot so glyphs don't hit slot edges.
    """
    left_children,  (lx0, ly0, lw, lh) = load_svg_children(left_svg)
    right_children, (rx0, ry0, rw, rh) = load_svg_children(right_svg)

    # Clamp inputs
    left_width_ratio   = max(0.05, min(0.9, float(left_width_ratio)))
    outer_margin_ratio = max(0.0,  min(0.2, float(outer_margin_ratio)))
    slot_inset_ratio   = max(0.0,  min(0.4, float(slot_inset_ratio)))
    gutter             = size * float(gutter_ratio)

    # --- Horizontal layout with outer margins ---
    outer_margin = size * outer_margin_ratio                  # margin on the far left & right
    total_w      = max(1.0, size - 2*outer_margin - gutter)   # width available for both slots (excluding margins & gutter)
    total_h      = size * float(height_ratio)
    y_offset     = (size - total_h) / 2.0

    left_slot_w   = total_w * left_width_ratio
    right_slot_w  = total_w - left_slot_w

    # Slot X origins (respect outer margins)
    left_slot_x   = outer_margin
    right_slot_x  = outer_margin + left_slot_w + gutter

    # --- Inset each slot so glyphs don't reach slot edges ---
    left_inner_w   = left_slot_w  * (1.0 - 2.0*slot_inset_ratio)
    right_inner_w  = right_slot_w * (1.0 - 2.0*slot_inset_ratio)
    left_inner_x   = left_slot_x  + left_slot_w  * slot_inset_ratio
    right_inner_x  = right_slot_x + right_slot_w * slot_inset_ratio

    # Non-uniform scales: exact height to total_h; width to inner slot width
    sy_left   = total_h / lh
    sx_left   = left_inner_w / lw
    sy_right  = total_h / rh
    sx_right  = right_inner_w / rw

    # Drawn sizes
    left_draw_w, left_draw_h   = lw * sx_left,  lh * sy_left
    right_draw_w, right_draw_h = rw * sx_right, rh * sy_right

    # Vertical alignment
    if align == "baseline":
        left_ty  = (size - left_draw_h)  - ly0 * sy_left
        right_ty = (size - right_draw_h) - ry0 * sy_right
    else:
        left_ty  = y_offset + (total_h - left_draw_h)  / 2.0 - ly0 * sy_left
        right_ty = y_offset + (total_h - right_draw_h) / 2.0 - ry0 * sy_right

    # Center horizontally within the *inner* slot rectangles
    left_tx  = left_inner_x  + (left_inner_w  - left_draw_w)  / 2.0 - lx0 * sx_left
    right_tx = right_inner_x + (right_inner_w - right_draw_w) / 2.0 - rx0 * sx_right

    root = make_root_svg(size=size)
    left_group  = transform_group(left_children,  (left_tx,  left_ty),  (sx_left,  sy_left),  id_prefix="L")
    right_group = transform_group(right_children, (right_tx, right_ty), (sx_right, sy_right), id_prefix="R")
    root.append(left_group)
    root.append(right_group)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    ET.ElementTree(root).write(out_path, encoding="utf-8", xml_declaration=True)
    print(f"✅ Wrote {out_path}")


def compose_tb(top_svg, bottom_svg, out_path, size=1024, gutter_ratio=0.02, top_height_ratio=0.33):
    """
    ⿱ with uniform scaling, but allow a shorter top (common in real glyphs).
      - top gets `top_height_ratio` of the canvas height
      - bottom gets the rest
    """
    top_children, (tx0, ty0, tw, th) = load_svg_children(top_svg)
    bot_children, (bx0, by0, bw, bh) = load_svg_children(bottom_svg)

    root = make_root_svg(size=size)

    gutter = size * gutter_ratio
    usable_h = size - gutter
    top_slot_h = usable_h * float(top_height_ratio)
    bot_slot_h = usable_h - top_slot_h
    slot_w = size

    top_scale = min(slot_w / tw, top_slot_h / th)
    bot_scale = min(slot_w / bw, bot_slot_h / bh)

    top_draw_w, top_draw_h = tw * top_scale, th * top_scale
    bot_draw_w, bot_draw_h = bw * bot_scale, bh * bot_scale

    top_tx = (size - top_draw_w) / 2.0 - tx0 * top_scale
    top_ty = (top_slot_h - top_draw_h) / 2.0 - ty0 * top_scale

    bot_tx = (size - bot_draw_w) / 2.0 - bx0 * bot_scale
    bot_ty = top_slot_h + gutter + (bot_slot_h - bot_draw_h) / 2.0 - by0 * bot_scale

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
