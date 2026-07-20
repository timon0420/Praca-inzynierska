import unittest
from types import SimpleNamespace

from app.hand_position import HandPositionCalculator


class HandPositionCalculatorTests(unittest.TestCase):
    def setUp(self):
        self.calculator = HandPositionCalculator()
        self.landmarks = [SimpleNamespace(x=0.5, y=0.5, z=0.0) for _ in range(21)]
        self.landmarks[0] = SimpleNamespace(x=0.5, y=0.8, z=0.0)
        self.landmarks[5] = SimpleNamespace(x=0.35, y=0.45, z=0.0)
        self.landmarks[9] = SimpleNamespace(x=0.5, y=0.35, z=0.0)
        self.landmarks[13] = SimpleNamespace(x=0.6, y=0.45, z=0.0)
        self.landmarks[17] = SimpleNamespace(x=0.7, y=0.5, z=0.0)

    def test_center_is_average_of_palm_landmarks(self):
        result = self.calculator.calculate_position(self.landmarks, 1000, 500)
        expected_x = (500 + 350 + 500 + 600 + 700) / 5
        expected_y = (400 + 225 + 175 + 225 + 250) / 5
        self.assertAlmostEqual(result.center_pixels[0], expected_x)
        self.assertAlmostEqual(result.center_pixels[1], expected_y)
        self.assertAlmostEqual(result.center_pixels[2], 0.0)

    def test_relative_coordinates_use_palm_center(self):
        result = self.calculator.calculate_position(self.landmarks, 1000, 500)
        for axis in range(3):
            mean = sum(result.relative_landmarks[i][axis]
                       for i in self.calculator.PALM_INDICES) / 5
            self.assertAlmostEqual(mean, 0.0)

    def test_angles_always_stay_in_unity_range(self):
        result = self.calculator.calculate_position(self.landmarks, 1000, 500)
        angles = self.calculator.pixels_to_angles(result, 1000, 500)
        self.assertEqual(len(angles), 6)
        self.assertTrue(all(0.0 <= angle <= 180.0 for angle in angles))

    def test_mapping_clamps_values(self):
        self.assertEqual(self.calculator._map_to_angle(-10, 0, 1), 0.0)
        self.assertEqual(self.calculator._map_to_angle(10, 0, 1), 180.0)

    def test_invalid_landmark_count_is_rejected(self):
        with self.assertRaises(ValueError):
            self.calculator.calculate_position(self.landmarks[:5], 100, 100)


if __name__ == "__main__":
    unittest.main()
