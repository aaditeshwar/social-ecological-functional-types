"""Compact polygon encoding shared by the pipeline and the web viewer.

A geometry is a '|' separated list of rings. Each ring is a comma-separated list of integer
deltas of round(coord * 1e4), starting from (0, 0), so the first pair is absolute lon, lat.
"""
from shapely.geometry import Polygon, MultiPolygon, shape
from shapely.ops import unary_union

def decode(s):
    rings = []
    for part in s.split('|'):
        if not part: continue
        v = [int(x) for x in part.split(',')]
        x = y = 0; ring = []
        for i in range(0, len(v) - 1, 2):
            x += v[i]; y += v[i + 1]; ring.append((x / 1e4, y / 1e4))
        rings.append(ring)
    return rings

def encode_geom(g, tol=0.0):
    if tol: g = g.simplify(tol, preserve_topology=True)
    polys = [g] if isinstance(g, Polygon) else list(getattr(g, 'geoms', []))
    out = []
    for p in polys:
        if p.is_empty or not isinstance(p, Polygon): continue
        coords = list(p.exterior.coords)
        if len(coords) < 4: continue
        x0 = y0 = 0; v = []
        for x, y in coords:
            X, Y = round(x * 1e4), round(y * 1e4)
            v += [X - x0, Y - y0]; x0, y0 = X, Y
        out.append(','.join(map(str, v)))
    return '|'.join(out)

def to_shape(s):
    polys = [Polygon(r) for r in decode(s) if len(r) >= 4]
    polys = [p if p.is_valid else p.buffer(0) for p in polys]
    return unary_union(polys) if polys else None
