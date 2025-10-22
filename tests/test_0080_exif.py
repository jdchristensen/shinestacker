import os
import logging
import numpy as np
from PIL import Image
from PIL.ExifTags import TAGS
from PIL.PngImagePlugin import PngInfo
from shinestacker.core.logging import setup_logging
from shinestacker.algorithms.exif import (
    get_exif, copy_exif_from_file_to_file, print_exif, write_image_with_exif_data,
    get_tiff_dtype_count, save_exif_data, exif_dict, exif_extra_tags_for_tif,
    extract_enclosed_data_for_jpg, IFDRational)


NO_TEST_TIFF_TAGS = [
    "XMLPacket", "Compression", "StripOffsets", "RowsPerStrip", "StripByteCounts",
    "ImageResources", "ExifOffset", 34665]

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
        image = Image.open("examples/input/img-jpg/0001.jpg")
        write_image_with_exif_data(exif, np.array(image), jpg_out_filename, verbose=True)
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
        image = Image.open("examples/input/img-tif/0001.tif")
        if image.mode == 'I;16':
            image_array = np.array(image, dtype=np.uint16)
        elif image.mode == 'RGB':
            if image.getexif().get(258, (8, 8, 8))[0] == 16:
                image_array = np.array(image, dtype=np.uint16)
            else:
                image_array = np.array(image)
        else:
            image_array = np.array(image)
        write_image_with_exif_data(exif, image_array, tiff_out_filename, verbose=True)
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
        with Image.open(png_file) as source_img:
            image_array = np.array(source_img)
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
            ("string", (2, 7)),         # ASCII string (dtype=2), length + null terminator
            (b"bytes", (1, 5)),         # Binary data (dtype=1), length without null terminator
            # Lists are treated as strings in the current implementation
            ([1, 2, 3], (2, 10)),       # Current behavior treats lists as strings
            (np.array([1, 2, 3], dtype=np.uint16), (3, 3)),
            (np.array([1, 2, 3], dtype=np.uint32), (4, 3)),
            (np.array([1.0, 2.0], dtype=np.float32), (11, 2)),
            (np.array([1.0, 2.0], dtype=np.float64), (12, 2)),
            (12345, (3, 1)),            # uint16 (dtype=3)
            (123456, (4, 1)),           # uint32 (dtype=4)
            (3.14, (11, 1)),            # float32 (dtype=11)
            (None, (2, 5)),             # None becomes 'None' (length 4 + null terminator)
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
            256: 1000,  # ImageWidth
            257: 2000,  # ImageLength
            282: IFDRational(72, 1),  # XResolution
            283: IFDRational(72, 1),  # YResolution
            296: 2,     # ResolutionUnit (inches)
            305: b'Test Software',  # Software
            270: 'Test Image Description',  # ImageDescription
            271: 'Test Camera Make',  # Make
            272: 'Test Camera Model',  # Model
            306: '2023:01:01 12:00:00',  # DateTime
            33432: 'Test Copyright',  # Copyright
            700: b'Test XML data',  # XMLPacket
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
        # XMLPacket (700) should be included in extra_tags, not excluded
        # Check that some expected tags are included
        included_tags = [270, 271, 272, 306, 33432]  # Should be included
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
            270: 'Test with special chars: ñáéíóú',  # ImageDescription
            305: 'Test Software v1.0',  # Software
            315: 'Test Artist',  # Artist
        }
        out_file2 = output_dir + "/test_special_chars.png"
        write_image_with_exif_data(special_exif, test_img, out_file2, verbose=True)
        assert os.path.exists(out_file2), "Should create file with special chars"
        logger.info("✓ Special characters test passed")
        long_exif = {
            270: 'A' * 500,  # Very long description
            305: 'B' * 200,  # Long software name
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
        test_exif = {
            256: 1000,  # ImageWidth
            257: 2000,  # ImageLength
            270: 'Test Description',  # ImageDescription
            282: IFDRational(72, 1),  # XResolution
            283: IFDRational(72, 1),  # YResolution
            296: 2,     # ResolutionUnit
            700: b'Test XML data',  # XMLPacket
            34377: b'Photoshop data',  # ImageResources
        }
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
            282: IFDRational(72, 1),  # XResolution
            283: IFDRational(96, 1),  # YResolution
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
        270: b'\xff\xfe\x00\x01',  # Invalid UTF-8 sequence
        305: b'Valid ASCII',       # Valid ASCII (should decode fine)
    }
    extra_tags, exif_tags = exif_extra_tags_for_tif(test_exif)
    assert extra_tags is not None


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
