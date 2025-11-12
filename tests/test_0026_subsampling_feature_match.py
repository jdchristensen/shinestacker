import cv2
import numpy as np
from shinestacker.algorithms.feature_match import (
    SubsamplingFeatureMatcher, DEFAULT_FEATURE_CONFIG)


def create_test_images():
    img1 = np.zeros((400, 400, 3), dtype=np.uint8)
    img2 = np.zeros((400, 400, 3), dtype=np.uint8)
    cv2.rectangle(img1, (100, 100), (150, 150), (255, 255, 255), -1)
    cv2.rectangle(img2, (120, 120), (170, 170), (255, 255, 255), -1)  # Translated
    cv2.circle(img1, (300, 300), 25, (200, 200, 200), -1)
    cv2.circle(img2, (315, 315), 25, (200, 200, 200), -1)  # Translated
    return img1, img2


def test_basic_matching():
    print("Testing basic feature matching...")
    img1, img2 = create_test_images()
    matcher = SubsamplingFeatureMatcher()
    result = matcher.match_images(img1, img2)
    print(f"Number of good matches: {result.n_good_matches()}")
    print(f"Has sufficient matches (min=4): {result.has_sufficient_matches(4)}")
    if result.n_good_matches() > 0:
        src_pts = result.get_src_points()
        dst_pts = result.get_dst_points()
        print(f"Source points shape: {src_pts.shape}")
        print(f"Target points shape: {dst_pts.shape}")
        transform, _ = cv2.estimateAffinePartial2D(src_pts, dst_pts)
        if transform is not None:
            print(f"Estimated translation: dx={transform[0, 2]:.1f}, dy={transform[1, 2]:.1f}")


def test_subsampling():
    print("\nTesting subsampling...")
    img1, img2 = create_test_images()
    matcher = SubsamplingFeatureMatcher()
    for subsample in [1, 2, 4]:
        result = matcher.match_images(img1, img2, subsample=subsample)
        print(f"Subsample {subsample}: {result.n_good_matches()} matches")


def test_fast_subsampling():
    print("\nTesting fast subsampling...")
    img1, img2 = create_test_images()
    matcher = SubsamplingFeatureMatcher()
    result_normal = matcher.match_images(img1, img2, subsample=4, fast_subsampling=False)
    result_fast = matcher.match_images(img1, img2, subsample=4, fast_subsampling=True)
    print(f"Normal subsampling: {result_normal.n_good_matches()} matches")
    print(f"Fast subsampling: {result_fast.n_good_matches()} matches")


def test_different_detectors():
    print("\nTesting different detectors...")
    img1, img2 = create_test_images()
    detectors = ['SIFT', 'ORB', 'AKAZE']
    for detector in detectors:
        try:
            config = DEFAULT_FEATURE_CONFIG.copy()
            config['detector'] = detector
            config['descriptor'] = detector
            matcher = SubsamplingFeatureMatcher(feature_config=config)
            result = matcher.match_images(img1, img2)
            print(f"{detector}: {result.n_good_matches()} matches")
        except Exception as e:
            print(f"{detector}: Failed - {e}")


def test_no_features():
    print("\nTesting with featureless images...")
    img1 = np.zeros((200, 200, 3), dtype=np.uint8)
    img2 = np.zeros((200, 200, 3), dtype=np.uint8)
    matcher = SubsamplingFeatureMatcher()
    result = matcher.match_images(img1, img2)
    print(f"Featureless images: {result.n_good_matches()} matches")
    print(f"Has sufficient matches (min=1): {result.has_sufficient_matches(1)}")


if __name__ == "__main__":
    test_basic_matching()
    test_subsampling()
    test_fast_subsampling()
    test_different_detectors()
    test_no_features()
