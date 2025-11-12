from shinestacker.config.constants import constants
from shinestacker.algorithms.feature_match import (
    FeatureMatcher, _DEFAULT_FEATURE_CONFIG, _DEFAULT_MATCHING_CONFIG)


def test_constructor_default():
    print("Testing FeatureMatcher constructor with default parameters...")
    matcher = FeatureMatcher()
    assert matcher.feature_config == _DEFAULT_FEATURE_CONFIG
    assert matcher.matching_config == _DEFAULT_MATCHING_CONFIG
    assert matcher.callbacks == {}
    assert matcher.detector is not None
    assert matcher.descriptor is not None
    print("✓ Constructor with default parameters: PASS")


def test_constructor_custom_config():
    print("Testing FeatureMatcher constructor with custom parameters...")
    custom_feature_config = {
        'detector': constants.DETECTOR_SIFT,
        'descriptor': constants.DESCRIPTOR_SIFT
    }
    custom_matching_config = {
        'match_method': constants.MATCHING_KNN,
        'threshold': 0.7
    }

    def dummy_callback(msg):
        print(f"Callback: {msg}")

    callbacks = {'warning': dummy_callback}
    matcher = FeatureMatcher(
        feature_config=custom_feature_config,
        matching_config=custom_matching_config,
        callbacks=callbacks
    )
    assert matcher.feature_config['detector'] == constants.DETECTOR_SIFT
    assert matcher.feature_config['descriptor'] == constants.DESCRIPTOR_SIFT
    assert matcher.matching_config['match_method'] == constants.MATCHING_KNN
    assert matcher.matching_config['threshold'] == 0.7
    assert 'warning' in matcher.callbacks
    assert matcher.detector is not None
    assert matcher.descriptor is not None
    print("✓ Constructor with custom parameters: PASS")


def test_constructor_invalid_config():
    print("Testing FeatureMatcher constructor with invalid configuration...")
    invalid_feature_config = {
        'detector': constants.DETECTOR_SIFT,
        'descriptor': constants.DESCRIPTOR_ORB  # Invalid combo
    }
    try:
        matcher = FeatureMatcher(feature_config=invalid_feature_config)
        assert False, "Should have raised an exception for invalid config"
        assert matcher is not None
    except ValueError as e:
        assert "Detector SIFT requires descriptor SIFT" in str(e)
        print("✓ Constructor with invalid config correctly raised exception: PASS")


def test_constructor_edge_cases():
    print("Testing FeatureMatcher constructor edge cases...")
    matcher = FeatureMatcher(feature_config={}, matching_config={})
    assert matcher.feature_config == _DEFAULT_FEATURE_CONFIG
    assert matcher.matching_config == _DEFAULT_MATCHING_CONFIG
    matcher = FeatureMatcher(feature_config=None, matching_config=None)
    assert matcher.feature_config == _DEFAULT_FEATURE_CONFIG
    assert matcher.matching_config == _DEFAULT_MATCHING_CONFIG
    print("✓ Constructor edge cases: PASS")


if __name__ == "__main__":
    print("Running FeatureMatcher tests...")
    test_constructor_default()
    test_constructor_custom_config()
    test_constructor_invalid_config()
    test_constructor_edge_cases()
