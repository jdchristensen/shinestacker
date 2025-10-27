# pylint: disable=C0114, C0116, W0718, R0911, R0912, E1101, R0915, R1702, R0914, R0917, R0913
import os
import re
import logging
import cv2
import numpy as np
from PIL import Image
from PIL.TiffImagePlugin import IFDRational
from PIL.PngImagePlugin import PngInfo
from PIL.ExifTags import TAGS
import tifffile
from .. config.constants import constants
from .utils import write_img, extension_jpg, extension_tif, extension_png

IMAGEWIDTH = 256
IMAGELENGTH = 257
RESOLUTIONX = 282
RESOLUTIONY = 283
RESOLUTIONUNIT = 296
BITSPERSAMPLE = 258
PHOTOMETRICINTERPRETATION = 262
SAMPLESPERPIXEL = 277
PLANARCONFIGURATION = 284
SOFTWARE = 305
IMAGERESOURCES = 34377
INTERCOLORPROFILE = 34675
EXIFTAG = 34665
XMLPACKET = 700
STRIPOFFSETS = 273
STRIPBYTECOUNTS = 279
NO_COPY_TIFF_TAGS_ID = [IMAGEWIDTH, IMAGELENGTH, RESOLUTIONX, RESOLUTIONY, BITSPERSAMPLE,
                        PHOTOMETRICINTERPRETATION, SAMPLESPERPIXEL, PLANARCONFIGURATION, SOFTWARE,
                        RESOLUTIONUNIT, EXIFTAG, INTERCOLORPROFILE, IMAGERESOURCES]
NO_COPY_TIFF_TAGS = ["Compression", "StripOffsets", "RowsPerStrip", "StripByteCounts"]


def extract_enclosed_data_for_jpg(data, head, foot):
    try:
        xmp_start = data.find(head)
        if xmp_start == -1:
            return None
        xmp_end = data.find(foot, xmp_start)
        if xmp_end == -1:
            return None
        xmp_end += len(foot)
        return data[xmp_start:xmp_end]
    except Exception:
        return None


def get_exif(exif_filename, enhanced_png_parsing=True):
    if not os.path.isfile(exif_filename):
        raise RuntimeError(f"File does not exist: {exif_filename}")
    image = Image.open(exif_filename)
    if extension_tif(exif_filename):
        return image.tag_v2 if hasattr(image, 'tag_v2') else image.getexif()
    if extension_jpg(exif_filename):
        exif_data = image.getexif()
        try:
            exif_subifd = image.getexif().get_ifd(34665)
            for tag_id, value in exif_subifd.items():
                exif_data[tag_id] = value
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.debug(msg=f"Could not extract EXIF SubIFD: {e}")
        with open(exif_filename, 'rb') as f:
            data = extract_enclosed_data_for_jpg(f.read(), b'<?xpacket', b'<?xpacket end="w"?>')
            if data is not None:
                exif_data[XMLPACKET] = data
        return exif_data
    if extension_png(exif_filename):
        if enhanced_png_parsing:
            return get_enhanced_exif_from_png(image)
        exif_data = get_exif_from_png(image)
        return exif_data if exif_data else image.getexif()
    return image.getexif()


def get_exif_from_png(image):
    exif_data = {}
    exif_from_image = image.getexif()
    if exif_from_image:
        exif_data.update(dict(exif_from_image))
    if hasattr(image, 'text') and image.text:
        for key, value in image.text.items():
            exif_data[f"PNG_{key}"] = value
    if hasattr(image, 'info') and image.info:
        for key, value in image.info.items():
            if key not in ['dpi', 'gamma']:
                exif_data[f"PNG_{key}"] = value
    return exif_data


def parse_xmp_to_exif(xmp_data):
    exif_data = {}
    if not xmp_data:
        return exif_data
    if isinstance(xmp_data, bytes):
        xmp_data = xmp_data.decode('utf-8', errors='ignore')
    xmp_to_exif_map = {
        'tiff:Make': 271, 'tiff:Model': 272, 'exif:ExposureTime': 33434,
        'exif:FNumber': 33437, 'exif:ISOSpeedRatings': 34855, 'exif:FocalLength': 37386,
        'exif:DateTimeOriginal': 36867, 'xmp:CreateDate': 306, 'xmp:CreatorTool': 305,
        'aux:Lens': 42036, 'exif:Flash': 37385, 'exif:WhiteBalance': 41987,
        'dc:description': 270, 'dc:creator': 315, 'dc:rights': 33432
    }
    for xmp_tag, exif_tag in xmp_to_exif_map.items():
        start_tag = f'<{xmp_tag}>'
        end_tag = f'</{xmp_tag}>'
        if start_tag in xmp_data:
            start = xmp_data.find(start_tag) + len(start_tag)
            end = xmp_data.find(end_tag, start)
            if end != -1:
                value = xmp_data[start:end].strip()
                if value:
                    exif_data[exif_tag] = _parse_xmp_value(exif_tag, value)
    return exif_data


def _parse_xmp_value(exif_tag, value):
    if exif_tag in [33434, 33437, 37386]:  # Rational values
        if '/' in value:
            num, den = value.split('/')
            try:
                return IFDRational(int(num), int(den))
            except (ValueError, ZeroDivisionError):
                return float(value) if value else 0.0
        return float(value) if value else 0.0
    if exif_tag == 34855:  # ISO
        if '<rdf:li>' in value:
            matches = re.findall(r'<rdf:li>([^<]+)</rdf:li>', value)
            if matches:
                value = matches[0]
        try:
            return int(value)
        except ValueError:
            return value
    if exif_tag in [306, 36867]:  # DateTime and DateTimeOriginal
        if 'T' in value:
            value = value.replace('T', ' ').replace('-', ':')
        return value
    return value


def parse_typed_png_text(value):
    if isinstance(value, str):
        if value.startswith('RATIONAL:'):
            parts = value[9:].split('/')
            if len(parts) == 2:
                try:
                    return IFDRational(int(parts[0]), int(parts[1]))
                except (ValueError, ZeroDivisionError):
                    return value
        elif value.startswith('INT:'):
            try:
                return int(value[4:])
            except ValueError:
                return value[4:]
        elif value.startswith('FLOAT:'):
            try:
                return float(value[6:])
            except ValueError:
                return value[6:]
        elif value.startswith('STRING:'):
            return value[7:]
    return value


def get_enhanced_exif_from_png(image):
    basic_exif = get_exif_from_png(image)
    enhanced_exif = {}
    enhanced_exif.update(basic_exif)
    xmp_data = None
    if hasattr(image, 'text') and image.text:
        xmp_data = image.text.get('XML:com.adobe.xmp') or image.text.get('xml:com.adobe.xmp')
    if not xmp_data and 700 in basic_exif:
        xmp_data = basic_exif[700]
    if xmp_data:
        enhanced_exif.update(parse_xmp_to_exif(xmp_data))
    return {k: v for k, v in enhanced_exif.items() if isinstance(k, int)}


def reconstruct_exif_for_jpeg_with_exposure(exif_dict_data, verbose=False):
    logger = logging.getLogger(__name__)
    main_exif = Image.Exif()
    main_ifd_tags = {
        256, 257, 258, 259, 262, 274, 277, 282, 283, 284,
        296, 270, 271, 272, 305, 306, 315, 33432
    }
    exif_subifd_tags = {
        33434, 33437, 34855, 37377, 37378, 37386, 36864, 36867,
        36868, 37380, 37381, 37383, 37385, 40961, 40962, 40963,
        41985, 41986, 41987, 41990, 42033, 42034, 42036, 37521,
        37522, 36880, 41486, 41487, 41488
    }
    for tag_id in main_ifd_tags:
        if tag_id in exif_dict_data:
            try:
                main_exif[tag_id] = exif_dict_data[tag_id]
            except Exception:
                if verbose:
                    logger.warning(msg=f"Failed to add {TAGS.get(tag_id, tag_id)} to main IFD")
    subifd_exif = Image.Exif()
    subifd_found = False
    for tag_id in exif_subifd_tags:
        if tag_id in exif_dict_data:
            try:
                subifd_exif[tag_id] = exif_dict_data[tag_id]
                subifd_found = True
            except Exception:
                if verbose:
                    logger.warning(msg=f"Failed to add {TAGS.get(tag_id, tag_id)} to SubIFD")
    if subifd_found:
        try:
            main_exif[34665] = subifd_exif
        except Exception as e:
            if verbose:
                logger.warning(msg=f"Failed to create EXIF SubIFD: {e}")
    return main_exif


def safe_decode_bytes(data, encoding='utf-8'):
    if not isinstance(data, bytes):
        return data
    encodings = [encoding, 'latin-1', 'cp1252', 'utf-16', 'ascii']
    for enc in encodings:
        try:
            return data.decode(enc, errors='strict')
        except UnicodeDecodeError:
            continue
    try:
        return data.decode('utf-8', errors='replace')
    except Exception:
        return "<<< decode error >>>"


def get_tiff_dtype_count(value):
    if isinstance(value, str):
        return 2, len(value) + 1  # ASCII string, (dtype=2), length + null terminator
    if isinstance(value, (bytes, bytearray)):
        return 1, len(value)  # Binary data (dtype=1)
    if isinstance(value, (list, tuple, np.ndarray)):
        if isinstance(value, np.ndarray):
            dtype = value.dtype  # Array or sequence
        else:
            dtype = np.array(value).dtype  # Map numpy dtype to TIFF dtype
        if dtype == np.uint8:
            return 1, len(value)
        if dtype == np.uint16:
            return 3, len(value)
        if dtype == np.uint32:
            return 4, len(value)
        if dtype == np.float32:
            return 11, len(value)
        if dtype == np.float64:
            return 12, len(value)
    if isinstance(value, int):
        if 0 <= value <= 65535:
            return 3, 1  # uint16
        return 4, 1  # uint32
    if isinstance(value, float):
        return 11, 1  # float64
    return 2, len(str(value)) + 1  # Default for othre cases (ASCII string)


def add_exif_data_to_jpg_file(exif, in_filename, out_filename, verbose=False):
    if exif is None:
        raise RuntimeError('No exif data provided.')
    logger = logging.getLogger(__name__)
    xmp_data = exif.get(XMLPACKET) if hasattr(exif, 'get') else None
    with Image.open(in_filename) as image:
        if hasattr(exif, 'tobytes') and 'TiffImagePlugin' in str(type(exif)):
            jpeg_exif = Image.Exif()
            for tag_id in exif:
                if tag_id != XMLPACKET:
                    try:
                        jpeg_exif[tag_id] = exif[tag_id]
                    except Exception as e:
                        if verbose:
                            logger.warning(msg=f"Failed to add tag {tag_id}: {e}")
            exif_bytes = jpeg_exif.tobytes()
        elif hasattr(exif, 'tobytes'):
            exif_bytes = exif.tobytes()
        else:
            jpeg_exif = Image.Exif()
            for tag_id, value in exif.items():
                if tag_id != XMLPACKET:
                    try:
                        jpeg_exif[tag_id] = value
                    except Exception as e:
                        if verbose:
                            logger.warning(msg=f"Failed to add tag {tag_id}: {e}")
            exif_bytes = jpeg_exif.tobytes()
        image.save(out_filename, "JPEG", exif=exif_bytes, quality=100)
        if xmp_data and isinstance(xmp_data, bytes):
            _insert_xmp_into_jpeg(out_filename, xmp_data, verbose)


def _insert_xmp_into_jpeg(jpeg_path, xmp_data, verbose=False):
    logger = logging.getLogger(__name__)
    with open(jpeg_path, 'rb') as f:
        jpeg_data = f.read()
    soi_pos = jpeg_data.find(b'\xFF\xD8')
    if soi_pos == -1:
        if verbose:
            logger.warning("No SOI marker found, cannot insert XMP")
        return
    insert_pos = soi_pos + 2
    current_pos = insert_pos
    while current_pos < len(jpeg_data) - 4:
        if jpeg_data[current_pos] != 0xFF:
            break
        marker = jpeg_data[current_pos + 1]
        if marker == 0xDA:
            break
        segment_length = int.from_bytes(jpeg_data[current_pos + 2:current_pos + 4], 'big')
        if marker == 0xE1:
            insert_pos = current_pos + 2 + segment_length
            current_pos = insert_pos
            continue
        current_pos += 2 + segment_length
    xmp_identifier = b'http://ns.adobe.com/xap/1.0/\x00'
    xmp_payload = xmp_identifier + xmp_data
    segment_length = len(xmp_payload) + 2
    xmp_segment = b'\xFF\xE1' + segment_length.to_bytes(2, 'big') + xmp_payload
    updated_data = (
        jpeg_data[:insert_pos] +
        xmp_segment +
        jpeg_data[insert_pos:]
    )
    with open(jpeg_path, 'wb') as f:
        f.write(updated_data)
    if verbose:
        logger.info("Successfully inserted XMP data into JPEG")


def create_xmp_from_exif(exif_data):
    xmp_elements = []
    if exif_data:
        for tag_id, value in exif_data.items():
            if isinstance(tag_id, int):
                if tag_id == 270 and value:  # ImageDescription
                    desc = safe_decode_bytes(value)
                    xmp_elements.append(
                        f'<dc:description><rdf:Alt><rdf:li xml:lang="x-default">{desc}</rdf:li>'
                        '</rdf:Alt></dc:description>')
                elif tag_id == 315 and value:  # Artist
                    artist = safe_decode_bytes(value)
                    xmp_elements.append(
                        f'<dc:creator><rdf:Seq><rdf:li>{artist}</rdf:li>'
                        '</rdf:Seq></dc:creator>')
                elif tag_id == 33432 and value:  # Copyright
                    copyright_tag = safe_decode_bytes(value)
                    xmp_elements.append(
                        f'<dc:rights><rdf:Alt><rdf:li xml:lang="x-default">{copyright_tag}</rdf:li>'
                        '</rdf:Alt></dc:rights>')
                elif tag_id == 271 and value:  # Make
                    make = safe_decode_bytes(value)
                    xmp_elements.append(f'<tiff:Make>{make}</tiff:Make>')
                elif tag_id == 272 and value:  # Model
                    model = safe_decode_bytes(value)
                    xmp_elements.append(f'<tiff:Model>{model}</tiff:Model>')
                elif tag_id == 306 and value:  # DateTime
                    datetime_val = safe_decode_bytes(value)
                    if ':' in datetime_val:
                        datetime_val = datetime_val.replace(':', '-', 2).replace(' ', 'T')
                    xmp_elements.append(f'<xmp:CreateDate>{datetime_val}</xmp:CreateDate>')
                elif tag_id == 36867 and value:  # DateTimeOriginal
                    datetime_orig = safe_decode_bytes(value)
                    if ':' in datetime_orig:
                        datetime_orig = datetime_orig.replace(':', '-', 2).replace(' ', 'T')
                    xmp_elements.append(
                        f'<exif:DateTimeOriginal>{datetime_orig}</exif:DateTimeOriginal>')
                elif tag_id == 305 and value:  # Software
                    software = safe_decode_bytes(value)
                    xmp_elements.append(f'<xmp:CreatorTool>{software}</xmp:CreatorTool>')
                elif tag_id == 33434 and value:  # ExposureTime
                    if hasattr(value, 'numerator'):
                        exposure = float(value)
                    else:
                        exposure = float(value) if value else 0
                    xmp_elements.append(f'<exif:ExposureTime>{exposure}</exif:ExposureTime>')
                elif tag_id == 33437 and value:  # FNumber
                    if hasattr(value, 'numerator'):
                        fnumber = float(value)
                    else:
                        fnumber = float(value) if value else 0
                    xmp_elements.append(f'<exif:FNumber>{fnumber}</exif:FNumber>')
                elif tag_id == 34855 and value:  # ISOSpeedRatings
                    xmp_elements.append(
                        f'<exif:ISOSpeedRatings><rdf:Seq><rdf:li>{value}</rdf:li>'
                        '</rdf:Seq></exif:ISOSpeedRatings>')
                elif tag_id == 37386 and value:  # FocalLength
                    if hasattr(value, 'numerator'):
                        focal = float(value)
                    else:
                        focal = float(value) if value else 0
                    xmp_elements.append(f'<exif:FocalLength>{focal}</exif:FocalLength>')
                elif tag_id == 42036 and value:  # LensModel
                    lens_model = safe_decode_bytes(value)
                    xmp_elements.append(f'<aux:Lens>{lens_model}</aux:Lens>')
                elif tag_id == 34853 and value:  # GPSInfo (not implemented)
                    pass
                elif tag_id == 37385 and value:  # Flash
                    xmp_elements.append(f'<exif:Flash>{value}</exif:Flash>')
                elif tag_id == 41987 and value:  # WhiteBalance
                    wb_map = {0: 'Auto', 1: 'Manual'}
                    wb = wb_map.get(value, str(value))
                    xmp_elements.append(f'<exif:WhiteBalance>{wb}</exif:WhiteBalance>')
    if xmp_elements:
        xmp_content = '\n    '.join(xmp_elements)
        xmp_template = f"""<?xpacket begin='﻿' id='W5M0MpCehiHzreSzNTczkc9d'?>
<x:xmpmeta xmlns:x='adobe:ns:meta/'
 x:xmptk='Adobe XMP Core 5.6-c140 79.160451, 2017/05/06-01:08:21'>
 <rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#'>
  <rdf:Description rdf:about=''
    xmlns:dc='http://purl.org/dc/elements/1.1/'
    xmlns:xmp='http://ns.adobe.com/xap/1.0/'
    xmlns:tiff='http://ns.adobe.com/tiff/1.0/'
    xmlns:exif='http://ns.adobe.com/exif/1.0/'
    xmlns:aux='http://ns.adobe.com/exif/1.0/aux/'>
    {xmp_content}
  </rdf:Description>
 </rdf:RDF>
</x:xmpmeta>
<?xpacket end='w'?>"""
        return xmp_template
    return """<?xpacket begin='﻿' id='W5M0MpCehiHzreSzNTczkc9d'?>
<x:xmpmeta xmlns:x='adobe:ns:meta/'
 x:xmptk='Adobe XMP Core 5.6-c140 79.160451, 2017/05/06-01:08:21'>
 <rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#'>
  <rdf:Description rdf:about=''/>
 </rdf:RDF>
</x:xmpmeta>
<?xpacket end='w'?>"""


def write_image_with_exif_data_png(exif, image, out_filename, verbose=False, color_order='auto'):
    logger = logging.getLogger(__name__)
    if isinstance(image, np.ndarray) and image.dtype == np.uint16:
        if verbose:
            logger.warning(msg="EXIF data not supported for 16-bit PNG format")
        write_img(out_filename, image)
        return
    pil_image = _convert_to_pil_image(image, color_order)
    pnginfo, icc_profile = _prepare_png_metadata(exif, verbose, logger)
    try:
        save_args = {'format': 'PNG', 'pnginfo': pnginfo}
        if icc_profile:
            save_args['icc_profile'] = icc_profile
        pil_image.save(out_filename, **save_args)
    except Exception as e:
        if verbose:
            logger.error(msg=f"Failed to write PNG with metadata: {e}")
        pil_image.save(out_filename, format='PNG')


def _convert_to_pil_image(image, color_order):
    if isinstance(image, np.ndarray):
        if len(image.shape) == 3 and image.shape[2] == 3:
            if color_order in ['auto', 'bgr']:
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                return Image.fromarray(image_rgb)
        return Image.fromarray(image)
    return image


def _prepare_png_metadata(exif, verbose, logger):
    pnginfo = PngInfo()
    icc_profile = None
    xmp_data = _extract_xmp_data(exif)
    if xmp_data:
        pnginfo.add_text("XML:com.adobe.xmp", xmp_data)
    _add_exif_tags_to_pnginfo(exif, pnginfo)
    icc_profile = _extract_icc_profile(exif, verbose, logger)
    return pnginfo, icc_profile


def _extract_xmp_data(exif):
    for key, value in exif.items():
        if isinstance(key, str) and ('xmp' in key.lower() or 'xml' in key.lower()):
            if isinstance(value, bytes):
                try:
                    return value.decode('utf-8', errors='ignore')
                except Exception:
                    continue
            elif isinstance(value, str):
                return value
    return create_xmp_from_exif(exif)


def _add_exif_tags_to_pnginfo(exif, pnginfo):
    camera_tags = {
        271: 'CameraMake', 272: 'CameraModel', 305: 'Software',
        306: 'DateTime', 315: 'Artist', 33432: 'Copyright'
    }
    exposure_tags = {
        33434: 'ExposureTime', 33437: 'FNumber', 34855: 'ISOSpeed', 37377: 'ShutterSpeedValue',
        37378: 'ApertureValue', 37386: 'FocalLength', 42036: 'LensModel'
    }
    for tag_id, value in exif.items():
        if value is None:
            continue
        if isinstance(tag_id, int):
            if tag_id in camera_tags:
                _add_typed_tag(pnginfo, f"EXIF_{camera_tags[tag_id]}", value)
            elif tag_id in exposure_tags:
                _add_typed_tag(pnginfo, f"EXIF_{exposure_tags[tag_id]}", value)
            else:
                _add_exif_tag(pnginfo, tag_id, value)
        elif isinstance(tag_id, str) and not tag_id.lower().startswith(('xmp', 'xml')):
            _add_png_text_tag(pnginfo, tag_id, value)


def _add_typed_tag(pnginfo, key, value):
    try:
        if hasattr(value, 'numerator'):
            stored_value = f"RATIONAL:{value.numerator}/{value.denominator}"
        elif isinstance(value, bytes):
            try:
                stored_value = f"STRING:{value.decode('utf-8', errors='replace')}"
            except Exception:
                stored_value = f"BYTES:{str(value)[:100]}"
        elif isinstance(value, (list, tuple)):
            stored_value = f"ARRAY:{','.join(str(x) for x in value)}"
        elif isinstance(value, int):
            stored_value = f"INT:{value}"
        elif isinstance(value, float):
            stored_value = f"FLOAT:{value}"
        else:
            stored_value = f"STRING:{str(value)}"
        pnginfo.add_text(key, stored_value)
    except Exception:
        pass


def _add_exif_tag(pnginfo, tag_id, value):
    try:
        tag_name = TAGS.get(tag_id, f"Unknown_{tag_id}")
        if isinstance(value, bytes) and len(value) > 1000:
            return
        if isinstance(value, (int, float, str)):
            pnginfo.add_text(tag_name, str(value))
        elif isinstance(value, bytes):
            try:
                decoded_value = value.decode('utf-8', errors='replace')
                pnginfo.add_text(tag_name, decoded_value)
            except Exception:
                pass
        elif hasattr(value, 'numerator'):
            rational_str = f"{value.numerator}/{value.denominator}"
            pnginfo.add_text(tag_name, rational_str)
        else:
            pnginfo.add_text(tag_name, str(value))
    except Exception:
        pass


def _add_png_text_tag(pnginfo, key, value):
    try:
        clean_key = key[4:] if key.startswith('PNG_') else key
        if 'icc' in clean_key.lower() or 'profile' in clean_key.lower():
            return
        if isinstance(value, bytes):
            try:
                decoded_value = value.decode('utf-8', errors='replace')
                pnginfo.add_text(clean_key, decoded_value)
            except Exception:
                truncated_value = str(value)[:100] + "..."
                pnginfo.add_text(clean_key, truncated_value)
        else:
            pnginfo.add_text(clean_key, str(value))
    except Exception:
        pass


def _extract_icc_profile(exif, verbose, logger):
    for key, value in exif.items():
        if (isinstance(key, str) and
            isinstance(value, bytes) and
                ('icc' in key.lower() or 'profile' in key.lower())):
            if verbose:
                logger.info(f"Found ICC profile: {key}")
            return value
    return None


def clean_data_for_tiff(data):
    if isinstance(data, str):
        return data.encode('ascii', 'ignore').decode('ascii')
    if isinstance(data, bytes):
        try:
            return data.decode('utf-8', errors='ignore').encode('ascii', 'ignore').decode('ascii')
        except Exception:
            return ""
    if isinstance(data, IFDRational):
        return (data.numerator, data.denominator)
    return data


def write_image_with_exif_data_jpg(exif, image, out_filename, verbose):
    cv2.imwrite(out_filename, image, [int(cv2.IMWRITE_JPEG_QUALITY), 100])
    add_exif_data_to_jpg_file(exif, out_filename, out_filename, verbose)


def exif_extra_tags_for_tif(exif):
    res_x, res_y = exif.get(RESOLUTIONX), exif.get(RESOLUTIONY)
    resolution = (
        (res_x.numerator, res_x.denominator),
        (res_y.numerator, res_y.denominator)
    ) if res_x and res_y else (
        (720000, 10000), (720000, 10000)
    )
    exif_tags = {
        'resolution': resolution,
        'resolutionunit': exif.get(RESOLUTIONUNIT, 'inch'),
        'software': clean_data_for_tiff(exif.get(SOFTWARE)) or constants.APP_TITLE,
        'photometric': exif.get(PHOTOMETRICINTERPRETATION)
    }
    extra = []
    for tag_id in exif:
        tag, data = TAGS.get(tag_id, tag_id), exif.get(tag_id)
        if tag in NO_COPY_TIFF_TAGS or tag_id in NO_COPY_TIFF_TAGS_ID or tag_id == SOFTWARE:
            continue
        if isinstance(data, IFDRational):
            data = (data.numerator, data.denominator) if data.denominator != 0 else (0, 1)
            extra.append((tag_id, 5, 1, data, False))
            continue
        processed_data = _process_tiff_data(data)
        if processed_data:
            dtype, count, data_value = processed_data
            extra.append((tag_id, dtype, count, data_value, False))
    return extra, exif_tags


def _process_tiff_data(data):
    if isinstance(data, IFDRational):
        data = (data.numerator, data.denominator) if data.denominator != 0 else (0, 1)
        return 5, 1, data
    if hasattr(data, '__iter__') and not isinstance(data, (str, bytes)):
        try:
            clean_data = [float(x)
                          if not hasattr(x, 'denominator') or x.denominator != 0
                          else float('nan') for x in data]
            return 12, len(clean_data), tuple(clean_data)
        except Exception:
            return None
    if isinstance(data, (str, bytes)):
        clean_data = clean_data_for_tiff(data)
        if clean_data:
            return 2, len(clean_data) + 1, clean_data
    try:
        dtype, count = get_tiff_dtype_count(data)
        return dtype, count, data
    except Exception:
        return None


def write_image_with_exif_data_tif(exif, image, out_filename):
    logger = logging.getLogger(__name__)
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    try:
        metadata = {"description": f"image generated with {constants.APP_STRING} package"}
        extra_tags, exif_tags = exif_extra_tags_for_tif(exif)
        tifffile.imwrite(out_filename, image, metadata=metadata, compression='adobe_deflate',
                         extratags=extra_tags, **exif_tags)
    except Exception as e:
        logger.error(
            msg=f"Failed to write EXIF data into TIFF file: {e}. "
            "EXIF data not written with file.")
        tifffile.imwrite(out_filename, image, compression='adobe_deflate')


def write_image_with_exif_data(exif, image, out_filename, verbose=False, color_order='auto'):
    if exif is None:
        write_img(out_filename, image)
        return None
    if verbose:
        print_exif(exif)
    if extension_jpg(out_filename):
        write_image_with_exif_data_jpg(exif, image, out_filename, verbose)
    elif extension_tif(out_filename):
        write_image_with_exif_data_tif(exif, image, out_filename)
    elif extension_png(out_filename):
        write_image_with_exif_data_png(exif, image, out_filename, verbose, color_order=color_order)
    return exif


def save_exif_data(exif, in_filename, out_filename=None, verbose=False):
    if out_filename is None:
        out_filename = in_filename
    if exif is None:
        raise RuntimeError('No exif data provided.')
    if verbose:
        print_exif(exif)
    if extension_png(in_filename) or extension_tif(in_filename):
        if extension_tif(in_filename):
            image_new = tifffile.imread(in_filename)
        elif extension_png(in_filename):
            image_new = cv2.imread(in_filename, cv2.IMREAD_UNCHANGED)
        if extension_tif(in_filename):
            metadata = {"description": f"image generated with {constants.APP_STRING} package"}
            extra_tags, exif_tags = exif_extra_tags_for_tif(exif)
            tifffile.imwrite(
                out_filename, image_new, metadata=metadata, compression='adobe_deflate',
                extratags=extra_tags, **exif_tags)
        elif extension_png(in_filename):
            write_image_with_exif_data_png(exif, image_new, out_filename, verbose)
    else:
        add_exif_data_to_jpg_file(exif, in_filename, out_filename, verbose)
    return exif


def copy_exif_from_file_to_file(exif_filename, in_filename, out_filename=None, verbose=False):
    if not os.path.isfile(exif_filename):
        raise RuntimeError(f"File does not exist: {exif_filename}")
    if not os.path.isfile(in_filename):
        raise RuntimeError(f"File does not exist: {in_filename}")
    exif = get_exif(exif_filename)
    return save_exif_data(exif, in_filename, out_filename, verbose)


def exif_dict(exif_data):
    if exif_data is None:
        return None
    result = {}
    for tag, value in exif_data.items():
        if isinstance(tag, int):
            tag_name = TAGS.get(tag, str(tag))
        else:
            tag_name = str(tag)
        if 'PNG_EXIF_' in tag_name:
            standard_tag = tag_name.replace('PNG_EXIF_', '')
        elif 'EXIF_' in tag_name:
            standard_tag = tag_name.replace('EXIF_', '')
        elif tag_name.startswith('PNG_'):
            continue
        else:
            standard_tag = tag_name
        result[standard_tag] = (tag, value)
    return result


def print_exif(exif):
    exif_data = exif_dict(exif)
    if exif_data is None:
        raise RuntimeError('Image has no exif data.')
    logger = logging.getLogger(__name__)
    for tag, (tag_id, data) in exif_data.items():
        if isinstance(data, IFDRational):
            data = f"{data.numerator}/{data.denominator}"
        data_str = f"{data}"
        if len(data_str) > 40:
            data_str = f"{data_str[:40]}... (truncated)"
        if isinstance(tag_id, int):
            tag_id_str = f"[#{tag_id:5d}]"
        else:
            tag_id_str = f"[ {tag_id:20} ]"
        logger.info(msg=f"{tag:25} {tag_id_str}: {data_str}")
