import sys, os, json
sys.path.insert(0, os.path.abspath('.'))

folder = 'templates_tgs3'
rows = []
for fname in sorted(os.listdir(folder)):
    if not fname.endswith('.json'): continue
    path = os.path.join(folder, fname)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except:
        continue

    # refId layer
    ref_p = ref_s = ref_a = None
    for layer in data.get('layers', []):
        if layer.get('refId') == 'mylogo':
            ks = layer.get('ks', {})
            ref_p = ks.get('p', {}).get('k', [None, None])[:2]
            ref_s = ks.get('s', {}).get('k', [None, None])[:2]
            ref_a = ks.get('a', {}).get('k', [None, None])[:2]
            break

    # mylogo bbox
    import logo_engine
    data_n = logo_engine._normalize_lottie_keys(data)
    lg = logo_engine._find_mylogo_placeholder(data_n)
    bbox = None
    if lg:
        bbox = logo_engine._bbox_of_shape_group(lg)

    # Compute nick canvas center with placeholder bbox
    if bbox and ref_p and ref_s and ref_a:
        sx, sy = ref_s[0]/100., ref_s[1]/100.
        lcx = (bbox[0]+bbox[2])/2
        lcy = (bbox[1]+bbox[3])/2
        ccx = (lcx - ref_a[0])*sx + ref_p[0]
        ccy = (lcy - ref_a[1])*sy + ref_p[1]
        # size
        cw = (bbox[2]-bbox[0])*sx
        ch = (bbox[3]-bbox[1])*sy
    else:
        ccx = ccy = cw = ch = None

    rows.append((fname, ref_p, ref_s, ref_a, bbox, (ccx,ccy,cw,ch)))

# Print table
print(f"{'File':<8} {'ref_p':<16} {'ref_s':<16} {'ref_a':<16} {'placeholder_bbox':<36} {'NICK CANVAS center, size':<28}")
print("-"*140)
for (fname, rp, rs, ra, bb, c) in rows:
    print(f"{fname:<8} {str(rp):<16} {str(rs):<16} {str(ra):<16} {str(bb):<36} center=({c[0]:.0f},{c[1]:.0f}) {c[2]:.0f}x{c[3]:.0f}")

# HIGH PROBLEM: nick very low on canvas? (cy > ~350) or canvas y > 400?
print("\n=== PROBLEMATIC: Nick at BOTTOM of canvas (canvas_cy > 350) ===")
for (fname, rp, rs, ra, bb, c) in rows:
    if c and c[1] > 350:
        print(f"  {fname}: canvas_cy={c[1]:.0f} size={c[2]:.0f}x{c[3]:.0f} ref_p={rp} ref_s={rs} bbox={bb}")

print("\n=== PROBLEMATIC: Nick at RIGHT (canvas_cx > 350) ===")
for (fname, rp, rs, ra, bb, c) in rows:
    if c and c[0] > 350:
        print(f"  {fname}: canvas_cx={c[0]:.0f} size={c[2]:.0f}x{c[3]:.0f} ref_p={rp} ref_s={rs} bbox={bb}")

print("\n=== PROBLEMATIC: Nick at TOP-LEFT corner (cx<200 AND cy<200 and small size) ===")
for (fname, rp, rs, ra, bb, c) in rows:
    if c and c[0] < 200 and c[1] < 200 and c[2] < 80:
        print(f"  {fname}: center=({c[0]:.0f},{c[1]:.0f}) size={c[2]:.0f}x{c[3]:.0f} — TOO SMALL, NOT CENTER, maybe refId transform problem!")
