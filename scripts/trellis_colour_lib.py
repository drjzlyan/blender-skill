"""Pure-numpy helpers for colouring generated characters (no bpy, unit-testable).

Reference art never matches a generated mesh exactly (proportions, pose, feature placement). The cure
is to warp each art into a canonical orthographic image registered to the mesh silhouette row by row,
then let the shader sample those images at texture resolution.
"""
from __future__ import annotations

import numpy as np

def smooth1d(a, sigma):
    """Gaussian smoothing with edge padding (sigma in samples)."""
    a = np.asarray(a, dtype=np.float64)
    if sigma <= 0:
        return a
    r = int(3 * sigma) + 1
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2); k /= k.sum()
    return np.convolve(np.pad(a, r, mode="edge"), k, mode="valid")


def mesh_row_extents(coord, zn, bins=400, low_q=0.5, high_q=99.5, min_count=12, sigma=8.0):
    """Per-height-bin extent [lo, hi] of one horizontal mesh coordinate. Returns (zn_centres, lo, hi)."""
    edges = np.linspace(0.0, 1.0, bins + 1)
    idx = np.clip(np.digitize(zn, edges) - 1, 0, bins - 1)
    lo = np.full(bins, np.nan); hi = np.full(bins, np.nan)
    for b in range(bins):
        m = idx == b
        if m.sum() >= min_count:
            lo[b], hi[b] = np.percentile(coord[m], [low_q, high_q])
    centres = (edges[:-1] + edges[1:]) / 2
    ok = ~np.isnan(lo)
    lo = np.interp(centres, centres[ok], lo[ok]); hi = np.interp(centres, centres[ok], hi[ok])
    # median first (kills single-bin spikes), then a Gaussian so rows never shear against each other
    k = 5
    pad = lambda a: np.pad(a, k // 2, mode="edge")
    lo = np.array([np.median(pad(lo)[i:i + k]) for i in range(bins)])
    hi = np.array([np.median(pad(hi)[i:i + k]) for i in range(bins)])
    return centres, smooth1d(lo, sigma), smooth1d(hi, sigma)


def mask_row_extents(mask):
    """Per-row [first, last] foreground column of a figure mask; NaN on empty rows."""
    h = mask.shape[0]
    lo = np.full(h, np.nan); hi = np.full(h, np.nan)
    rows = np.where(mask.any(axis=1))[0]
    for r in rows:
        cols = np.where(mask[r])[0]
        lo[r], hi[r] = cols[0], cols[-1]
    return lo, hi


def canonical_view(art, mask, centres, m_lo, m_hi, art_rows_of_zn, span, out_h=2048, out_w=2048,
                   flip=False, centre=0.0, art_sigma=6.0):
    """Warp reference art into an orthographic canonical image registered to the mesh.

    Output row i is height zn = 1 - i/(out_h-1); output column j is coordinate
    centre + (j/(out_w-1) - 0.5) * span in metres (increasing to the right). For each row the art's
    silhouette extent is stretched onto the mesh's extent, so features land on the right surface
    even when the art's proportions differ from the generated mesh. flip mirrors the art (a back view).
    """
    ah, aw = art.shape[:2]
    a_lo, a_hi = mask_row_extents(mask)
    good = ~np.isnan(a_lo)
    rr = np.arange(ah)
    a_lo = np.interp(rr, rr[good], a_lo[good]); a_hi = np.interp(rr, rr[good], a_hi[good])
    a_lo = smooth1d(a_lo, art_sigma); a_hi = smooth1d(a_hi, art_sigma)
    zn = 1.0 - np.arange(out_h) / (out_h - 1)
    rows = np.clip(art_rows_of_zn(zn), 0, ah - 1)
    r0 = np.floor(rows).astype(int); r1 = np.minimum(r0 + 1, ah - 1); fr = rows - r0
    lo_a = a_lo[r0] * (1 - fr) + a_lo[r1] * fr
    hi_a = a_hi[r0] * (1 - fr) + a_hi[r1] * fr
    lo_m = np.interp(zn, centres, m_lo); hi_m = np.interp(zn, centres, m_hi)
    coord = centre + (np.arange(out_w) / (out_w - 1) - 0.5) * span
    t = (coord[None, :] - lo_m[:, None]) / np.maximum(hi_m - lo_m, 1e-4)[:, None]
    if flip:
        t = 1.0 - t
    cols = lo_a[:, None] + t * np.maximum(hi_a - lo_a, 1.0)[:, None]
    cols = np.clip(cols, 0, aw - 1)
    c0 = np.floor(cols).astype(int); c1 = np.minimum(c0 + 1, aw - 1); fc = (cols - c0)[..., None]
    ri = np.clip(np.rint(rows).astype(int), 0, ah - 1)[:, None]
    out = art[ri, c0] * (1 - fc) + art[ri, c1] * fc
    return out.astype(np.float32)
