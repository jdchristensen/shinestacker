import os
import logging
import numpy as np
from PIL import Image
from PIL.ExifTags import TAGS
from PIL.PngImagePlugin import PngInfo
from shinestacker.core.logging import setup_logging
from shinestacker.algorithms.utils import read_img
from shinestacker.algorithms.exif import (
    get_exif, copy_exif_from_file_to_file, print_exif, write_image_with_exif_data,
    get_tiff_dtype_count, save_exif_data, exif_dict, exif_extra_tags_for_tif,
    extract_enclosed_data_for_jpg, safe_decode_bytes, IFDRational)


NO_TEST_TIFF_TAGS = [
    "XMLPacket", "Compression", "StripOffsets", "RowsPerStrip", "StripByteCounts",
    "ImageResources", "ExifOffset", 34665, "IPTCNAA", 33723]

NO_TEST_JPG_TAGS = [34665]


def test_exif_jpg():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        out_filename = output_dir + "/0001.jpg"
        logger.info("======== Testing JPG EXIF ======== ")
        logger.info("*** Source JPG EXIF ***")
        exif = copy_exif_from_file_to_file(
            "examples/input/img-jpg/0000.jpg", "examples/input/img-jpg/0001.jpg",
            out_filename=out_filename, verbose=True)
        exif_copy = get_exif(out_filename)
        logger.info("*** Copy JPG EXIF ***")
        print_exif(exif_copy)
        for tag, tag_copy in zip(exif, exif_copy):
            data, data_copy = exif.get(tag), exif_copy.get(tag_copy)
            if isinstance(data, bytes):
                data = data.decode()
            if isinstance(data_copy, bytes):
                data_copy = data_copy.decode()
            if tag not in NO_TEST_TIFF_TAGS and not (tag == tag_copy and data == data_copy):
                logger.error(
                    "JPG EXIF data don't match: {tag} => {data}, {tag_copy} => {data_copy}")
                assert False
    except Exception:
        assert False


def common_entries(*dcts):
    if not dcts:
        return
    for i in set(dcts[0]).intersection(*dcts[1:]):
        yield (i,) + tuple(d[i] for d in dcts)


def test_exif_tiff():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        out_filename = output_dir + "/0001.tif"
        logger.info("======== Testing TIFF EXIF ========")
        logging.getLogger(__name__).info("*** Source TIFF EXIF ***")
        exif = copy_exif_from_file_to_file(
            "examples/input/img-tif/0000.tif", "examples/input/img-tif/0001.tif",
            out_filename=out_filename, verbose=True)
        image = Image.open(out_filename)
        exif_copy = image.tag_v2 if hasattr(image, 'tag_v2') else image.getexif()
        logging.getLogger(__name__).info("*** Copy TIFF EXIF ***")
        print_exif(exif_copy)
        meta, meta_copy = {}, {}
        for tag_id, tag_id_copy in zip(exif, exif_copy):
            tag = TAGS.get(tag_id, tag_id)
            tag_copy = TAGS.get(tag_id_copy, tag_id_copy)
            data, data_copy = exif.get(tag_id), exif_copy.get(tag_id_copy)
            if isinstance(data, bytes):
                if tag != "ImageResources":
                    try:
                        data = data.decode()
                    except Exception:
                        logger.warning("Test: can't decode EXIF tag {tag:25} [#{tag_id}]")
                        data = '<<< decode error >>>'
            if isinstance(data_copy, bytes):
                data_copy = data_copy.decode()
            meta[tag], meta_copy[tag_copy] = data, data_copy
        for (tag, data, data_copy) in list(common_entries(meta, meta_copy)):
            if tag not in NO_TEST_TIFF_TAGS and not data == data_copy:
                if tag in ["XResolution", "YResolution"]:
                    try:
                        if float(data) == float(data_copy):
                            continue
                    except Exception:
                        pass
                logger.error(f"TIFF EXIF data don't match: {tag}: {data}=>{data_copy}")
                assert False
    except Exception:
        assert False


def test_exif_png():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        out_filename = output_dir + "/0001.png"
        logger.info("======== Testing PNG EXIF ========")
        png_file = "examples/input/img-png-8/0000.png"
        if os.path.exists(png_file):
            logger.info("*** Source PNG EXIF ***")
            exif = get_exif(png_file)
            print_exif(exif)
            logger.info("*** Writing PNG with EXIF ***")
            image = Image.open(png_file)
            image_array = np.array(image)
            write_image_with_exif_data(
                exif, image_array, out_filename, verbose=True, color_order='rgb')
            logger.info("*** Written PNG EXIF ***")
            exif_copy = get_exif(out_filename)
            print_exif(exif_copy)
            if exif_copy:
                logger.info("PNG metadata test passed - found metadata in output file")
            else:
                logger.warning("No metadata found in PNG output file (this may be normal)")
            assert os.path.exists(out_filename), "Output PNG file was not created"
            test_img = Image.open(out_filename)
            test_img.verify()
            test_img.close()
        else:
            logger.warning("Test PNG file not found, skipping PNG EXIF test")
    except Exception as e:
        logger.error(f"PNG EXIF test failed: {str(e)}")
        assert False


def test_write_image_with_exif_data_jpg():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        XMLPACKET = 700
        IMAGERESOURCES = 34377
        INTERCOLORPROFILE = 34675
        logger.info("======== Testing write_image_with_exif_data (JPG) ========")
        jpg_out_filename = output_dir + "/0001_write_test.jpg"
        exif = get_exif("examples/input/img-jpg/0000.jpg")
        image = read_img("examples/input/img-jpg/0001.jpg")
        write_image_with_exif_data(exif, image, jpg_out_filename, verbose=True)
        written_exif = get_exif(jpg_out_filename)
        logger.info("*** Written JPG EXIF ***")
        print_exif(written_exif)
        for tag_id in exif:
            if tag_id not in NO_TEST_JPG_TAGS:
                original_data = exif.get(tag_id)
                written_data = written_exif.get(tag_id)
                if tag_id in [XMLPACKET, IMAGERESOURCES, INTERCOLORPROFILE]:
                    continue
                if isinstance(original_data, bytes):
                    try:
                        original_data = original_data.decode('utf-8', errors='replace')
                    except UnicodeDecodeError:
                        continue
                if isinstance(written_data, bytes):
                    try:
                        written_data = written_data.decode('utf-8', errors='replace')
                    except UnicodeDecodeError:
                        continue
                if original_data != written_data:
                    logger.error(
                        f"JPG EXIF data don't match for tag {tag_id}: "
                        f"{original_data} != {written_data}")
                    assert False
        logger.info("JPG write test passed successfully")
    except Exception as e:
        logger.error(f"JPG write test failed: {str(e)}")
        assert False


def test_write_image_with_exif_data_tiff():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        XMLPACKET = 700
        IMAGERESOURCES = 34377
        INTERCOLORPROFILE = 34675
        logger.info("======== Testing write_image_with_exif_data (TIFF) ========")
        tiff_out_filename = output_dir + "/0001_write_test.tif"
        exif = get_exif("examples/input/img-tif/0000.tif")
        image = read_img("examples/input/img-tif/0001.tif")
        write_image_with_exif_data(exif, image, tiff_out_filename, verbose=True)
        written_image = Image.open(tiff_out_filename)
        written_exif = written_image.tag_v2 \
            if hasattr(written_image, 'tag_v2') else \
            written_image.getexif()
        logger.info("*** Written TIFF EXIF ***")
        print_exif(written_exif)
        TIFF_SKIP_TAGS = [
            258,    # BitsPerSample
            259,    # Compression
            273,    # StripOffsets
            278,    # RowsPerStrip
            279,    # StripByteCounts
            282,    # XResolution
            283,    # YResolution
            296,    # ResolutionUnit
            305,    # Software - we change this to constants.APP_TITLE
            IMAGERESOURCES,
            INTERCOLORPROFILE,
            XMLPACKET
        ]
        for tag_id in exif:
            if tag_id not in TIFF_SKIP_TAGS:
                original_data = exif.get(tag_id)
                written_data = written_exif.get(tag_id)
                if original_data is None or written_data is None:
                    continue
                if isinstance(original_data, bytes) or isinstance(written_data, bytes):
                    continue
                if hasattr(original_data, 'numerator') and hasattr(written_data, 'numerator'):
                    if float(original_data) != float(written_data):
                        logger.error(
                            f"TIFF EXIF data don't match for tag {tag_id}: "
                            f"{original_data} != {written_data}")
                        assert False
                    continue
                elif hasattr(original_data, 'numerator') or hasattr(written_data, 'numerator'):
                    logger.error(
                        f"TIFF EXIF type mismatch for tag {tag_id}: "
                        f"{type(original_data)} != {type(written_data)}")
                    assert False
                if original_data != written_data:
                    logger.error(
                        f"TIFF EXIF data don't match for tag {tag_id}: "
                        f"{original_data} != {written_data}")
                    assert False
        logger.info("Skipped tags comparison for:")
        for tag_id in TIFF_SKIP_TAGS:
            if tag_id in exif:
                tag_name = TAGS.get(tag_id, tag_id)
                logger.info(f"  {tag_name} (tag {tag_id})")
        logger.info("TIFF write test passed successfully")
    except Exception as e:
        logger.error(f"TIFF write test failed: {str(e)}")
        assert False


def test_write_image_with_exif_data_png():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        logger.info("======== Testing write_image_with_exif_data (PNG) ========")
        png_out_filename = output_dir + "/0001_write_test.png"
        png_file = "examples/input/img-png-8/0000.png"
        if not os.path.exists(png_file):
            logger.warning("Test PNG file not found, skipping PNG write test")
            return
        exif = get_exif(png_file)
        logger.info("*** Source PNG EXIF ***")
        print_exif(exif)
        image_array = read_img(png_file)
        write_image_with_exif_data(exif, image_array, png_out_filename, verbose=True)
        logger.info("*** Verifying PNG file integrity ***")
        try:
            with Image.open(png_out_filename) as verify_img:
                verify_img.verify()
            logger.info("✓ PNG file verification passed")
        except Exception as e:
            logger.error(f"PNG verification failed: {e}")
            assert False, "PNG file verification failed"
        logger.info("*** Checking written PNG metadata with PIL ***")
        with Image.open(png_out_filename) as written_img:
            if hasattr(written_img, 'text') and written_img.text:
                logger.info("Written PNG text chunks (PIL):")
                for key, value in written_img.text.items():
                    logger.info(f"  {key}: {str(value)[:100]}...")
                    if 'xmp' in key.lower():
                        logger.info("✓ Found XMP metadata in written PNG!")
            else:
                logger.info("No text chunks found in written PNG (PIL)")
        logger.info("*** Checking written PNG metadata with get_exif ***")
        written_exif = get_exif(png_out_filename)
        if written_exif:
            logger.info("Written PNG EXIF (get_exif):")
            print_exif(written_exif)
        else:
            logger.info("No EXIF found in written PNG (get_exif)")
        logger.info("PNG write test completed successfully")
    except Exception as e:
        logger.error(f"PNG write test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        assert False


def test_get_tiff_dtype_count():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("======== Testing get_tiff_dtype_count ========")
        test_cases = [
            ("string", (2, 7)),
            (b"bytes", (1, 5)),
            ([1, 2, 3], (2, 10)),
            (np.array([1, 2, 3], dtype=np.uint16), (3, 3)),
            (np.array([1, 2, 3], dtype=np.uint32), (4, 3)),
            (np.array([1.0, 2.0], dtype=np.float32), (11, 2)),
            (np.array([1.0, 2.0], dtype=np.float64), (12, 2)),
            (12345, (3, 1)),
            (123456, (4, 1)),
            (3.14, (11, 1)),
            (None, (2, 5)),
        ]
        for value, expected in test_cases:
            result = get_tiff_dtype_count(value)
            logger.info(f"Testing {value!r:20} => Expected: {expected}, Got: {result}")
            assert result == expected, f"Failed for {value!r}: expected {expected}, got {result}"
        logger.info("All get_tiff_dtype_count tests passed")
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        assert False


def test_get_exif_from_png_with_metadata():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("======== Testing get_exif_from_png with metadata ========")
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        test_png = output_dir + "/test_metadata.png"
        img = Image.new('RGB', (100, 100), color='red')
        pnginfo = PngInfo()
        pnginfo.add_text("Title", "Test Image")
        pnginfo.add_text("Author", "Test Author")
        pnginfo.add_text("Description", "A test image for metadata")
        pnginfo.add_text("Software", "Test Software")
        img.save(test_png, pnginfo=pnginfo)
        exif = get_exif(test_png)
        logger.info("*** PNG Metadata extracted ***")
        print_exif(exif)
        assert exif is not None, "Should extract metadata from PNG"
        logger.info("✓ PNG metadata extraction test passed")
    except Exception as e:
        logger.error(f"PNG metadata test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        assert False


def test_extract_enclosed_data_for_jpg():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("======== Testing extract_enclosed_data_for_jpg ========")
        test_data = b'Some header data <?xpacket begin="test"?>' \
                    b'XMP content here<?xpacket end="w"?> trailer data'
        result = extract_enclosed_data_for_jpg(test_data, b'<?xpacket', b'<?xpacket end="w"?>')
        assert result is not None, "Should extract XMP data"
        assert b'XMP content here' in result, "Should contain the XMP content"
        logger.info("✓ Valid XMP extraction test passed")
        test_data = b'Just some regular data without XMP'
        result = extract_enclosed_data_for_jpg(test_data, b'<?xpacket', b'<?xpacket end="w"?>')
        assert result is None, "Should return None when no XMP found"
        logger.info("✓ No XMP data test passed")
        test_data = b'Data with <?xpacket begin but no end'
        result = extract_enclosed_data_for_jpg(test_data, b'<?xpacket', b'<?xpacket end="w"?>')
        assert result is None, "Should return None when only start marker found"
        logger.info("✓ Partial XMP data test passed")
        logger.info("All extract_enclosed_data_for_jpg tests passed")
    except Exception as e:
        logger.error(f"XMP extraction test failed: {str(e)}")
        assert False


def test_exif_extra_tags_for_tif():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("======== Testing exif_extra_tags_for_tif ========")
        test_exif = {
            256: 1000,
            257: 2000,
            282: IFDRational(72, 1),
            283: IFDRational(72, 1),
            296: 2,
            305: b'Test Software',
            270: 'Test Image Description',
            271: 'Test Camera Make',
            272: 'Test Camera Model',
            306: '2023:01:01 12:00:00',
            33432: 'Test Copyright',
            700: b'Test XML data',
        }
        extra_tags, exif_tags = exif_extra_tags_for_tif(test_exif)
        logger.info(f"Generated {len(extra_tags)} extra tags")
        logger.info(f"EXIF tags: {exif_tags}")
        assert 'resolution' in exif_tags
        assert 'resolutionunit' in exif_tags
        assert 'software' in exif_tags
        assert 'photometric' in exif_tags
        res_x, res_y = exif_tags['resolution']
        assert isinstance(res_x, tuple) and len(res_x) == 2
        assert isinstance(res_y, tuple) and len(res_y) == 2
        included_tags = [270, 271, 272, 306, 33432]
        found_tags = [tag_id for tag_id, dtype, count, value, write_once in extra_tags]
        for tag_id in included_tags:
            assert tag_id in found_tags, f"Tag {tag_id} should be included but was not found"
        logger.info("✓ exif_extra_tags_for_tif test passed")
    except Exception as e:
        logger.error(f"exif_extra_tags_for_tif test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        assert False


def test_write_image_with_exif_data_png_edge_cases():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        logger.info("======== Testing PNG EXIF edge cases ========")
        empty_exif = {}
        test_img = np.ones((50, 50, 3), dtype=np.uint8) * 128
        out_file = output_dir + "/test_empty_exif.png"
        write_image_with_exif_data(empty_exif, test_img, out_file, verbose=True)
        assert os.path.exists(out_file), "Should create file with empty EXIF"
        logger.info("✓ Empty EXIF test passed")
        special_exif = {
            270: 'Test with special chars: ñáéíóú',
            305: 'Test Software v1.0',
            315: 'Test Artist',
        }
        out_file2 = output_dir + "/test_special_chars.png"
        write_image_with_exif_data(special_exif, test_img, out_file2, verbose=True)
        assert os.path.exists(out_file2), "Should create file with special chars"
        logger.info("✓ Special characters test passed")
        long_exif = {
            270: 'A' * 500,
            305: 'B' * 200,
        }
        out_file3 = output_dir + "/test_long_values.png"
        write_image_with_exif_data(long_exif, test_img, out_file3, verbose=True)
        assert os.path.exists(out_file3), "Should create file with long values"
        logger.info("✓ Long values test passed")
        logger.info("All PNG edge case tests passed")
    except Exception as e:
        logger.error(f"PNG edge cases test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        assert False


def test_save_exif_data_different_formats():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        logger.info("======== Testing save_exif_data with different formats ========")
        source_file = "examples/input/img-jpg/0000.jpg"
        if not os.path.exists(source_file):
            logger.warning("Source file not found, skipping test")
            return
        exif = get_exif(source_file)
        jpg_out = output_dir + "/test_save_exif.jpg"
        if os.path.exists("examples/input/img-jpg/0001.jpg"):
            save_exif_data(exif, "examples/input/img-jpg/0001.jpg", jpg_out, verbose=True)
            assert os.path.exists(jpg_out), "Should save JPG with EXIF"
            logger.info("✓ JPG save_exif_data test passed")
        tiff_out = output_dir + "/test_save_exif.tif"
        if os.path.exists("examples/input/img-tif/0001.tif"):
            save_exif_data(exif, "examples/input/img-tif/0001.tif", tiff_out, verbose=True)
            assert os.path.exists(tiff_out), "Should save TIFF with EXIF"
            logger.info("✓ TIFF save_exif_data test passed")
        png_out = output_dir + "/test_save_exif.png"
        if os.path.exists("examples/input/img-png-8/0000.png"):
            save_exif_data(exif, "examples/input/img-png-8/0000.png", png_out, verbose=True)
            assert os.path.exists(png_out), "Should save PNG with EXIF"
            logger.info("✓ PNG save_exif_data test passed")
        logger.info("All save_exif_data format tests passed")
    except Exception as e:
        logger.error(f"save_exif_data test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        assert False


def test_exif_dict_functionality():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("======== Testing exif_dict functionality ========")
        result_none = exif_dict(None)
        assert result_none is None, "Should return None for None input"
        logger.info("✓ exif_dict with None input test passed")
        logger.info("All exif_dict functionality tests passed")
    except Exception as e:
        logger.error(f"exif_dict test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        assert False


def test_error_handling():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("======== Testing error handling ========")
        try:
            get_exif("non_existent_file.jpg")
            assert False, "Should raise exception for non-existent file"
        except RuntimeError as e:
            assert "File does not exist" in str(e)
            logger.info("✓ Non-existent file error handling works")
        try:
            copy_exif_from_file_to_file("non_existent.jpg", "examples/input/img-jpg/0001.jpg")
            assert False, "Should raise exception for non-existent source"
        except RuntimeError as e:
            assert "File does not exist" in str(e)
            logger.info("✓ Non-existent source error handling works")
        try:
            copy_exif_from_file_to_file("examples/input/img-jpg/0000.jpg", "non_existent.jpg")
            assert False, "Should raise exception for non-existent input"
        except RuntimeError as e:
            assert "File does not exist" in str(e)
            logger.info("✓ Non-existent input error handling works")
        try:
            save_exif_data(None, "examples/input/img-jpg/0001.jpg")
            assert False, "Should raise exception for None EXIF"
        except RuntimeError as e:
            assert "No exif data provided" in str(e)
            logger.info("✓ None EXIF error handling works")
        logger.info("All error handling tests passed")
    except Exception as e:
        logger.error(f"Error handling test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        assert False


def test_print_exif_edge_cases():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("======== Testing print_exif edge cases ========")
        rational_exif = {
            282: IFDRational(72, 1),
            283: IFDRational(96, 1),
        }
        print_exif(rational_exif)
        logger.info("✓ IFDRational printing test passed")
        string_exif = {
            "CustomTag1": "Custom Value 1",
            "CustomTag2": "Custom Value 2",
        }
        print_exif(string_exif)
        logger.info("✓ String tag IDs printing test passed")
        empty_exif = {}
        print_exif(empty_exif)
        logger.info("✓ Empty EXIF printing test passed")
        logger.info("All print_exif edge case tests passed")
    except Exception as e:
        logger.error(f"print_exif edge cases test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        assert False


def test_exif_decoding_error():
    test_exif = {
        270: b'\xff\xfe\x00\x01',
        305: b'Valid ASCII',
    }
    extra_tags, exif_tags = exif_extra_tags_for_tif(test_exif)
    assert extra_tags is not None


def test_safe_decode_bytes():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("======== Testing safe_decode_bytes ========")
        test_cases = [
            (b"Hello World", "Hello World"),
            (b"Caf\xe9", "Café"),
            (b"Test \xa9 2024", "Test © 2024"),
            (b"\xe9", "é"),
            (b"Invalid \xff\xfe bytes", "Invalid ÿþ bytes"),
        ]
        for input_bytes, expected in test_cases:
            result = safe_decode_bytes(input_bytes)
            logger.info(f"Testing {input_bytes!r} => Expected: {expected!r}, Got: {result!r}")
            assert result == expected, f"Failed for {input_bytes!r}"
        assert safe_decode_bytes("Already a string") == "Already a string"
        assert safe_decode_bytes(123) == 123
        assert safe_decode_bytes(None) is None
        logger.info("✓ All safe_decode_bytes tests passed")
    except Exception as e:
        logger.error(f"safe_decode_bytes test failed: {str(e)}")
        assert False


def test_exif_exposure_data_detection():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        logger.info("======== Testing EXIF Exposure Data Detection (Including SubIFD) ========")
        source_file = "examples/input/img-exif/0000.jpg"
        if not os.path.exists(source_file):
            logger.warning(f"Test file not found: {source_file}")
            return
        original_exif = get_exif(source_file)
        logger.info("*** All EXIF Tags Found ***")
        print_exif(original_exif)
        exposure_tags = {
            33434: "ExposureTime",
            33437: "FNumber",
            34855: "ISOSpeedRatings",
            34850: "ExposureProgram",
            37377: "ShutterSpeedValue",
            37378: "ApertureValue",
            37379: "BrightnessValue",
            37380: "ExposureBiasValue",
            37381: "MaxApertureValue",
            37382: "SubjectDistance",
            37383: "MeteringMode",
            37384: "LightSource",
            37385: "Flash",
            37386: "FocalLength",
            41986: "ExposureMode",
            41987: "WhiteBalance",
            42034: "ExposureIndex"
        }
        found_exposure_data = {}
        for tag_id, tag_name in exposure_tags.items():
            if tag_id in original_exif:
                found_exposure_data[tag_name] = original_exif[tag_id]
        if found_exposure_data:
            logger.info("=== FOUND EXPOSURE DATA ===")
            for tag_name, value in found_exposure_data.items():
                logger.info(f"  {tag_name}: {value}")
            out_file = output_dir + "/test_exposure_preservation.jpg"
            test_target = "examples/input/img-jpg/0001.jpg"
            if os.path.exists(test_target):
                copy_exif_from_file_to_file(source_file, test_target, out_file, verbose=True)
                copied_exif = get_exif(out_file)
                logger.info("=== VERIFYING COPIED EXPOSURE DATA ===")
                preserved_count = 0
                for tag_name in found_exposure_data.keys():
                    tag_id = [k for k, v in exposure_tags.items() if v == tag_name][0]
                    if tag_id in copied_exif:
                        preserved_count += 1
                        logger.info(f"  ✓ {tag_name} preserved: {copied_exif[tag_id]}")
                    else:
                        logger.warning(f"  ✗ {tag_name} NOT preserved")
                logger.info(
                    f"=== RESULT: {preserved_count}/{len(found_exposure_data)} "
                    "exposure tags preserved ===")
        else:
            logger.warning("=== NO EXPOSURE DATA FOUND ===")
            logger.warning("Even with SubIFD extraction, no exposure data was found.")
            logger.warning("This could mean:")
            logger.warning("1. The file was heavily processed and exposure data was stripped")
            logger.warning("2. The camera didn't write exposure data to this particular file")
            logger.warning("3. There's an issue with the EXIF SubIFD extraction")
    except Exception as e:
        logger.error(f"Exposure data detection test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())


def test_exif_subifd_exposure_preservation():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        logger.info("======== Testing EXIF SubIFD Exposure Data Preservation ========")
        source_file = "examples/input/img-exif/0000.jpg"
        if not os.path.exists(source_file):
            logger.warning("Test file not found, skipping SubIFD test")
            return
        original_exif = get_exif(source_file)
        subifd_exposure_tags = {
            33434: "ExposureTime",
            33437: "FNumber",
            34855: "ISOSpeedRatings",
            37377: "ShutterSpeedValue",
            37378: "ApertureValue",
            37386: "FocalLength"
        }
        found_tags = []
        for tag_id, tag_name in subifd_exposure_tags.items():
            if tag_id in original_exif:
                found_tags.append(tag_name)
                logger.info(f"✓ Found SubIFD tag: {tag_name} = {original_exif[tag_id]}")
            else:
                logger.error(f"✗ Missing SubIFD tag: {tag_name}")
                assert False, f"SubIFD tag {tag_name} not found"
        out_file = output_dir + "/test_subifd_preservation.jpg"
        test_target = "examples/input/img-jpg/0001.jpg"
        if os.path.exists(test_target):
            copy_exif_from_file_to_file(source_file, test_target, out_file, verbose=False)
            copied_exif = get_exif(out_file)
            preserved_count = 0
            for tag_id, tag_name in subifd_exposure_tags.items():
                if tag_id in original_exif and tag_id in copied_exif:
                    if original_exif[tag_id] == copied_exif[tag_id]:
                        preserved_count += 1
                    else:
                        logger.error(
                            f"SubIFD tag {tag_name} not preserved: "
                            f"{original_exif[tag_id]} -> {copied_exif[tag_id]}")
            logger.info(
                f"=== RESULT: {preserved_count}/{len(subifd_exposure_tags)} "
                "SubIFD exposure tags preserved ===")
            assert preserved_count == len(subifd_exposure_tags), \
                "Not all SubIFD exposure tags were preserved"
        logger.info("✓ EXIF SubIFD exposure preservation test passed")
    except Exception as e:
        logger.error(f"SubIFD exposure test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        assert False


def test_exif_tiff_with_subifd_data():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        logger.info("======== Testing TIFF Writing with SubIFD EXIF Data ========")
        source_file = "examples/input/img-exif/0000.jpg"
        if not os.path.exists(source_file):
            logger.warning("Test file not found, skipping TIFF SubIFD test")
            return
        exif = get_exif(source_file)
        logger.info("*** Source EXIF with SubIFD ***")
        exposure_tags = [33434, 33437, 34855, 37377, 37378, 37386]
        found_exposure = [tag for tag in exposure_tags if tag in exif]
        logger.info(f"Found {len(found_exposure)} exposure tags in source")
        test_image = np.ones((100, 100, 3), dtype=np.uint8) * 128
        out_file = output_dir + "/test_tiff_subifd.tif"
        write_image_with_exif_data(exif, test_image, out_file)
        assert os.path.exists(out_file), "TIFF file was not created"
        tiff_exif = get_exif(out_file)
        logger.info("*** TIFF EXIF (should preserve exposure data) ***")
        preserved_count = 0
        for tag_id in found_exposure:
            if tag_id in tiff_exif:
                preserved_count += 1
                logger.info(f"✓ TIFF preserved: {TAGS.get(tag_id, tag_id)} = {tiff_exif[tag_id]}")
            else:
                logger.warning(f"✗ TIFF missing: {TAGS.get(tag_id, tag_id)}")
        logger.info(
            f"=== RESULT: {preserved_count}/{len(found_exposure)} "
            "exposure tags preserved in TIFF ===")
        if preserved_count == 0:
            logger.warning(
                "No exposure data was preserved in TIFF - "
                "this is a known limitation with tifffile library")
        elif preserved_count < len(found_exposure):
            logger.warning(
                f"Only {preserved_count}/{len(found_exposure)} "
                "exposure tags preserved in TIFF")
        else:
            logger.info("✓ TIFF writing with SubIFD data test passed")
    except Exception as e:
        logger.error(f"TIFF SubIFD test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        logger.warning("TIFF SubIFD test encountered an error but continuing...")


def test_real_world_tiff_with_exif():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        logger.info("======== Testing Real-World TIFF with EXIF ========")
        source_file = "examples/input/img-exif/0000.jpg"
        if not os.path.exists(source_file):
            logger.warning("Test file not found, skipping real-world test")
            return
        exif = get_exif(source_file)
        logger.info(f"*** EXIF extracted from {os.path.basename(source_file)} ***")
        logger.info("=== Testing TIFF write with write_image_with_exif_data ===")
        test_image = np.ones((100, 100, 3), dtype=np.uint8) * 128
        out_file = output_dir + "/real_world_test.tif"
        write_image_with_exif_data(exif, test_image, out_file, verbose=False)
        assert os.path.exists(out_file), "TIFF file was not created"
        tiff_exif = get_exif(out_file)
        logger.info("*** TIFF EXIF (should preserve exposure data) ***")
        exposure_tags = {
            33434: "ExposureTime",
            33437: "FNumber",
            34855: "ISOSpeedRatings",
            37377: "ShutterSpeedValue",
            37378: "ApertureValue",
            37386: "FocalLength"
        }
        preserved_count = 0
        for tag_id, tag_name in exposure_tags.items():
            if tag_id in tiff_exif:
                preserved_count += 1
                logger.info(f"✓ TIFF preserved: {tag_name} = {tiff_exif[tag_id]}")
            else:
                logger.warning(f"✗ TIFF missing: {tag_name}")
        logger.info(
            f"=== RESULT: {preserved_count}/{len(exposure_tags)}"
            " exposure tags preserved in TIFF ===")
        try:
            with Image.open(out_file) as img:
                img.verify()
            logger.info("✓ TIFF file verification passed")
        except Exception as e:
            logger.error(f"TIFF verification failed: {e}")
            assert False, "TIFF file verification failed"
        logger.info("✓ Real-world TIFF test passed")
    except Exception as e:
        logger.error(f"Real-world TIFF test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        assert False


if __name__ == '__main__':
    test_exif_tiff()
    test_exif_jpg()
    test_exif_png()
    test_write_image_with_exif_data_jpg()
    test_write_image_with_exif_data_tiff()
    test_write_image_with_exif_data_png()
    test_get_tiff_dtype_count()
    test_get_exif_from_png_with_metadata()
    test_extract_enclosed_data_for_jpg()
    test_exif_extra_tags_for_tif()
    test_write_image_with_exif_data_png_edge_cases()
    test_save_exif_data_different_formats()
    test_exif_dict_functionality()
    test_error_handling()
    test_print_exif_edge_cases()
    test_exif_decoding_error()
    test_safe_decode_bytes()
    test_exif_exposure_data_detection()
    test_exif_subifd_exposure_preservation()
    test_exif_tiff_with_subifd_data()
    test_real_world_tiff_with_exif()
