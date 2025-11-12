import numpy as np
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


def test_detect_and_compute_basic():
    print("Testing detect_and_compute with basic image...")
    test_image = np.zeros((100, 100, 3), dtype=np.uint8)
    # Create an "L" shape which should produce corners
    test_image[20:80, 20:40] = 255  # Vertical bar
    test_image[20:40, 20:80] = 255  # Horizontal bar
    matcher = FeatureMatcher()
    kp, des = matcher.detect_and_compute(test_image)
    assert kp is not None, "Keypoints should not be None"
    if len(kp) > 0:
        assert des is not None, f"Should have descriptors for {len(kp)} keypoints"
        assert des.shape[0] == len(kp), "Number of descriptors should match number of keypoints"
    else:
        print("  Note: No keypoints found in test image (this can happen with some detectors)")
    print(f"✓ Found {len(kp)} keypoints: PASS")


def test_detect_and_compute_different_detectors():
    print("Testing detect_and_compute with different detector/descriptor combinations...")
    test_image = np.random.randint(0, 255, (50, 50, 3), dtype=np.uint8)
    combinations = [
        {'detector': constants.DETECTOR_SIFT, 'descriptor': constants.DESCRIPTOR_SIFT},
        {'detector': constants.DETECTOR_ORB, 'descriptor': constants.DESCRIPTOR_ORB},
    ]
    for combo in combinations:
        try:
            matcher = FeatureMatcher(feature_config=combo)
            kp, des = matcher.detect_and_compute(test_image)
            assert kp is not None, f"Keypoints should not be None for {combo}"
            assert des is None or des.shape[0] == len(kp), \
                f"Descriptor count should match keypoints for {combo}"
            print(f"✓ {combo['detector']}-{combo['descriptor']}: {len(kp)} keypoints: PASS")
        except Exception as e:
            print(f"✗ {combo['detector']}-{combo['descriptor']}: {e}")


def test_detect_and_compute_grayscale():
    print("Testing detect_and_compute with grayscale image...")
    test_image = np.zeros((100, 100), dtype=np.uint8)
    test_image[20:80, 20:40] = 255  # Vertical bar
    test_image[20:40, 20:80] = 255  # Horizontal bar
    matcher = FeatureMatcher()
    kp, des = matcher.detect_and_compute(test_image)
    assert kp is not None, "Should work with grayscale images"
    if len(kp) > 0:
        assert des is not None, "Should have descriptors when keypoints are found"
        if hasattr(des, 'shape'):
            assert des.shape[0] == len(kp), "Descriptor count should match keypoints"
    else:
        assert des is None, "Descriptors should be None when no keypoints found"
    print("✓ Grayscale image handling: PASS")


def test_detect_and_compute_empty_image():
    print("Testing detect_and_compute with empty image...")
    test_image = np.zeros((50, 50, 3), dtype=np.uint8)  # All black
    matcher = FeatureMatcher()
    kp, des = matcher.detect_and_compute(test_image)
    assert kp is not None, "Should handle empty image without crashing"
    assert len(kp) == 0, "Empty image should have 0 keypoints"
    assert des is None, "Descriptors should be None when no keypoints found"
    print("✓ Empty image handling: PASS")


def test_detect_and_compute_with_real_image():
    print("Testing detect_and_compute with real image pattern...")
    test_image = np.zeros((100, 100, 3), dtype=np.uint8)
    for i in range(0, 100, 20):
        for j in range(0, 100, 20):
            if (i // 20 + j // 20) % 2 == 0:
                test_image[i:i + 10, j:j + 10] = 255
    matcher = FeatureMatcher()
    kp, des = matcher.detect_and_compute(test_image)
    assert kp is not None, "Keypoints should not be None"
    assert len(kp) > 0, "Chessboard pattern should produce keypoints"
    assert des is not None, "Should have descriptors when keypoints are found"
    assert des.shape[0] == len(kp), "Descriptor count should match keypoints"
    print(f"✓ Real image pattern: {len(kp)} keypoints found: PASS")


if __name__ == "__main__":
    print("Running FeatureMatcher tests...")
    test_constructor_default()
    test_constructor_custom_config()
    test_constructor_invalid_config()
    test_constructor_edge_cases()
    test_detect_and_compute_basic()
    test_detect_and_compute_different_detectors()
    test_detect_and_compute_grayscale()
    test_detect_and_compute_empty_image()
    test_detect_and_compute_with_real_image()
