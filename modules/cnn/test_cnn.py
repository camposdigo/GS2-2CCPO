import io
import unittest
import numpy as np
from PIL import Image
import torch
from fastapi.testclient import TestClient

from app import app
from model import LandscapeCNN
from train import ROOT, make_split


class CnnTests(unittest.TestCase):
    def test_architectures_produce_ten_logits_and_gradients(self):
        for filters in ((16, 32), (16, 32, 64), (24, 48, 96)):
            network = LandscapeCNN(filters)
            values = network(torch.rand(2, 3, 64, 64))
            self.assertEqual(tuple(values.shape), (2, 10))
            values.sum().backward()
            self.assertIsNotNone(next(network.parameters()).grad)

    def test_invalid_file_rejected_before_inference(self):
        response = TestClient(app).post('/api/classify', files={'file': ('fake.png', b'not a png', 'image/png')})
        self.assertEqual(response.status_code, 422)

    def test_tiny_image_is_rejected(self):
        contents = io.BytesIO()
        Image.new('RGB', (8, 8)).save(contents, format='PNG')
        response = TestClient(app).post('/api/classify', files={'file': ('tiny.png', contents.getvalue(), 'image/png')})
        self.assertEqual(response.status_code, 422)

    def test_oversized_file_rejected(self):
        response = TestClient(app).post('/api/classify', files={'file': ('big.png', b'x' * (5 * 1024 * 1024 + 1), 'image/png')})
        self.assertEqual(response.status_code, 413)

    @unittest.skipUnless((ROOT / 'data/2750').exists(), 'Dataset local necessário')
    def test_split_is_reproducible_and_disjoint(self):
        classes, splits = make_split(ROOT / 'data/2750', 50, 42)
        _, repeat = make_split(ROOT / 'data/2750', 50, 42)
        self.assertEqual(splits, repeat)
        files = [set(path for path, _ in rows) for rows in splits.values()]
        self.assertFalse(files[0] & files[1] or files[0] & files[2] or files[1] & files[2])
        self.assertEqual(len(classes), 10)

    @unittest.skipUnless((ROOT / 'artifacts/manifest.json').exists(), 'Modelo treinado necessário')
    def test_trained_inference_has_all_classes_and_sums_to_one(self):
        sample = next((ROOT / 'data/2750/Forest').glob('*.jpg'), None)
        if sample is None:
            self.skipTest('Dataset local necessário')
        response = TestClient(app).post('/api/classify', files={'file': ('forest.jpg', sample.read_bytes(), 'image/jpeg')})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload['probabilities']), 10)
        self.assertAlmostEqual(sum(item['score'] for item in payload['probabilities']), 1, places=5)
        self.assertTrue(payload['requiresHumanReview'])
        self.assertEqual(payload['confidence']['type'], 'softmax_uncalibrated')


if __name__ == '__main__':
    unittest.main()
