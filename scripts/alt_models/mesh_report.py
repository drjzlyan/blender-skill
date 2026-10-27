"""Mesh statistics for a GLB (run with a python that has trimesh):  mesh_report.py model.glb"""
import json, sys
import numpy as np, trimesh
scene = trimesh.load(sys.argv[1], force="scene")
meshes = [g for g in scene.geometry.values() if isinstance(g, trimesh.Trimesh)]
m = trimesh.util.concatenate(meshes)
uv_islands = None  # filled below: components before welding = UV islands
# components by union-find over shared vertices (cheap; trimesh.split() can balloon on dense meshes)
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
f = m.faces; n = len(m.vertices)
g = coo_matrix((np.ones(len(f) * 2), (np.r_[f[:, 0], f[:, 1]], np.r_[f[:, 1], f[:, 2]])), shape=(n, n))
nc, lab = connected_components(g, directed=False)
sizes = sorted(np.bincount(lab[f[:, 0]], minlength=nc).tolist(), reverse=True)
sizes = [s for s in sizes if s > 0]
uv_islands = len(sizes)
m.merge_vertices(merge_tex=True, merge_norm=True, digits_vertex=5)          # weld seams: now components are true surface pieces
f = m.faces; n = len(m.vertices)
g = coo_matrix((np.ones(len(f) * 2), (np.r_[f[:, 0], f[:, 1]], np.r_[f[:, 1], f[:, 2]])), shape=(n, n))
nc, lab = connected_components(g, directed=False)
sizes = sorted([s for s in np.bincount(lab[f[:, 0]], minlength=nc).tolist() if s > 0], reverse=True)
comps = sizes
ext = m.bounds[1] - m.bounds[0]
tex = None
for g in meshes:
    mat = getattr(g.visual, "material", None)
    img = getattr(mat, "baseColorTexture", None)
    if img is not None:
        tex = list(img.size); break
print(json.dumps({
    "faces": int(len(m.faces)), "verts": int(len(m.vertices)),
    "uv_islands": uv_islands, "components": len(comps), "largest_component_share": round(sizes[0] / max(1, len(m.faces)), 4),
    "small_components_<1%": int(sum(1 for s in sizes if s < 0.01 * len(m.faces))),
    "watertight": bool(m.is_watertight), "bbox_m": [round(float(v), 3) for v in ext],
    "has_uv": bool(getattr(m.visual, "uv", None) is not None), "base_color_texture": tex,
    "file_mb": round(__import__("os").path.getsize(sys.argv[1]) / 2**20, 1),
}))
