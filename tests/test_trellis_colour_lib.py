import sys, unittest
from pathlib import Path

try:
    import numpy as np
except ImportError:  # system python without numpy: run with the TRELLIS venv python
    np = None

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


@unittest.skipIf(np is None, "numpy not available; run with the TRELLIS venv python")
class ColourLibTests(unittest.TestCase):
    def setUp(self):
        import trellis_colour_lib as lib
        self.lib = lib

    def test_canonical_view_registers_art_to_mesh_extents(self):
        # art: 100x200 figure, left half red / right half blue, drawn narrower than the mesh
        art = np.zeros((100, 200, 3), np.float32); art[:, :100, 0] = 1; art[:, 100:, 2] = 1
        mask = np.zeros((100, 200), bool); mask[:, 50:150] = True
        zn = np.linspace(0, 1, 100); coord = np.concatenate([np.full(100, -0.20), np.full(100, 0.20)])
        zz = np.concatenate([zn, zn])
        centres, lo, hi = self.lib.mesh_row_extents(coord, zz, bins=20, min_count=2)
        view = self.lib.canonical_view(art, mask, centres, lo, hi, lambda z: (1 - z) * 99, span=0.8, out_h=40, out_w=80)
        row = view[20]
        self.assertGreater(row[25, 0], 0.5)      # coordinate -0.2.. left of centre: red
        self.assertGreater(row[55, 2], 0.5)      # right of centre: blue
        self.assertLess(row[5, 0] + row[5, 2], 1.1)  # outside the figure extent is just clamped art edge, not garbage

    def test_flip_mirrors_a_back_view(self):
        art = np.zeros((20, 40, 3), np.float32); art[:, :20, 0] = 1; art[:, 20:, 2] = 1
        mask = np.ones((20, 40), bool)
        zn = np.linspace(0, 1, 50); coord = np.tile([-0.2, 0.2], 25); zz = np.repeat(zn[:25], 2)
        centres, lo, hi = self.lib.mesh_row_extents(coord, zz, bins=10, min_count=2)
        v = self.lib.canonical_view(art, mask, centres, lo, hi, lambda z: (1 - z) * 19, span=0.8, out_h=10, out_w=40, flip=True)
        self.assertGreater(v[5, 12, 2], 0.5)     # mirrored: blue now on the left
        self.assertGreater(v[5, 28, 0], 0.5)

    def test_extents_are_smooth_so_rows_cannot_shear(self):
        rng = np.random.RandomState(3)
        zn = rng.rand(20000); coord = rng.randn(20000) * 0.05 + np.where(rng.rand(20000) > 0.5, 0.2, -0.2)
        _, lo, hi = self.lib.mesh_row_extents(coord, zn, bins=200, sigma=8.0)
        self.assertLess(np.abs(np.diff(lo)).max(), 0.02)
        self.assertLess(np.abs(np.diff(hi)).max(), 0.02)

    def test_smooth1d_preserves_constants_and_reduces_noise(self):
        c = self.lib.smooth1d(np.full(50, 3.0), 4)
        self.assertTrue(np.allclose(c, 3.0))
        n = np.random.RandomState(0).randn(200)
        self.assertLess(self.lib.smooth1d(n, 5).std(), n.std() * 0.4)


if __name__ == "__main__":
    unittest.main()
