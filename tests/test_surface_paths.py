import unittest
import numpy as np
import pandas as pd
from surface_paths import surface_path

class SurfacePathTests(unittest.TestCase):
    def test_periodic_wrap_is_not_a_material_edge(self):
        frame=pd.DataFrame([[-250,25,1],[250,25,2],[250,25,3],[-250,.07,4],[-225,.07,4]],columns=['x_A','z_A','cell_id'])
        original=frame.copy(deep=True);path,audit=surface_path(frame)
        self.assertEqual(np.isnan(path[:,0]).sum(),2)
        self.assertEqual(audit.break_reason.tolist(),['','opposite_boundary_jump','','opposite_boundary_jump',''])
        pd.testing.assert_frame_equal(frame,original)
        np.testing.assert_array_equal(path[np.isfinite(path[:,0])],frame[['x_A','z_A']].to_numpy())

    def test_vertical_faces_reentrant_edges_and_full_width_single_cell(self):
        frame=pd.DataFrame([[-10,0,1],[10,0,1],[10,5,1],[5,5,2],[5,10,2]],columns=['x_A','z_A','cell_id'])
        path,audit=surface_path(frame)
        self.assertFalse(np.isnan(path).any());self.assertFalse((audit.break_reason!='').any())

    def test_diagonal_jump_breaks_without_smoothing(self):
        frame=pd.DataFrame([[0,0,1],[2,3,2],[2,6,2],[4,6,2]],columns=['x_A','z_A','cell_id'])
        path,audit=surface_path(frame)
        self.assertEqual(audit.break_reason.iloc[1],'non_axis_aligned_jump')
        self.assertTrue(np.isnan(path[1]).all())
