import os
from unittest import TestCase

import numpy as np
from sklearn.neural_network import MLPClassifier, MLPRegressor

import pandas_ml_quant
from pandas_ml_common import naive_splitter
from pandas_ml_utils import FeaturesAndLabels, SkModel
from pandas_ml_utils.constants import PREDICTION_COLUMN_NAME
from pandas_ml_utils import RegressionSummary, FittingParameter
from test.config import DF_TEST

print(pandas_ml_quant.__version__)
os.environ["CUDA_VISIBLE_DEVICES"] = ""


class TestModel(TestCase):

    def test_simple_regression_model(self):
        df = DF_TEST.copy()

        fit = df.model.fit(
            SkModel(
                MLPRegressor(activation='tanh', hidden_layer_sizes=(60, 50), random_state=42, max_iter=2),
                FeaturesAndLabels(
                    features=[
                        lambda df: df["Close"].ta.rsi().ta.rnn(28),
                        lambda df: (df["Volume"] / df["Volume"].ta.ema(14) - 1).ta.rnn(28)
                    ],
                    labels=[
                        lambda df: (df["Close"] / df["Open"] - 1).shift(-1),
                    ]
                ),
                summary_provider=RegressionSummary
            ),
            FittingParameter()
        )

        print(fit)
        html = fit._repr_html_()

        prediction = df.model.predict(fit.model)
        print(prediction)
        self.assertIsInstance(prediction[PREDICTION_COLUMN_NAME, 0].iloc[-1], (float, np.float, np.float32, np.float64))

        backtest = df.model.backtest(fit.model)


    def test_simple_classification_model(self):
        df = DF_TEST.copy()

        fit = df.model.fit(
            SkModel(
                MLPClassifier(activation='tanh', hidden_layer_sizes=(60, 50), random_state=42, max_iter=2),
                FeaturesAndLabels(
                    features=[
                        lambda df: df["Close"].ta.rsi().ta.rnn(28),
                        lambda df: (df["Volume"] / df["Volume"].ta.ema(14) - 1).ta.rnn(28)
                    ],
                    labels=[
                        lambda df: (df["Close"] > df["Open"]).shift(-1),
                    ]
                ),
                # kwargs
                forecasting_time_steps=7
            )
        )

        print(fit)
        html = fit._repr_html_()

        prediction = df.model.predict(fit.model)
        print(prediction)
        self.assertIsInstance(prediction[PREDICTION_COLUMN_NAME, 0].iloc[-1], (float, np.float, np.float32, np.float64))

        backtest = df.model.backtest(fit.model)

        # test multiple samples
        samples = df.model.predict(fit.model, samples=2)
        self.assertIsInstance(samples[PREDICTION_COLUMN_NAME, 0].iloc[-1], list)
        self.assertEqual(2, len(samples[PREDICTION_COLUMN_NAME, 0].iloc[-1]))

    # FIXME implement functionality such that test passes
    def _test_hyper_parameter_for_simple_model(self):
        from hyperopt import hp

        """given"""
        df = DF_TEST.copy()
        df['label'] = df["spy_Close"] > df["spy_Open"]

        """when fit with find hyper parameter"""
        fit = df.fit(
            SkModel(MLPClassifier(activation='tanh', hidden_layer_sizes=(60, 50), random_state=42),
                    FeaturesAndLabels(features=['vix_Close'], labels=['label'],
                                      target_columns=["vix_Open"],
                                      loss_column="spy_Volume")),
            test_size=0.4,
            test_validate_split_seed=42,
            hyper_parameter_space={'alpha': hp.choice('alpha', [0.0001, 10]), 'early_stopping': True, 'max_iter': 50,
                                   '__max_evals': 4, '__rstate': np.random.RandomState(42)}
        )

        """then test best parameter"""
        self.assertEqual(fit.model.sk_model.get_params()['alpha'], 0.0001)
