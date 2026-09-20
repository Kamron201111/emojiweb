import sys, os
sys.path.insert(0, os.path.abspath('.'))
import logo_engine
import json

# ============================================================
# TEST 1: templates_tgs3/001.json — Hozirgi nima sodir bo'lyapti?
# ============================================================
path = os.path.join('templates_tgs3', '001.json')
with open(path, 'r', encoding='utf-8') as f:
    raw = json.load(f)

data = logo_engine._normalize_lottie_keys(raw)
print("\n=== TEST 1: After normalize ===")

# Find mylogo asset:
for asset in data.get('assets', []):
    if asset.get('id') == 'mylogo':
        print(f"mylogo asset found: layers count={len(asset.get('layers', []))}")
        for i, layer in enumerate(asset.get('layers', [])):
            shapes = layer.get('shapes') or []
            print(f"  Asset layer[{i}] ind={layer.get('ind')} shapes count={len(shapes)} nm={layer.get('nm','?')}")
            for j, s in enumerate(shapes):
                print(f"    shape[{j}] ty={s.get('ty')} it_len={len(s.get('it', []))} nm={s.get('nm','?')}")

logo_group = logo_engine._find_mylogo_placeholder(data)
print(f"\n_find_mylogo_placeholder -> logo_group is {'FOUND' if logo_group is not None else 'NONE'}")

if logo_group:
    bbox = logo_engine._bbox_of_shape_group(logo_group)
    print(f"_bbox_of_shape_group -> {bbox}")
else:
    print("SKIP bbox (logo_group is None)")

# ============================================================
# TEST 2: Fallback logic values
# ============================================================
proj_box = logo_engine._project_mylogo_box_via_refid(data)
guess_box = logo_engine._guess_default_logo_box(data, dir_path='templates_tgs3')

# Local asset-space box (what we SHOULD use if nick goes INSIDE mylogo asset group):
asset_local_box = (512*0.14, 512*0.14, 512*0.86, 512*0.86)

print(f"\n=== TEST 2: Fallback box comparison ===")
print(f"asset_local_box (512x512, 14% pad) = {asset_local_box}     ← NIK ASSET ICHIDA BO'LSA, MUNOSABATLI BU!")
print(f"_project_mylogo_box_via_refid      = {proj_box}")
print(f"_guess_default_logo_box            = {guess_box}")

# ============================================================
# TEST 3: refId='mylogo' layer transform (ks.p & ks.s)
# ============================================================
print("\n=== TEST 3: refId='mylogo' layer ===")
for layer in data.get('layers', []):
    if layer.get('refId') == 'mylogo':
        ks = layer.get('ks', {})
        print(f"  ind={layer.get('ind')} nm={layer.get('nm','?')}")
        p = ks.get('p', {}).get('k')
        s = ks.get('s', {}).get('k')
        a = ks.get('a', {}).get('k')
        print(f"  ks.p (position) = {p}")
        print(f"  ks.s (scale %)  = {s}")
        print(f"  ks.a (anchor)   = {a}")
        print(f"  => Center project: (px+256*sx/100, py+256*sy/100) = ({p[0]+256*s[0]/100:.1f}, {p[1]+256*s[1]/100:.1f})")
        break

# ============================================================
# TEST 4: REAL build_tgs_sticker → qaerga joyladi nickni?
# ============================================================
nick_svg = logo_engine.text_to_svg("ТАК", font_path=logo_engine.FALLBACK_FONT, letter_spacing=20)
_, built_dict = logo_engine.build_tgs_sticker(
    '001.json', nick_svg, '#FFFFFF', '#000000', '#FFFFFF',
    size_percent=100, watermark=False, dir_path='templates_tgs3'
)

# Find the nick shape vertices inside the mylogo asset and compute final bbox
print("\n=== TEST 4: Final nick placement in built dict ===")
final_nick_bbox_local = None
final_nick_bbox_layer_level = None
for asset in built_dict.get('assets', []):
    if asset.get('id') != 'mylogo': continue
    for layer in asset.get('layers', []):
        shapes = layer.get('shapes') or []
        # find group with 'Logo' or the only grp
        for s in shapes:
            if s.get('ty') == 'gr' and len(s.get('it', [])) > 0:
                verts = []
                logo_engine._collect_shape_vertices(s.get('it', []), verts)
                if verts:
                    xs = [v[0] for v in verts]; ys = [v[1] for v in verts]
                    final_nick_bbox_local = (min(xs), min(ys), max(xs), max(ys))
                    print(f"  Nick inside mylogo asset, LOCAL bbox = {final_nick_bbox_local}")
                    print(f"    -> center=({(final_nick_bbox_local[0]+final_nick_bbox_local[2])/2:.1f},{(final_nick_bbox_local[1]+final_nick_bbox_local[3])/2:.1f}), size={final_nick_bbox_local[2]-final_nick_bbox_local[0]:.0f}x{final_nick_bbox_local[3]-final_nick_bbox_local[1]:.0f}")

# Now get the refId transform and compute CANVAS nick position by composing with refId layer
for layer in built_dict.get('layers', []):
    if layer.get('refId') == 'mylogo':
        ks = layer.get('ks', {})
        p = ks.get('p', {}).get('k', [0,0])[:2]
        s = ks.get('s', {}).get('k', [100,100])[:2]
        a = ks.get('a', {}).get('k', [0,0])[:2]
        if final_nick_bbox_local:
            sx, sy = s[0]/100., s[1]/100.
            x0 = (final_nick_bbox_local[0]-a[0])*sx + p[0]
            y0 = (final_nick_bbox_local[1]-a[1])*sy + p[1]
            x1 = (final_nick_bbox_local[2]-a[0])*sx + p[1]
            y1 = (final_nick_bbox_local[3]-a[1])*sy + p[1]
            final_nick_bbox_layer_level = (x0, y0, (final_nick_bbox_local[2]-a[0])*sx + p[0], (final_nick_bbox_local[3]-a[1])*sy + p[1])
            cx = (final_nick_bbox_layer_level[0]+final_nick_bbox_layer_level[2])/2
            cy = (final_nick_bbox_layer_level[1]+final_nick_bbox_layer_level[3])/2
            print(f"\n  Composed nick on CANVAS (with refId transform):")
            print(f"    bbox  = {final_nick_bbox_layer_level}")
            print(f"    center=({cx:.1f},{cy:.1f})  size={(final_nick_bbox_layer_level[2]-final_nick_bbox_layer_level[0]):.0f}x{(final_nick_bbox_layer_level[3]-final_nick_bbox_layer_level[1]):.0f}")
            print(f"  Canvas is 512x512. (512,512) = bottom-right corner")
            print(f"  Expected: nick should be in the sign area, not at bottom-right")
        break

# ============================================================
# TEST 5: What does WORKING templates_tgs2 return for comparison?
# ============================================================
print("\n=== TEST 5: Working templates_tgs2/001.json for comparison ===")
path2 = os.path.join('templates_tgs2', '001.json')
with open(path2, 'r', encoding='utf-8') as f:
    raw2 = json.load(f)
data2 = logo_engine._normalize_lottie_keys(raw2)

ref_layer2 = None
for layer in data2.get('layers', []):
    if layer.get('refId') == 'mylogo':
        ref_layer2 = layer
        break
if ref_layer2:
    ks2 = ref_layer2.get('ks', {})
    p2 = ks2.get('p', {}).get('k')[:2]
    s2 = ks2.get('s', {}).get('k')[:2]
    print(f"  tgs2 refId ks.p={p2} ks.s={s2}")

logo_group2 = logo_engine._find_mylogo_placeholder(data2)
if logo_group2:
    bbox2 = logo_engine._bbox_of_shape_group(logo_group2)
    print(f"  tgs2 _find_mylogo_placeholder=OK, bbox={bbox2}")
    cx2 = (bbox2[0]+bbox2[2])/2; cy2=(bbox2[1]+bbox2[3])/2
    print(f"  tgs2 nick LOCAL center=({cx2:.1f},{cy2:.1f}), size={(bbox2[2]-bbox2[0]):.0f}x{(bbox2[3]-bbox2[1]):.0f}")
    # compose with refId transform to canvas:
    sx2 = s2[0]/100.; sy2 = s2[1]/100.
    a2 = ks2.get('a', {}).get('k', [0,0])[:2]
    cxc2 = (cx2-a2[0])*sx2 + p2[0]
    cyc2 = (cy2-a2[1])*sy2 + p2[1]
    print(f"  tgs2 nick CANVAS composed center=({cxc2:.1f},{cyc2:.1f})")

# ============================================================
# FINAL: Why nick at BOTTOM?
# ============================================================
print("\n=== FINAL DIAGNOSIS ===")
if final_nick_bbox_local:
    cy_local = (final_nick_bbox_local[1]+final_nick_bbox_local[3])/2
    if cy_local > 400:
        print(f"  XATO: Nick LOCAL bbox center Y={cy_local:.1f} — asset 512x512 da PASTDA (512 = pastki chekka)")
        print(f"  SABAB: Fallback box _project_mylogo_box_via_refid CANVAS-space box qaytargani lekin biz uni asset-local space da ishlatmoqdamiz!")
        print(f"  TO'G'RI: Fallback 512x512 asset-local box bo'lishi kerak (0.14 pad markazda)")
    else:
        print(f"  Nick LOCAL center Y={cy_local:.1f} — OK")
