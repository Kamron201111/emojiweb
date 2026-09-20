import sys, os, json
sys.path.insert(0, os.path.abspath('.'))
import logo_engine

def _get_vec2(ks_obj, key, default):
    raw = ks_obj.get(key, {}).get('k', default)
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

for folder in ['templates_tgs2']:
    print(f"\n=== {folder} 5 ta sample ===")
    samples = sorted([f for f in os.listdir(folder) if f.endswith('.json')])[:5]
    for fname in samples:
        path = os.path.join(folder, fname)
        with open(path, 'r', encoding='utf-8') as f: data = json.load(f)
        data_n = logo_engine._normalize_lottie_keys(data)

        # Collect shape lists like in build_tgs_sticker
        all_shape_lists = []
        for layer in data_n.get('layers', []):
            if layer.get('shapes'): all_shape_lists.append(layer['shapes'])
        for asset in data_n.get('assets', []):
            if asset.get('id') == 'mylogo': continue
            for layer in asset.get('layers', []) or []:
                if layer.get('shapes'): all_shape_lists.append(layer['shapes'])
        for asset in data_n.get('assets', []):
            if asset.get('id') != 'mylogo': continue
            for layer in asset.get('layers', []) or []:
                if layer.get('shapes'): all_shape_lists.append(layer['shapes'])

        logo_group = None
        for shapes in all_shape_lists:
            logo_group = logo_engine._find_logo_group(shapes)
            if logo_group: break
        if logo_group is None:
            logo_group = logo_engine._find_mylogo_placeholder(data_n)

        ref_p = ref_s = ref_a = [256.,256.]
        for layer in data_n.get('layers', []):
            if layer.get('refId') == 'mylogo':
                ks = layer.get('ks', {})
                ref_p = _get_vec2(ks, 'p', [256,256])
                ref_s = _get_vec2(ks, 's', [100,100])
                ref_a = _get_vec2(ks, 'a', [0,0])
                break

        bbox = logo_engine._bbox_of_shape_group(logo_group) if logo_group else None
        if bbox:
            sx, sy = ref_s[0]/100., ref_s[1]/100.
            lcx = (bbox[0]+bbox[2])/2; lcy = (bbox[1]+bbox[3])/2
            ccx = (lcx - ref_a[0])*sx + ref_p[0]
            ccy = (lcy - ref_a[1])*sy + ref_p[1]
            cw = (bbox[2]-bbox[0])*sx; ch = (bbox[3]-bbox[1])*sy
            print(f"  {fname}: bbox_center=({lcx:.0f},{lcy:.0f})  bbox={bbox}")
            print(f"         ref_p={ref_p} ref_s={ref_s} ref_a={ref_a}")
            print(f"         CANVAS_center=({ccx:.0f},{ccy:.0f})  size={cw:.0f}x{ch:.0f}")
        else:
            print(f"  {fname}: NO LOGO GROUP FOUND")
