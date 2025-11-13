import cv2
import numpy as np
from shinestacker.algorithms.feature_match import (
    SubsamplingFeatureMatcher, DEFAULT_FEATURE_CONFIG, DEFAULT_MATCHING_CONFIG,
    DEFAULT_ALIGNMENT_CONFIG)


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
    matcher = SubsamplingFeatureMatcher(
        DEFAULT_FEATURE_CONFIG, DEFAULT_MATCHING_CONFIG, DEFAULT_ALIGNMENT_CONFIG)
    result, final_subsample = matcher.match_images_with_fallback(img1, img2)
    print(f"Number of good matches: {result.n_good_matches()}")
    print(f"Final subsample used: {final_subsample}")
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
    matcher = SubsamplingFeatureMatcher(
        DEFAULT_FEATURE_CONFIG, DEFAULT_MATCHING_CONFIG, DEFAULT_ALIGNMENT_CONFIG)
    for subsample in [1, 2, 4]:
        result, final_subsample = matcher.match_images_with_fallback(
            img1, img2, subsample=subsample)
        print(f"Requested subsample {subsample}: "
              f"{result.n_good_matches()} matches, final subsample: {final_subsample}")
        img_ref_sub, img_0_sub = matcher.get_last_subsampled_images()
        print(f"  Subsampled image shapes: {img_ref_sub.shape}, {img_0_sub.shape}")


def test_fallback_behavior():
    print("\nTesting fallback behavior...")
    img1, img2 = create_test_images()
    alignment_config = DEFAULT_ALIGNMENT_CONFIG.copy()
    alignment_config['min_good_matches'] = 1000  # Impossible to reach
    matcher = SubsamplingFeatureMatcher(
        DEFAULT_FEATURE_CONFIG, DEFAULT_MATCHING_CONFIG, alignment_config)
    result, final_subsample = matcher.match_images_with_fallback(
        img1, img2, subsample=4,
        warning_callback=lambda msg: print(f"  Fallback warning: {msg}"))
    print(f"After fallback: {result.n_good_matches()} matches, final subsample: {final_subsample}")
    print(f"Expected fallback to 1: {final_subsample == 1}")


def test_different_detectors():
    print("\nTesting different detectors...")
    img1, img2 = create_test_images()
    detectors = ['SIFT', 'ORB', 'AKAZE']
    for detector in detectors:
        try:
            config = DEFAULT_FEATURE_CONFIG.copy()
            config['detector'] = detector
            config['descriptor'] = detector
            matcher = SubsamplingFeatureMatcher(
                config, DEFAULT_MATCHING_CONFIG, DEFAULT_ALIGNMENT_CONFIG)
            result, final_subsample = matcher.match_images_with_fallback(img1, img2)
            print(f"{detector}: {result.n_good_matches()} matches, subsample: {final_subsample}")
        except Exception as e:
            print(f"{detector}: Failed - {e}")


def test_no_features():
    print("\nTesting with featureless images...")
    img1 = np.zeros((200, 200, 3), dtype=np.uint8)
    img2 = np.zeros((200, 200, 3), dtype=np.uint8)
    matcher = SubsamplingFeatureMatcher(
        DEFAULT_FEATURE_CONFIG, DEFAULT_MATCHING_CONFIG, DEFAULT_ALIGNMENT_CONFIG)
    result, final_subsample = matcher.match_images_with_fallback(img1, img2)
    print(f"Featureless images: {result.n_good_matches()} matches")
    print(f"Has sufficient matches (min=1): {result.has_sufficient_matches(1)}")
    print(f"Final subsample: {final_subsample}")


def test_coordinate_consistency():
    print("\nTesting coordinate consistency...")
    img1, img2 = create_test_images()
    matcher = SubsamplingFeatureMatcher(
        DEFAULT_FEATURE_CONFIG, DEFAULT_MATCHING_CONFIG, DEFAULT_ALIGNMENT_CONFIG)
    for subsample in [1, 2, 4]:
        result, final_subsample = matcher.match_images_with_fallback(
            img1, img2, subsample=subsample)
        if result.n_good_matches() > 0:
            src_pts = result.get_src_points()
            max_coord = max(src_pts.flatten()) if len(src_pts) > 0 else 0
            print(f"Subsample {subsample}: max coordinate = {max_coord:.1f}")
            if subsample > 1:
                print(f"  Coordinates scaled to original image space: {max_coord <= 400}")


if __name__ == "__main__":
    test_basic_matching()
    test_subsampling()
    test_fallback_behavior()
    test_different_detectors()
    test_no_features()
    test_coordinate_consistency()
