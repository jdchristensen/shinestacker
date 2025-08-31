import os
import cv2
import numpy as np
from shinestacker.algorithms.utils import bgr_to_hsv, hsv_to_bgr, bgr_to_hls, hls_to_bgr, bgr_to_lab, lab_to_bgr


def test_hsv_conversion():
    height, width = 100, 100    
    x = np.linspace(0, 65535, width, dtype=np.uint16)
    y = np.linspace(0, 65535, height, dtype=np.uint16)
    xx, yy = np.meshgrid(x, y)    
    red_channel = xx
    green_channel = yy
    blue_channel = 65535 - xx
    test_bgr = cv2.merge([blue_channel, green_channel, red_channel])    
    hsv = bgr_to_hsv(test_bgr)
    reconstructed = hsv_to_bgr(hsv)    
    diff = cv2.absdiff(test_bgr, reconstructed)
    print(f"Max difference: {np.max(diff)}")
    print(f"Mean difference: {np.mean(diff)}")
    # cv2.imwrite("original.tif", test_bgr)
    # cv2.imwrite("hsv.tif", hsv)
    # cv2.imwrite("reconstructed.tif", reconstructed)
    assert np.max(diff) < 10
    assert np.mean(diff) < 2

def test_hls_conversion():
    height, width = 100, 100    
    x = np.linspace(0, 65535, width, dtype=np.uint16)
    y = np.linspace(0, 65535, height, dtype=np.uint16)
    xx, yy = np.meshgrid(x, y)    
    red_channel = xx
    green_channel = yy
    blue_channel = 65535 - xx
    test_bgr = cv2.merge([blue_channel, green_channel, red_channel])    
    hls = bgr_to_hls(test_bgr)
    reconstructed = hls_to_bgr(hls)    
    diff = cv2.absdiff(test_bgr, reconstructed)
    print(f"HLS Max difference: {np.max(diff)}")
    print(f"HLS Mean difference: {np.mean(diff)}")    
    # cv2.imwrite("original_hls.tif", test_bgr)
    # cv2.imwrite("hls.tif", hls)
    #cv2.imwrite("reconstructed_hls.tif", reconstructed)
    assert np.max(diff) < 10
    assert np.mean(diff) < 2

def test_lab_conversion():
    height, width = 100, 100    
    x = np.linspace(0, 65535, width, dtype=np.uint16)
    y = np.linspace(0, 65535, height, dtype=np.uint16)
    xx, yy = np.meshgrid(x, y)    
    red_channel = xx
    green_channel = yy
    blue_channel = 65535 - xx
    test_bgr = cv2.merge([blue_channel, green_channel, red_channel])    
    lab = bgr_to_lab(test_bgr)
    reconstructed = lab_to_bgr(lab)    
    diff = cv2.absdiff(test_bgr, reconstructed)
    print(f"LAB Max difference: {np.max(diff)}")
    print(f"LAB Mean difference: {np.mean(diff)}")    
    # cv2.imwrite("original_lab.tif", test_bgr)
    # cv2.imwrite("lab.tif", lab)
    # cv2.imwrite("reconstructed_lab.tif", reconstructed)
    assert np.max(diff) < 100
    assert np.mean(diff) < 10   

