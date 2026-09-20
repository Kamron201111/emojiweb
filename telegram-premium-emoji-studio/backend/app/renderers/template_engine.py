import copy
import gzip
import json

try:  # package import (app.renderers.*)
    from .font_render import build_lottie_letter_groups
    from .templates_config import FALLBACK_FONT
except ImportError:  # standalone import (running inside renderers/ directly)
    from font_render import build_lottie_letter_groups
    from templates_config import FALLBACK_FONT


def hex_to_rgb01(hex_color):
    h = hex_color.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0


def _shape_color_key(shape):
    ty = shape.get("ty")
    if ty in ("gf", "gs"):
        g = shape.get("g", {}).get("k")
        if not isinstance(g, dict):
            return None
        arr = g.get("k")
        if not isinstance(arr, list) or len(arr) < 4:
            return None
        if not all(isinstance(x, (int, float)) for x in arr[:4]):
            return None
        return ("grad", round(float(arr[1]), 3), round(float(arr[2]), 3), round(float(arr[3]), 3))
    k = shape.get("c", {}).get("k")
    if not isinstance(k, list) or len(k) < 3:
        return None
    if not all(isinstance(x, (int, float)) for x in k[:3]):
        return None
    return tuple(round(float(x), 3) for x in k[:3])


def _set_shape_color(shape, rgb):
    ty = shape.get("ty")
    if ty in ("gf", "gs"):
        p = shape.get("g", {}).get("p")
        kobj = shape.get("g", {}).get("k")
        if isinstance(kobj, dict) and p:
            arr = kobj.get("k")
            if isinstance(arr, list):
                tr, tg, tb = rgb
                n = min(int(p), len(arr) // 4)
                for i in range(n):
                    base = i * 4
                    orig_r, orig_g, orig_b = arr[base + 1], arr[base + 2], arr[base + 3]
                    luminance = (orig_r + orig_g + orig_b) / 3.0
                    arr[base + 1] = max(0.0, min(1.0, tr * luminance))
                    arr[base + 2] = max(0.0, min(1.0, tg * luminance))
                    arr[base + 3] = max(0.0, min(1.0, tb * luminance))
        return
    r, g, b = rgb
    k = shape.get("c", {}).get("k")
    if isinstance(k, list) and len(k) == 4:
        shape["c"]["k"] = [r, g, b, k[3]]
    else:
        shape["c"]["k"] = [r, g, b]


def _walk_shapes(shapes, visit_fn, ignore_nm_prefix=None):
    for shape in shapes:
        ty = shape.get("ty")
        nm = shape.get("nm") or ""
        if ignore_nm_prefix and nm.startswith(ignore_nm_prefix):
            continue
        if ty == "gr":
            visit_fn(shape)
            _walk_shapes(shape.get("it", []), visit_fn, ignore_nm_prefix)
        else:
            visit_fn(shape)


def _collect_color_stats(data):
    stroke_counter = {}
    fill_counter = {}

    def visit(shape):
        key = _shape_color_key(shape)
        if key is None:
            return
        ty = shape.get("ty")
        if ty in ("st", "gs"):
            stroke_counter[key] = stroke_counter.get(key, 0) + 1
        elif ty in ("fl", "gf"):
            fill_counter[key] = fill_counter.get(key, 0) + 1

    all_shapes = []
    for layer in data.get("layers", []):
        s = layer.get("shapes")
        if s:
            all_shapes.append(s)
    for asset in data.get("assets", []):
        for layer in asset.get("layers", []) or []:
            s = layer.get("shapes")
            if s:
                all_shapes.append(s)

    for shapes in all_shapes:
        _walk_shapes(shapes, visit)

    dom_stroke = max(stroke_counter, key=stroke_counter.get) if stroke_counter else None
    dom_fill = max(fill_counter, key=fill_counter.get) if fill_counter else None
    return dom_stroke, dom_fill


def _recolor_shapes(data, outer_key, outer_rgb, inner_key, inner_rgb):
    def visit(shape):
        key = _shape_color_key(shape)
        if key is None:
            return
        ty = shape.get("ty")
        if ty in ("st", "gs") and outer_key is not None and key == outer_key:
            _set_shape_color(shape, outer_rgb)
        elif ty in ("fl", "gf") and inner_key is not None and key == inner_key:
            _set_shape_color(shape, inner_rgb)

    all_shapes = []
    for layer in data.get("layers", []):
        s = layer.get("shapes")
        if s:
            all_shapes.append(s)
    for asset in data.get("assets", []):
        for layer in asset.get("layers", []) or []:
            s = layer.get("shapes")
            if s:
                all_shapes.append(s)
    for shapes in all_shapes:
        _walk_shapes(shapes, visit)


def _hsv_of(rgb):
    import colorsys
    return colorsys.rgb_to_hsv(max(0.0, min(1.0, rgb[0])), max(0.0, min(1.0, rgb[1])), max(0.0, min(1.0, rgb[2])))


def _approx_rgb(key):
    if not isinstance(key, tuple):
        return None
    if len(key) == 3:
        return key
    if len(key) == 4 and key[0] == "grad":
        return key[1:4]
    return None


def _retint(key, target_rgb, ref_key=None, tol=0.15, min_sat=0.10):
    rgb = _approx_rgb(key)
    if rgb is None:
        return None
    ref_rgb = _approx_rgb(ref_key) if ref_key else None

    import colorsys
    src_h, src_s, src_v = _hsv_of(rgb)
    target_h, target_s, target_v = _hsv_of(target_rgb)

    if ref_rgb:
        ref_h, ref_s, ref_v = _hsv_of(ref_rgb)
        if ref_s >= min_sat and src_s >= min_sat:
            dh = abs(src_h - ref_h)
            dh = min(dh, 1.0 - dh)
            if dh > tol:
                return None

    if target_s < 0.1:  # Qora, Kulrang, Oq
        if ref_rgb:
            _rh, _rs, ref_v = _hsv_of(ref_rgb)
            v_ratio = src_v / max(ref_v, 0.001)
        else:
            v_ratio = src_v

        if target_v < 0.1:  # Qora (#000000)
            val = max(0.0, min(0.35, (v_ratio - 1.0) * 0.25 if v_ratio > 1.0 else 0.0))
        else:
            val = max(0.0, min(1.0, target_v * v_ratio))
        return (val, val, val)
    else:
        if ref_rgb:
            _rh, _rs, ref_v = _hsv_of(ref_rgb)
            v_ratio = src_v / max(ref_v, 0.001)
        else:
            v_ratio = 1.0
        v_ratio = max(0.2, min(v_ratio, 1.5))
        r, g, b = colorsys.hsv_to_rgb(target_h, target_s, max(0.0, min(1.0, target_v * v_ratio)))
        return (r, g, b)


def _recolor_shapes_full(data, outer_key, outer_rgb, inner_key, inner_rgb):
    def visit(shape):
        key = _shape_color_key(shape)
        if key is None:
            return
        ty = shape.get("ty")
        if ty in ("st", "gs"):
            if outer_key is not None and key == outer_key:
                _set_shape_color(shape, outer_rgb)
            elif outer_key is not None:
                tint = _retint(key, outer_rgb, ref_key=outer_key)
                if tint is not None:
                    _set_shape_color(shape, tint)
        elif ty in ("fl", "gf"):
            if inner_key is not None and key == inner_key:
                _set_shape_color(shape, inner_rgb)
            elif inner_key is not None:
                tint = _retint(key, inner_rgb, ref_key=inner_key)
                if tint is not None:
                    _set_shape_color(shape, tint)

    all_shapes = []
    for layer in data.get("layers", []):
        s = layer.get("shapes")
        if s:
            all_shapes.append(s)
    for asset in data.get("assets", []):
        for layer in asset.get("layers", []) or []:
            s = layer.get("shapes")
            if s:
                all_shapes.append(s)
    for shapes in all_shapes:
        _walk_shapes(shapes, visit)


def _get_layer_list(data, path):
    if path[0] == "layers":
        return data["layers"]
    if path[0] == "assets":
        asset_id = path[1]
        asset = next(a for a in data["assets"] if a["id"] == asset_id)
        return asset["layers"]
    raise ValueError(f"unknown path {path}")


def _original_center(shapes):
    """Find the center (x, y) of the placeholder text currently baked into
    a layer's shapes, in that layer's own local coordinate space.

    Templates position their text two different ways: some center the
    content at local (0, 0) and rely on the layer's anchor+position
    transform to place it on the canvas; others leave anchor/position at
    (0, 0) and bake the absolute canvas position directly into the shape
    coordinates. Always assuming the old placeholder was centered at the
    origin only holds for the first group - for the second it silently
    shifts new text off to one side (or, vertically, leaves it sitting
    noticeably high/low in its badge once a manually-guessed baseline
    number doesn't quite match). Measuring the actual bounding box of
    what's already there works for both cases, for both axes."""
    xs, ys = [], []

    def walk(items):
        for it in items:
            if it.get("ty") == "gr":
                walk(it.get("it", []))
            elif it.get("ty") == "sh":
                for v in it["ks"]["k"].get("v", []):
                    xs.append(v[0])
                    ys.append(v[1])

    walk(shapes)
    if not xs:
        return 0.0, 0.0
    return (min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0


def _own_scale(layer):
    s = layer.get("ks", {}).get("s")
    if not s or not isinstance(s.get("k"), list) or not s["k"] or isinstance(s["k"][0], dict):
        return 1.0, 1.0
    sx, sy = s["k"][0], s["k"][1]
    return (sx / 100.0 or 1.0), (sy / 100.0 or 1.0)


def _layer_scale(layer, layer_list=None):
    """The layer's effective scale (sx, sy) as fractions (100% -> 1.0),
    including any scale inherited from a parent layer (AE-style layer
    parenting multiplies transforms down the chain - a layer that leaves
    its own scale at 100% but is parented to one scaled at 129% still
    ends up rendering at 129%, and treating it as 100% would make it come
    out the wrong size relative to its sibling).

    Several templates have their text layer scaled well past 100% inside
    the template itself (as high as ~380%). target_height/max_width in the
    config are meant to describe the final size the word should appear at
    on the sticker - if we don't account for this per-layer (and inherited)
    scale first, that amplification stacks on top and the word renders far
    larger (and can spill past the intended badge) than the configured
    numbers say."""
    sx, sy = _own_scale(layer)
    parent_ind = layer.get("parent")
    if parent_ind is not None and layer_list is not None:
        parent = next((l for l in layer_list if l.get("ind") == parent_ind), None)
        if parent is not None:
            psx, psy = _layer_scale(parent, layer_list)
            sx, sy = sx * psx, sy * psy
    return sx, sy


def render_template(template_cfg: dict, word: str,
                    outer_hex: str | None = None,
                    inner_hex: str | None = None,
                    text_hex: str | None = None) -> dict:
    with open(template_cfg["file"], encoding="utf-8") as f:
        data = json.load(f)
    data = copy.deepcopy(data)
    font_path = template_cfg["font"]

    if outer_hex or inner_hex:
        dom_stroke, dom_fill = _collect_color_stats(data)
        outer_rgb = hex_to_rgb01(outer_hex) if outer_hex else None
        inner_rgb = hex_to_rgb01(inner_hex) if inner_hex else None
        if outer_hex or inner_hex:
            _recolor_shapes_full(data,
                                 dom_stroke if outer_hex else None, outer_rgb,
                                 dom_fill if inner_hex else None, inner_rgb)

    text_rgb = hex_to_rgb01(text_hex) if text_hex else None

    for tl_idx, tl in enumerate(template_cfg["text_layers"]):
        layer_list = _get_layer_list(data, tl["path"])
        layer = next(l for l in layer_list if l.get("ind") == tl["ind"])

        center_x, center_y = _original_center(layer.get("shapes", []))
        scale_x, scale_y = _layer_scale(layer, layer_list)
        y_nudge = tl.get("y_nudge", 0)
        center_y = center_y - (y_nudge / scale_y if scale_y else y_nudge)

        if text_rgb is not None:
            base_fill = tl["fill"]
            base_v = sum(base_fill[:3]) / 3.0 if base_fill else 0.5
            if base_v < 0.001:
                base_v = 0.5
            v_ratio = max(0.25, min(1.25, base_v / base_v))
            lum = []
            if tl_idx == 0:
                lum_factor = 1.0
            else:
                lum_factor = 0.78
            fill_rgba = [
                max(0.0, min(1.0, text_rgb[0] * lum_factor)),
                max(0.0, min(1.0, text_rgb[1] * lum_factor)),
                max(0.0, min(1.0, text_rgb[2] * lum_factor)),
                1.0,
            ]
            stroke_rgba = list(fill_rgba)
        else:
            fill_rgba = tl["fill"]
            stroke_rgba = tl["stroke"] or [0, 0, 0, 0]

        stroke_w = tl["stroke_w"]
        max_width = tl.get("max_width")
        groups = build_lottie_letter_groups(
            word, font_path,
            tl["target_height"] / scale_y, center_y,
            stroke_rgba, stroke_w, fill_rgba,
            max_width=(max_width / scale_x) if max_width else None,
            center_x=center_x,
            fallback_font_path=FALLBACK_FONT,
        )
        layer["shapes"] = groups

    return data


def save_as_tgs(lottie_dict: dict, out_path: str):
    raw = json.dumps(lottie_dict, separators=(",", ":")).encode("utf-8")
    with gzip.open(out_path, "wb") as f:
        f.write(raw)
