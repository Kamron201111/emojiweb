import sys, os
sys.path.insert(0, os.path.abspath('.'))
import logo_engine
import json

path = os.path.join('templates_tgs3', '001.json')
with open(path, 'r', encoding='utf-8') as f:
    raw = json.load(f)
data = logo_engine._normalize_lottie_keys(raw)

# TEST 4: REAL build_tgs_sticker
nick_svg = logo_engine.text_to_svg("TAK", font_path=logo_engine.FALLBACK_FONT, letter_spacing=20)
_, built_dict = logo_engine.build_tgs_sticker(
    '001.json', nick_svg, '#FFFFFF', '#000000', '#FFFFFF',
    size_percent=100, watermark=False, dir_path='templates_tgs3'
)

print("=== FINAL nick placement ===")
final_nick_bbox_local = None
for asset in built_dict.get('assets', []):
    if asset.get('id') != 'mylogo': continue
    for layer in asset.get('layers', []):
        shapes = layer.get('shapes') or []
        for s in shapes:
            if s.get('ty') == 'gr' and len(s.get('it', [])) > 0:
                verts = []
                logo_engine._collect_shape_vertices(s.get('it', []), verts)
                if verts:
                    xs = [v[0] for v in verts]; ys = [v[1] for v in verts]
                    final_nick_bbox_local = (min(xs), min(ys), max(xs), max(ys))
                    cx = (final_nick_bbox_local[0]+final_nick_bbox_local[2])/2
                    cy = (final_nick_bbox_local[1]+final_nick_bbox_local[3])/2
                    print(f"LOCAL nick bbox (asset 512x512): {final_nick_bbox_local}")
                    print(f"  center=({cx:.1f},{cy:.1f})  size={final_nick_bbox_local[2]-final_nick_bbox_local[0]:.0f}x{final_nick_bbox_local[3]-final_nick_bbox_local[1]:.0f}")

# Compose with refId layer transform to get canvas coords
for layer in built_dict.get('layers', []):
    if layer.get('refId') == 'mylogo':
        ks = layer.get('ks', {})
        p = ks.get('p', {}).get('k', [0,0])[:2]
        s = ks.get('s', {}).get('k', [100,100])[:2]
        a = ks.get('a', {}).get('k', [0,0])[:2]
        print(f"\nrefId layer: ks.p={p}, ks.s={s}, ks.a={a}")
        if final_nick_bbox_local:
            sx, sy = s[0]/100., s[1]/100.
            # Compose local -> canvas:
            # canvas_coord = (local - anchor) * scale + position
            x0 = (final_nick_bbox_local[0]-a[0])*sx + p[0]
            y0 = (final_nick_bbox_local[1]-a[1])*sy + p[1]
            x1 = (final_nick_bbox_local[2]-a[0])*sx + p[0]
            y1 = (final_nick_bbox_local[3]-a[1])*sy + p[1]
            canvas_bbox = (x0,y0,x1,y1)
            cx = (x0+x1)/2
            cy = (y0+y1)/2
            print(f"CANVAS nick bbox (512x512): {canvas_bbox}")
            print(f"  center=({cx:.1f},{cy:.1f})  size={x1-x0:.0f}x{y1-y0:.0f}")
            print(f"  Canvas 512x512. (0,0)=top-left, (512,512)=bottom-right")
            if cy > 400 or cx > 400:
                print("  PROBLEM: Nick is at BOTTOM/RIGHT!")
            elif cy < 100 or cx < 100:
                print("  PROBLEM: Nick is at TOP/LEFT!")
            else:
                print("  Looks OK-ish.")
        break

# NOW TEST templates_tgs2 for comparison
print("\n=== Working templates_tgs2/001.json ===")
path2 = os.path.join('templates_tgs2', '001.json')
with open(path2, 'r', encoding='utf-8') as f: raw2 = json.load(f)
data2 = logo_engine._normalize_lottie_keys(raw2)
ref2 = None
for layer in data2.get('layers', []):
    if layer.get('refId') == 'mylogo':
        ref2 = layer
        break
if ref2:
    ks2 = ref2.get('ks', {})
    p2 = ks2.get('p', {}).get('k')[:2]
    s2 = ks2.get('s', {}).get('k')[:2]
    a2 = ks2.get('a', {}).get('k', [0,0])[:2]
    print(f"  tgs2 refId p={p2} s={s2} a={a2}")
# Build tgs2 sticker
_, built_dict2 = logo_engine.build_tgs_sticker(
    '001.json', nick_svg, '#FFFFFF', '#000000', '#FFFFFF',
    size_percent=100, watermark=False, dir_path='templates_tgs2'
)
for asset in built_dict2.get('assets', []):
    if asset.get('id') != 'mylogo': continue
    for layer in asset.get('layers', []):
        shapes = layer.get('shapes') or []
        for s in shapes:
            if s.get('ty') == 'gr' and len(s.get('it', [])) > 0:
                verts = []
                logo_engine._collect_shape_vertices(s.get('it', []), verts)
                if verts:
                    xs = [v[0] for v in verts]; ys = [v[1] for v in verts]
                    bb = (min(xs), min(ys), max(xs), max(ys))
                    if ref2:
                        sx2, sy2 = s2[0]/100., s2[1]/100.
                        x0=(bb[0]-a2[0])*sx2+p2[0]; y0=(bb[1]-a2[1])*sy2+p2[1]
                        x1=(bb[2]-a2[0])*sx2+p2[0]; y1=(bb[3]-a2[1])*sy2+p2[1]
                        print(f"  tgs2 CANVAS nick bbox: ({x0:.1f},{y0:.1f},{x1:.1f},{y1:.1f})")
                        print(f"  center=({(x0+x1)/2:.1f},{(y0+y1)/2:.1f})  size={x1-x0:.0f}x{y1-y0:.0f}")
