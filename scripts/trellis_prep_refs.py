"""Prepare reference art views for trellis_project_colour.py. Run with the TRELLIS venv python
(it ships OpenCV + numpy):

  $BLENDER_SKILL_HOME/venvs/trellis/bin/python scripts/trellis_prep_refs.py DIR --prefix kid \
      --front front.png:907 --back back.png:955 [--side side.png:968] \
      [--landmarks-back neck=318,waist=615] [--landmarks-side neck=485,waist=680,hem=800]

Each view is NAME.png:FEET_ROW (the row of the soles; the ground shadow is not part of the figure).
Writes DIR/PREFIX-<view>-filled.png, -mask.png, -extent.png (mask with thin protrusions removed) and DIR/proj-meta.json with, per view: silhouette box, head span,
and landmark rows. Backgrounds are removed from the border inward,
the silhouette is eroded 4 px so anti-aliased fringe is never sampled, and the outside is filled with
the nearest interior colour.
"""
import argparse, json
from pathlib import Path

import cv2
import numpy as np


def figure_mask(im):
    n, lab = cv2.connectedComponents((im.min(axis=2) > 222).astype(np.uint8), connectivity=4)
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    fg = (~np.isin(lab, list(border))).astype(np.uint8)
    fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab2, stats, _ = cv2.connectedComponentsWithStats(fg, connectivity=8)
    fg = (lab2 == 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])).astype(np.uint8)
    return cv2.morphologyEx(fg, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))


def fill_outside(im, fg):
    core = cv2.erode(fg, np.ones((3, 3), np.uint8), iterations=4)
    _, labels = cv2.distanceTransformWithLabels(np.where(core > 0, 0, 255).astype(np.uint8), cv2.DIST_L2, 5,
                                                labelType=cv2.DIST_LABEL_PIXEL)
    lut = np.zeros((labels.max() + 1, 3), np.uint8)
    cy, cx = np.where(core > 0)
    lut[labels[cy, cx]] = im[cy, cx]
    return lut[labels], core


def prep_view(src, feet, dst, head_rows, open_px=41):
    im = cv2.imread(str(src))
    fg = figure_mask(im)
    ys, xs = np.where(fg > 0)
    box = dict(x0=int(xs.min()), x1=int(xs.max()), y0=int(ys.min()), y1=int(feet or ys.max()))
    r1 = int(box["y0"] + head_rows * (box["y1"] - box["y0"]))
    hx = np.where(fg[box["y0"]:r1] > 0)[1]
    box["head_x0"], box["head_x1"] = int(hx.min()), int(hx.max())
    filled, _ = fill_outside(im, fg)
    cv2.imwrite(str(dst), filled)
    cv2.imwrite(str(Path(str(dst).replace('-filled', '-mask'))), fg * 255)
    # extent mask: thin protrusions (hands, ribbons) removed so silhouette registration only follows the body
    ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (open_px, open_px))
    cv2.imwrite(str(Path(str(dst).replace('-filled', '-extent'))), cv2.morphologyEx(fg, cv2.MORPH_OPEN, ker) * 255)
    return box


def parse_view(s):
    path, _, feet = s.partition(":")
    return path, int(feet or 0)


def parse_marks(s):
    return {k: int(v) for k, v in (kv.split("=") for kv in s.split(",") if kv)} if s else {}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("dir"); ap.add_argument("--prefix", default="kid")
    ap.add_argument("--front", required=True); ap.add_argument("--back", required=True); ap.add_argument("--side")
    ap.add_argument("--open-px", type=int, default=41); ap.add_argument("--head-rows", type=float, default=0.42)
    for v in ("front", "back", "side"):
        ap.add_argument(f"--landmarks-{v}", default="")
    a = ap.parse_args()
    d = Path(a.dir)
    meta = {}
    for view in ("front", "back", "side"):
        spec = getattr(a, view)
        if not spec:
            continue
        path, feet = parse_view(spec)
        meta[view] = prep_view(path, feet, d / f"{a.prefix}-{view}-filled.png", a.head_rows,
                               open_px=1 if view == "front" else a.open_px)
        meta[view].update(parse_marks(getattr(a, f"landmarks_{view}")))
    (d / "proj-meta.json").write_text(json.dumps(meta, indent=1))
    print(json.dumps(meta))
