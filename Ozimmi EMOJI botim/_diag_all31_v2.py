import sys, os, json
sys.path.insert(0, os.path.abspath('.'))

def _get_vec2(ks_obj, key, default):
    raw = ks_obj.get(key, {}).get('k', default)
    # print(f"DEBUG key={key} type(raw)={type(raw).__name__} raw={str(raw)[:80]}")
    if isinstance(raw, dict):
        v = raw.get('k', default)
        if isinstance(v, list) and len(v) and isinstance(v[0], (int,float)):
            return [float(v[0]), float(v[1])]
        if isinstance(v, list) and len(v) and isinstance(v[0], dict):
            vv = v[0].get('s', v[0].get('e', default))
            if isinstance(vv, list) and len(vv) >= 2:
                return [float(vv[0]), float(vv[1])]
        return [float(x) for x in default]
    if isinstance(raw, list) and len(raw) >= 2 and isinstance(raw[0], (int,float)):
        return [float(raw[0]), float(raw[1])]
    return [float(x) for x in default]

folder = 'templates_tgs3'
rows = []
import logo_engine
for fname in sorted(os.listdir(folder)):
    if not fname.endswith('.json'): continue
    path = os.path.join(folder, fname)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except:
        continue

    ref_p = ref_s = ref_a = None
    for layer in data.get('layers', []):
        if layer.get('refId') == 'mylogo':
            ks = layer.get('ks', {})
            ref_p = _get_vec2(ks, 'p', [256,256])
            ref_s = _get_vec2(ks, 's', [100,100])
            ref_a = _get_vec2(ks, 'a', [0,0])
            break

    data_n = logo_engine._normalize_lottie_keys(data)
    lg = logo_engine._find_mylogo_placeholder(data_n)
    bbox = None
    if lg:
        bbox = logo_engine._bbox_of_shape_group(lg)

    ccx = ccy = cw = ch = None
    if bbox and ref_p and ref_s and ref_a:
        sx, sy = float(ref_s[0])/100., float(ref_s[1])/100.
        lcx = (bbox[0]+bbox[2])/2
        lcy = (bbox[1]+bbox[3])/2
        ccx = (lcx - ref_a[0])*sx + ref_p[0]
        ccy = (lcy - ref_a[1])*sy + ref_p[1]
        cw = (bbox[2]-bbox[0])*sx
        ch = (bbox[3]-bbox[1])*sy
    rows.append((fname, ref_p, ref_s, ref_a, bbox, (ccx,ccy,cw,ch)))

with open('_all31_report.txt', 'w', encoding='utf-8') as f:
    f.write(f"{'File':<8} {'ref_p':<18} {'ref_s':<18} {'ref_a':<18} Nick_CANVAS_center size\n")
    f.write("-"*110 + "\n")
    for (fname, rp, rs, ra, bb, c) in rows:
        cc = "None"
        if c[0] is not None:
            cc = f"({c[0]:.0f},{c[1]:.0f}) {c[2]:.0f}x{c[3]:.0f}"
        f.write(f"{fname:<8} {str(rp):<18} {str(rs):<18} {str(ra):<18} {cc}\n")
    f.write("\n=== PROBLEMATIC: Nick at BOTTOM (cy > 350) ===\n")
    for (fname, rp, rs, ra, bb, c) in rows:
        if c and c[1] and c[1] > 350:
            f.write(f"  {fname}: cy={c[1]:.0f} size={c[2]:.0f}x{c[3]:.0f} ref_p={rp} bbox={bb}\n")
    f.write("\n=== PROBLEMATIC: Nick at TOP (cy < 180) ===\n")
    for (fname, rp, rs, ra, bb, c) in rows:
        if c and c[1] and c[1] < 180:
            f.write(f"  {fname}: cy={c[1]:.0f} size={c[2]:.0f}x{c[3]:.0f} ref_p={rp} bbox={bb}\n")
    f.write("\n=== PROBLEMATIC: Nick at RIGHT (cx > 380) ===\n")
    for (fname, rp, rs, ra, bb, c) in rows:
        if c and c[0] and c[0] > 380:
            f.write(f"  {fname}: cx={c[0]:.0f} size={c[2]:.0f}x{c[3]:.0f} ref_p={rp} bbox={bb}\n")
    f.write("\n=== PROBLEMATIC: Nick TOO SMALL (<40px either dim) ===\n")
    for (fname, rp, rs, ra, bb, c) in rows:
        if c and c[2] and (c[2] < 40 or c[3] < 40):
            f.write(f"  {fname}: size={c[2]:.0f}x{c[3]:.0f} ref_s={rs} bbox={bb}\n")

with open('_all31_report.txt', encoding='utf-8') as f:
    print(f.read())
