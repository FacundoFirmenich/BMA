import math
import unittest

from rmk_timber_model_v0_1 import (
    CommonSupportWeights,
    LocalOutcomeState,
    NotEstimable,
    StudentTPredictive,
    canonical_phase,
    convolved_logpdf,
    m0_predictive,
    m1_predictive,
)


class RmkTimberModelTests(unittest.TestCase):
    def test_m1_requires_three_prior_observations(self):
        with self.assertRaises(NotEstimable):
            m1_predictive([50.0, 51.0])
        prediction = m1_predictive([50.0, 51.0, 49.0])
        self.assertEqual(prediction.degrees_of_freedom, 2)
        self.assertGreater(prediction.scale, 0.0)

    def test_m0_density_requires_three_transitions(self):
        with self.assertRaises(NotEstimable):
            m0_predictive([50.0, 51.0, 49.0])
        self.assertEqual(m0_predictive([50.0, 51.0, 49.0, 52.0]).degrees_of_freedom, 2)

    def test_phase_is_exact_month_set(self):
        self.assertEqual(canonical_phase([8, 6, 7, 6]), "M06-M07-M08")

    def test_update_never_uses_current_outcome_in_its_own_prediction(self):
        state = LocalOutcomeState()
        phase = canonical_phase([6, 7, 8])
        for value in [50.0, 52.0, 49.0]:
            state.update_after_adjudication(phase, value)
        frozen = state.freeze_predictions(phase)
        expected = math.exp(sum(math.log(v) for v in [50.0, 52.0, 49.0]) / 3.0)
        self.assertAlmostEqual(frozen["M1"]["point"], expected)
        self.assertEqual(frozen["M2"]["phase_support"], 0)

    def test_m2_support_uses_only_prior_m1_innovations_same_phase(self):
        state = LocalOutcomeState()
        summer = canonical_phase([6, 7, 8])
        winter = canonical_phase([12, 1, 2])
        for phase, value in [(summer, 50), (summer, 52), (summer, 49), (winter, 60), (summer, 58)]:
            state.update_after_adjudication(phase, value)
        frozen = state.freeze_predictions(summer)
        self.assertEqual(frozen["M2"]["phase_support"], 1)
        self.assertTrue(str(frozen["M2"]["state"]).startswith("NOT_ESTIMABLE_"))

    def test_cauchy_convolution_matches_known_sum(self):
        first = StudentTPredictive(1.0, 2.0, 1)
        second = StudentTPredictive(3.0, 4.0, 1)
        observed = convolved_logpdf(first, second, 4.0)
        expected = -math.log(math.pi * 6.0)
        self.assertAlmostEqual(observed, expected, places=6)

    def test_weights_do_not_exist_before_common_support(self):
        weights = CommonSupportWeights()
        self.assertIsNone(weights.probabilities())
        weights.update_after_common_adjudication({"M0": -1.0, "M1": -2.0, "M2": -3.0})
        self.assertAlmostEqual(sum(weights.probabilities().values()), 1.0)
        self.assertEqual(weights.common_support_events, 1)


if __name__ == "__main__":
    unittest.main()
