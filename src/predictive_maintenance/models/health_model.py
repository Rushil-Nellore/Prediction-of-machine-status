from __future__ import annotations

import math
from dataclasses import dataclass


def sigmoid(value: float) -> float:
    if value >= 0:
        exp_term = math.exp(-value)
        return 1 / (1 + exp_term)
    exp_term = math.exp(value)
    return exp_term / (1 + exp_term)


@dataclass
class LogisticRegressionModel:
    weights: list[float]
    bias: float
    learning_rate: float = 0.05
    epochs: int = 800
    regularization: float = 0.0005

    def predict_probability(self, features: list[float]) -> float:
        score = self.bias
        for weight, value in zip(self.weights, features):
            score += weight * value
        return sigmoid(score)

    def train(self, x_rows: list[list[float]], y_rows: list[int]) -> None:
        if not x_rows:
            raise ValueError("No training data provided")

        sample_count = len(x_rows)
        feature_count = len(x_rows[0])
        self.weights = self.weights or [0.0] * feature_count

        for _ in range(self.epochs):
            grad_w = [0.0] * feature_count
            grad_b = 0.0
            for features, label in zip(x_rows, y_rows):
                prediction = self.predict_probability(features)
                error = prediction - label
                for index, value in enumerate(features):
                    grad_w[index] += error * value
                grad_b += error

            for index in range(feature_count):
                grad_w[index] = (grad_w[index] / sample_count) + self.regularization * self.weights[index]
                self.weights[index] -= self.learning_rate * grad_w[index]
            self.bias -= self.learning_rate * (grad_b / sample_count)

