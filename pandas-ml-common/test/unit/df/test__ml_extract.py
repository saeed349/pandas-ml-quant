from unittest import TestCase

from test.config import TEST_DF


class TestMLExtraction(TestCase):

    def test__mock_features_and_labels(self):
        df = TEST_DF.copy()

        self.assertEqual(len(df.ml.extract(lambda df: df["Close"])), len(df))

