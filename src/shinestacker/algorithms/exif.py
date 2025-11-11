# pylint: disable=C0114, C0116, C0302, W0718, R0911, R0912, E1101
# pylint: disable=R0915, R1702, R0914, R0917, R0913
import os
import re
import logging
import traceback
import cv2
import numpy as np
from PIL import Image
from PIL.TiffImagePlugin import IFDRational
from PIL.PngImagePlugin import PngInfo
from PIL.ExifTags import TAGS
import tifffile
from .. config.constants import constants
from .utils import read_img, write_img, extension_jpg, extension_tif, extension_png

IMAGEWIDTH = 256
IMAGELENGTH = 257
BITSPERSAMPLE = 258
COMPRESSION = 259
PHOTOMETRICINTERPRETATION = 262
IMAGEDESCRIPTION = 270
MAKE = 271
MODEL = 272
STRIPOFFSETS = 273
ORIENTATION = 274
SAMPLESPERPIXEL = 277
ROWSPERSTRIP = 278
STRIPBYTECOUNTS = 279
XRESOLUTION = 282
YRESOLUTION = 283
PLANARCONFIGURATION = 284
RESOLUTIONUNIT = 296
SOFTWARE = 305
DATETIME = 306
ARTIST = 315
PREDICTOR = 317
WHITEPOINT = 318
PRIMARYCHROMATICITIES = 319
COLORMAP = 320
TILEWIDTH = 322
TILELENGTH = 323
TILEOFFSETS = 324
TILEBYTECOUNTS = 325
EXIFIFD = 34665
ICCPROFILE = 34675
COPYRIGHT = 33432
EXPOSURETIME = 33434
FNUMBER = 33437
EXPOSUREPROGRAM = 34850
ISOSPEEDRATINGS = 34855
EXIFVERSION = 36864
DATETIMEORIGINAL = 36867
DATETIMEDIGITIZED = 36868
SHUTTERSPEEDVALUE = 37377
APERTUREVALUE = 37378
BRIGHTNESSVALUE = 37379
EXPOSUREBIASVALUE = 37380
MAXAPERTUREVALUE = 37381
SUBJECTDISTANCE = 37382
METERINGMODE = 37383
LIGHTSOURCE = 37384
FLASH = 37385
FOCALLENGTH = 37386
MAKERNOTE = 37500
USERCOMMENT = 37510
SUBSECTIME = 37520
SUBSECTIMEORIGINAL = 37521
SUBSECTIMEDIGITIZED = 37522
FLASHPIXVERSION = 40960
COLORSPACE = 40961
PIXELXDIMENSION = 40962
PIXELYDIMENSION = 40963
RELATEDSOUNDFILE = 40964
FLASHENERGY = 41483
SPATIALFREQUENCYRESPONSE = 41484
FOCALPLANEXRESOLUTION = 41486
FOCALPLANEYRESOLUTION = 41487
FOCALPLANERESOLUTIONUNIT = 41488
SUBJECTLOCATION = 41492
EXPOSUREINDEX = 41493
SENSINGMETHOD = 41495
FILESOURCE = 41728
SCENETYPE = 41729
CFAPATTERN = 41730
CUSTOMRENDERED = 41985
EXPOSUREMODE = 41986
WHITEBALANCE = 41987
DIGITALZOOMRATIO = 41988
FOCALLENGTHIN35MMFILM = 41989
SCENECAPTURETYPE = 41990
GAINCONTROL = 41991
CONTRAST = 41992
SATURATION = 41993
SHARPNESS = 41994
DEVICESETTINGDESCRIPTION = 41995
SUBJECTDISTANCERANGE = 41996
IMAGEUNIQUEID = 42016
LENSINFO = 42034
LENSMAKE = 42035
LENSMODEL = 42036
GPSIFD = 34853
XMLPACKET = 700
IMAGERESOURCES = 34377
INTERCOLORPROFILE = 34675

NO_COPY_TIFF_TAGS_ID = [
    IMAGEWIDTH, IMAGELENGTH, XRESOLUTION, YRESOLUTION, BITSPERSAMPLE,
    PHOTOMETRICINTERPRETATION, SAMPLESPERPIXEL, PLANARCONFIGURATION, SOFTWARE,
    RESOLUTIONUNIT, EXIFIFD, INTERCOLORPROFILE, IMAGERESOURCES,
    STRIPOFFSETS, STRIPBYTECOUNTS, TILEOFFSETS, TILEBYTECOUNTS
]

NO_COPY_TIFF_TAGS = ["Compression", "StripOffsets", "RowsPerStrip", "StripByteCounts"]

XMP_TEMPLATE = """<?xpacket begin='﻿' id='W5M0MpCehiHzreSzNTczkc9d'?>
<x:xmpmeta xmlns:x='adobe:ns:meta/' x:xmptk='Adobe XMP Core 5.6-c140 79.160451, 2017/05/06-01:08:21'>
 <rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#'>
  <rdf:Description rdf:about='' xmlns:dc='http://purl.org/dc/elements/1.1/' xmlns:xmp='http://ns.adobe.com/xap/1.0/' xmlns:tiff='http://ns.adobe.com/tiff/1.0/' xmlns:exif='http://ns.adobe.com/exif/1.0/' xmlns:aux='http://ns.adobe.com/exif/1.0/aux/'>
    {content}
  </rdf:Description>
 </rdf:RDF>
</x:xmpmeta>
<?xpacket end='w'?>"""  # noqa

XMP_EMPTY_TEMPLATE = """<?xpacket begin='﻿' id='W5M0MpCehiHzreSzNTczkc9d'?>
<x:xmpmeta xmlns:x='adobe:ns:meta/' x:xmptk='Adobe XMP Core 5.6-c140 79.160451, 2017/05/06-01:08:21'>
 <rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#'>
  <rdf:Description rdf:about=''/>
 </rdf:RDF>
</x:xmpmeta>
<?xpacket end='w'?>"""  # noqa

XMP_TO_EXIF_MAP = {
    'tiff:Make': MAKE,
    'tiff:Model': MODEL,
    'exif:ExposureTime': EXPOSURETIME,
    'exif:FNumber': FNUMBER,
    'exif:ISOSpeedRatings': ISOSPEEDRATINGS,
    'exif:FocalLength': FOCALLENGTH,
    'exif:DateTimeOriginal': DATETIMEORIGINAL,
    'xmp:CreateDate': DATETIME,
    'xmp:CreatorTool': SOFTWARE,
    'aux:Lens': LENSMODEL,  # Adobe's auxiliary namespace
    'exifEX:LensModel': LENSMODEL,  # EXIF 2.3 namespace
    'exif:Flash': FLASH,
    'exif:WhiteBalance': WHITEBALANCE,
    'dc:description': IMAGEDESCRIPTION,
    'dc:creator': ARTIST,
    'dc:rights': COPYRIGHT,
    'exif:ShutterSpeedValue': SHUTTERSPEEDVALUE,
    'exif:ApertureValue': APERTUREVALUE,
    'exif:ExposureBiasValue': EXPOSUREBIASVALUE,
    'exif:MaxApertureValue': MAXAPERTUREVALUE,
    'exif:MeteringMode': METERINGMODE,
    'exif:ExposureMode': EXPOSUREMODE,
    'exif:SceneCaptureType': SCENECAPTURETYPE
}

PNG_TAG_MAP = {
    'EXIF_CameraMake': MAKE,
    'EXIF_CameraModel': MODEL,
    'EXIF_Software': SOFTWARE,
    'EXIF_DateTime': DATETIME,
    'EXIF_Artist': ARTIST,
    'EXIF_Copyright': COPYRIGHT,
    'EXIF_ExposureTime': EXPOSURETIME,
    'EXIF_FNumber': FNUMBER,
    'EXIF_ISOSpeedRatings': ISOSPEEDRATINGS,
    'EXIF_ShutterSpeedValue': SHUTTERSPEEDVALUE,
    'EXIF_ApertureValue': APERTUREVALUE,
    'EXIF_FocalLength': FOCALLENGTH,
    'EXIF_LensModel': LENSMODEL,
    'EXIF_ExposureBiasValue': EXPOSUREBIASVALUE,
    'EXIF_MaxApertureValue': MAXAPERTUREVALUE,
    'EXIF_MeteringMode': METERINGMODE,
    'EXIF_Flash': FLASH,
    'EXIF_WhiteBalance': WHITEBALANCE,
    'EXIF_ExposureMode': EXPOSUREMODE,
    'EXIF_SceneCaptureType': SCENECAPTURETYPE,
    'EXIF_DateTimeOriginal': DATETIMEORIGINAL
}


def safe_decode_bytes(data, encoding='utf-8'):
    if not isinstance(data, bytes):
        return data
    encodings = [encoding, 'latin-1', 'cp1252', 'utf-16', 'ascii']
    for enc in encodings:
        try:
            return data.decode(enc, errors='strict')
        except UnicodeDecodeError:
            continue
    return data.decode('utf-8', errors='replace')


XMP_TAG_MAP = {
    IMAGEDESCRIPTION: {'format': 'dc:description', 'type': 'rdf_alt',
                       'processor': safe_decode_bytes},
    ARTIST: {'format': 'dc:creator', 'type': 'rdf_seq', 'processor': safe_decode_bytes},
    COPYRIGHT: {'format': 'dc:rights', 'type': 'rdf_alt', 'processor': safe_decode_bytes},
    MAKE: {'format': 'tiff:Make', 'type': 'simple', 'processor': safe_decode_bytes},
    MODEL: {'format': 'tiff:Model', 'type': 'simple', 'processor': safe_decode_bytes},
    DATETIME: {'format': 'xmp:CreateDate', 'type': 'datetime', 'processor': safe_decode_bytes},
    DATETIMEORIGINAL: {'format': 'exif:DateTimeOriginal', 'type': 'datetime',
                       'processor': safe_decode_bytes},
    SOFTWARE: {'format': 'xmp:CreatorTool', 'type': 'simple', 'processor': safe_decode_bytes},
    EXPOSURETIME: {'format': 'exif:ExposureTime', 'type': 'rational', 'processor': None},
    FNUMBER: {'format': 'exif:FNumber', 'type': 'rational', 'processor': None},
    ISOSPEEDRATINGS: {'format': 'exif:ISOSpeedRatings', 'type': 'rdf_seq', 'processor': None},
    FOCALLENGTH: {'format': 'exif:FocalLength', 'type': 'rational', 'processor': None},
    LENSMODEL: {'format': 'aux:Lens', 'type': 'simple', 'processor': safe_decode_bytes},
    SHUTTERSPEEDVALUE: {'format': 'exif:ShutterSpeedValue', 'type': 'rational', 'processor': None},
    APERTUREVALUE: {'format': 'exif:ApertureValue', 'type': 'rational', 'processor': None},
    EXPOSUREBIASVALUE: {'format': 'exif:ExposureBiasValue', 'type': 'rational', 'processor': None},
    MAXAPERTUREVALUE: {'format': 'exif:MaxApertureValue', 'type': 'rational', 'processor': None},
    METERINGMODE: {'format': 'exif:MeteringMode', 'type': 'simple', 'processor': None},
    FLASH: {'format': 'exif:Flash', 'type': 'simple', 'processor': None},
    WHITEBALANCE: {'format': 'exif:WhiteBalance', 'type': 'mapped', 'processor': None,
                   'map': {0: 'Auto', 1: 'Manual'}},
    EXPOSUREMODE: {'format': 'exif:ExposureMode', 'type': 'mapped', 'processor': None,
                   'map': {0: 'Auto', 1: 'Manual', 2: 'Auto bracket'}},
    SCENECAPTURETYPE: {'format': 'exif:SceneCaptureType', 'type': 'mapped', 'processor': None,
                       'map': {0: 'Standard', 1: 'Landscape', 2: 'Portrait', 3: 'Night scene'}}
}

CAMERA_TAGS_MAP = {
    MAKE: 'CameraMake',
    MODEL: 'CameraModel',
    SOFTWARE: 'Software',
    DATETIME: 'DateTime',
    ARTIST: 'Artist',
    COPYRIGHT: 'Copyright'
}

EXPOSURE_TAGS_MAP = {
    EXPOSURETIME: 'ExposureTime',
    FNUMBER: 'FNumber',
    ISOSPEEDRATINGS: 'ISOSpeedRatings',
    SHUTTERSPEEDVALUE: 'ShutterSpeedValue',
    APERTUREVALUE: 'ApertureValue',
    FOCALLENGTH: 'FocalLength',
    LENSMODEL: 'LensModel',
    EXPOSUREBIASVALUE: 'ExposureBiasValue',
    MAXAPERTUREVALUE: 'MaxApertureValue',
    METERINGMODE: 'MeteringMode',
    FLASH: 'Flash',
    WHITEBALANCE: 'WhiteBalance',
    EXPOSUREMODE: 'ExposureMode',
    SCENECAPTURETYPE: 'SceneCaptureType',
    DATETIMEORIGINAL: 'DateTimeOriginal'
}

EXPOSURE_DATA_TIFF = {v: k for k, v in EXPOSURE_TAGS_MAP.items()} | {
    'Make': MAKE,
    'Model': MODEL
}

COMPATIBLE_TAGS = [
    MAKE, MODEL, SOFTWARE, DATETIME, ARTIST, COPYRIGHT,
    EXPOSURETIME, FNUMBER, ISOSPEEDRATINGS, EXPOSUREPROGRAM,
    SHUTTERSPEEDVALUE, APERTUREVALUE, BRIGHTNESSVALUE, EXPOSUREBIASVALUE,
    MAXAPERTUREVALUE, SUBJECTDISTANCE, METERINGMODE, LIGHTSOURCE, FLASH,
    FOCALLENGTH, EXPOSUREMODE, WHITEBALANCE, EXPOSUREINDEX,
    SCENECAPTURETYPE, DATETIMEORIGINAL, LENSMODEL, LENSMAKE,
    FOCALLENGTHIN35MMFILM, GAINCONTROL, CONTRAST, SATURATION, SHARPNESS,
    CUSTOMRENDERED, DIGITALZOOMRATIO, SUBJECTDISTANCERANGE,
    EXIFVERSION, FLASHPIXVERSION,
    COLORSPACE, PIXELXDIMENSION, PIXELYDIMENSION, IMAGEWIDTH, IMAGELENGTH,
    BITSPERSAMPLE, ORIENTATION, XRESOLUTION, YRESOLUTION, RESOLUTIONUNIT
]


def extract_enclosed_data_for_jpg(data, head, foot):
    xmp_start = data.find(head)
    if xmp_start == -1:
        return None
    xmp_end = data.find(foot, xmp_start)
    if xmp_end == -1:
        return None
    xmp_end += len(foot)
    return data[xmp_start:xmp_end]


def get_exif(exif_filename, enhanced_png_parsing=True):
    if not os.path.isfile(exif_filename):
        raise RuntimeError(f"File does not exist: {exif_filename}")
    image = Image.open(exif_filename)
    if extension_tif(exif_filename):
        return get_exif_from_tiff(image, exif_filename)
    if extension_jpg(exif_filename):
        return get_exif_from_jpg(image, exif_filename)
    if extension_png(exif_filename):
        if enhanced_png_parsing:
            return get_enhanced_exif_from_png(image)
        exif_data = get_exif_from_png(image)
        return exif_data if exif_data else image.getexif()
    return image.getexif()


def get_exif_from_tiff(image, exif_filename):
    exif_data = image.tag_v2 if hasattr(image, 'tag_v2') else image.getexif()
    try:
        with tifffile.TiffFile(exif_filename) as tif:
            for page in tif.pages:
                if EXIFIFD in page.tags:
                    exif_dict_data = page.tags[EXIFIFD].value
                    for exif_key, tag_id in EXPOSURE_DATA_TIFF.items():
                        if exif_key in exif_dict_data:
                            value = exif_dict_data[exif_key]
                            if isinstance(value, tuple) and len(value) == 2:
                                value = IFDRational(value[0], value[1])
                            exif_data[tag_id] = value
                    break
    except Exception as e:
        print(f"Error reading EXIF with tifffile: {e}")
    try:
        if XMLPACKET in exif_data:
            xmp_data = exif_data[XMLPACKET]
            if isinstance(xmp_data, bytes):
                xmp_string = xmp_data.decode('utf-8', errors='ignore')
            else:
                xmp_string = str(xmp_data)
            xmp_exif = parse_xmp_to_exif(xmp_string)
            for tag_id in [EXPOSURETIME, FNUMBER, ISOSPEEDRATINGS, FOCALLENGTH, LENSMODEL]:
                if tag_id in xmp_exif and tag_id not in exif_data:
                    exif_data[tag_id] = xmp_exif[tag_id]
    except Exception as e:
        print(f"Error processing XMP: {e}")
    return exif_data


def get_exif_from_jpg(image, exif_filename):
    exif_data = image.getexif()
    try:
        exif_subifd = exif_data.get_ifd(EXIFIFD)
        for tag_id, value in exif_subifd.items():
            if tag_id in EXPOSURE_TAGS_MAP:
                exif_data[tag_id] = value
            elif tag_id not in exif_data:
                exif_data[tag_id] = value
    except Exception:
        pass
    if MAKERNOTE in exif_data:
        del exif_data[MAKERNOTE]
    with open(exif_filename, 'rb') as f:
        data = extract_enclosed_data_for_jpg(f.read(), b'<?xpacket', b'<?xpacket end="w"?>')
        if data is not None:
            exif_data[XMLPACKET] = data
    return exif_data


def get_exif_from_png(image):
    exif_data = {}
    exif_from_image = image.getexif()
    if exif_from_image:
        exif_data.update(dict(exif_from_image))
    for attr_name in ['text', 'info']:
        if hasattr(image, attr_name) and getattr(image, attr_name):
            for key, value in getattr(image, attr_name).items():
                if attr_name == 'info' and key in ['dpi', 'gamma']:
                    continue
                exif_data[f"PNG_{key}"] = value
    return exif_data


def parse_xmp_to_exif(xmp_data):
    exif_data = {}
    if not xmp_data:
        return exif_data
    if isinstance(xmp_data, bytes):
        xmp_data = xmp_data.decode('utf-8', errors='ignore')
    for xmp_tag, exif_tag in XMP_TO_EXIF_MAP.items():
        attr_pattern = f'{xmp_tag}="([^"]*)"'
        attr_matches = re.findall(attr_pattern, xmp_data)
        for value in attr_matches:
            if value:
                exif_data[exif_tag] = _parse_xmp_value(exif_tag, value)
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
    if exif_tag in [EXPOSURETIME, FNUMBER, FOCALLENGTH]:
        if '/' in value:
            num, den = value.split('/')
            try:
                return IFDRational(int(num), int(den))
            except (ValueError, ZeroDivisionError):
                try:
                    return float(value) if value else 0.0
                except ValueError:
                    return 0.0
        return float(value) if value else 0.0
    if exif_tag == ISOSPEEDRATINGS:  # ISO
        if '<rdf:li>' in value:
            matches = re.findall(r'<rdf:li>([^<]+)</rdf:li>', value)
            if matches:
                value = matches[0]
        try:
            return int(value)
        except ValueError:
            return value
    if exif_tag in [DATETIME, DATETIMEORIGINAL]:  # DateTime and DateTimeOriginal
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
                    return value[9:]
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
        elif value.startswith('BYTES:'):
            return value[6:].encode('utf-8')
        elif value.startswith('ARRAY:'):
            return [x.strip() for x in value[6:].split(',')]
    return value


def get_enhanced_exif_from_png(image):
    basic_exif = get_exif_from_png(image)
    enhanced_exif = {}
    enhanced_exif.update(basic_exif)
    xmp_data = None
    if hasattr(image, 'text') and image.text:
        xmp_data = image.text.get('XML:com.adobe.xmp') or image.text.get('xml:com.adobe.xmp')
    if not xmp_data and XMLPACKET in basic_exif:
        xmp_data = basic_exif[XMLPACKET]
    if xmp_data:
        enhanced_exif.update(parse_xmp_to_exif(xmp_data))
    if hasattr(image, 'text') and image.text:
        for key, value in image.text.items():
            if key.startswith('EXIF_'):
                parsed_value = parse_typed_png_text(value)
                tag_id = PNG_TAG_MAP.get(key)
                if tag_id:
                    enhanced_exif[tag_id] = parsed_value
    if MAKERNOTE in enhanced_exif:
        del enhanced_exif[MAKERNOTE]
    return {k: v for k, v in enhanced_exif.items() if isinstance(k, int)}


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
    return 2, len(str(value)) + 1  # Default for other cases (ASCII string)


def add_exif_data_to_jpg_file(exif, in_filename, out_filename, verbose=False):
    if exif is None:
        raise RuntimeError('No exif data provided.')
    logger = logging.getLogger(__name__)
    xmp_data = exif.get(XMLPACKET) if hasattr(exif, 'get') else None
    if out_filename is None:
        out_filename = in_filename
    use_temp = in_filename == out_filename
    if use_temp:
        temp_filename = out_filename + ".tmp"
        final_filename = temp_filename
    else:
        final_filename = out_filename
    try:
        with Image.open(in_filename) as image:
            jpeg_exif = Image.Exif()
            for tag_id in COMPATIBLE_TAGS:
                if tag_id in exif:
                    value = exif[tag_id]
                    if tag_id in [ORIENTATION, FLASH] and isinstance(value, float):
                        value = int(value)
                        if verbose:
                            print(f"Converted Orientation from float to int: {value}")
                    elif tag_id == BITSPERSAMPLE and isinstance(value, tuple):
                        jpeg_exif[tag_id] = 8
                        if verbose:
                            print(f"Converted BitsPerSample from {value} to 8 for JPEG")
                        continue
                    try:
                        if tag_id in [EXIFVERSION, FLASHPIXVERSION]:
                            if isinstance(value, str):
                                jpeg_exif[tag_id] = value.encode('ascii')
                            else:
                                jpeg_exif[tag_id] = value
                        elif isinstance(value, tuple) and len(value) == 2:
                            value = IFDRational(value[0], value[1])
                            jpeg_exif[tag_id] = value
                        elif isinstance(value, (int, str, float, IFDRational)):
                            jpeg_exif[tag_id] = value
                        else:
                            if verbose:
                                print(f"Skipping unsupported type for tag {tag_id}: {type(value)}")
                    except Exception as e:
                        if verbose:
                            logger.warning(msg=f"Failed to add tag {tag_id}: {e}")
            try:
                if hasattr(jpeg_exif, 'get_ifd'):
                    exif_ifd = jpeg_exif.get_ifd(EXIFIFD)
                    if exif_ifd is None:
                        exif_ifd = {}
                    tags_to_move = [
                        LENSMODEL, EXPOSURETIME, FNUMBER, ISOSPEEDRATINGS, FOCALLENGTH,
                        SHUTTERSPEEDVALUE, APERTUREVALUE, EXPOSUREBIASVALUE,
                    ]
                    for tag_id in tags_to_move:
                        if tag_id in exif:
                            exif_ifd[tag_id] = exif[tag_id]
                            if tag_id in jpeg_exif:
                                del jpeg_exif[tag_id]
            except Exception as e:
                if verbose:
                    logger.warning(msg=f"Failed to move tags to EXIF sub-IFD: {e}")
            exif_bytes = jpeg_exif.tobytes()
            image.save(final_filename, "JPEG", exif=exif_bytes, quality=100)
            if xmp_data and isinstance(xmp_data, bytes):
                _insert_xmp_into_jpeg(final_filename, xmp_data, verbose)
        if use_temp:
            if os.path.exists(out_filename):
                os.remove(out_filename)
            os.rename(temp_filename, out_filename)
    except Exception as e:
        traceback.print_tb(e.__traceback__)
        if use_temp and os.path.exists(temp_filename):
            try:
                os.remove(temp_filename)
            except Exception as ee:
                traceback.print_tb(ee.__traceback__)
        else:
            try:
                write_img(out_filename, read_img(in_filename))
            except Exception as ee:
                traceback.print_tb(ee.__traceback__)
        raise


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
            if isinstance(tag_id, int) and value and tag_id in XMP_TAG_MAP:
                config = XMP_TAG_MAP[tag_id]
                processed_value = config['processor'](value) if config['processor'] else value
                if config['type'] == 'simple':
                    xmp_elements.append(
                        f'<{config["format"]}>{processed_value}</{config["format"]}>')
                elif config['type'] == 'rdf_alt':
                    xmp_elements.append(
                        f'<{config["format"]}><rdf:Alt>'
                        f'<rdf:li xml:lang="x-default">{processed_value}</rdf:li>'
                        f'</rdf:Alt></{config["format"]}>')
                elif config['type'] == 'rdf_seq':
                    xmp_elements.append(
                        f'<{config["format"]}><rdf:Seq>'
                        f'<rdf:li>{processed_value}</rdf:li>'
                        f'</rdf:Seq></{config["format"]}>')
                elif config['type'] == 'datetime':
                    if ':' in processed_value:
                        processed_value = processed_value.replace(':', '-', 2).replace(' ', 'T')
                    xmp_elements.append(
                        f'<{config["format"]}>{processed_value}</{config["format"]}>')
                elif config['type'] == 'rational':
                    float_value = float(value) \
                        if hasattr(value, 'numerator') \
                        else (float(value) if value else 0)
                    xmp_elements.append(
                        f'<{config["format"]}>{float_value}</{config["format"]}>')
                elif config['type'] == 'mapped':
                    mapped_value = config['map'].get(value, str(value))
                    xmp_elements.append(
                        f'<{config["format"]}>{mapped_value}</{config["format"]}>')
    if xmp_elements:
        xmp_content = '\n    '.join(xmp_elements)
        return XMP_TEMPLATE.format(content=xmp_content)
    return XMP_EMPTY_TEMPLATE


def write_image_with_exif_data_png(exif, image, out_filename, color_order='auto'):
    temp_filename = out_filename + ".tmp"
    try:
        if isinstance(image, np.ndarray) and image.dtype == np.uint16:
            write_img(out_filename, image)
            return
        pil_image = _convert_to_pil_image(image, color_order)
        pnginfo, icc_profile = _prepare_png_metadata(exif)
        save_args = {'format': 'PNG', 'pnginfo': pnginfo}
        if icc_profile:
            save_args['icc_profile'] = icc_profile
        pil_image.save(temp_filename, **save_args)
        if os.path.exists(out_filename):
            os.remove(out_filename)
        os.rename(temp_filename, out_filename)
    except Exception:
        if os.path.exists(temp_filename):
            try:
                os.remove(temp_filename)
            except Exception:
                pass
        write_img(out_filename, image)
        raise


def _convert_to_pil_image(image, color_order):
    if isinstance(image, np.ndarray) and len(image.shape) == 3 and image.shape[2] == 3:
        if color_order in ['auto', 'bgr']:
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            return Image.fromarray(image_rgb)
    return Image.fromarray(image) if isinstance(image, np.ndarray) else image


def _prepare_png_metadata(exif):
    pnginfo = PngInfo()
    icc_profile = None
    xmp_data = _extract_xmp_data(exif)
    if xmp_data:
        pnginfo.add_text("XML:com.adobe.xmp", xmp_data)
    _add_exif_tags_to_pnginfo(exif, pnginfo)
    icc_profile = _extract_icc_profile(exif)
    return pnginfo, icc_profile


def _extract_xmp_data(exif):
    for key, value in exif.items():
        if isinstance(key, str) and ('xmp' in key.lower() or 'xml' in key.lower()):
            if isinstance(value, bytes):
                return value.decode('utf-8', errors='ignore')
            if isinstance(value, str):
                return value
    return create_xmp_from_exif(exif)


def _add_exif_tags_to_pnginfo(exif, pnginfo):
    for tag_id, value in exif.items():
        if value is None:
            continue
        if isinstance(tag_id, int):
            if tag_id in CAMERA_TAGS_MAP:
                _add_typed_tag(pnginfo, f"EXIF_{CAMERA_TAGS_MAP[tag_id]}", value)
            elif tag_id in EXPOSURE_TAGS_MAP:
                _add_typed_tag(pnginfo, f"EXIF_{EXPOSURE_TAGS_MAP[tag_id]}", value)
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


def _extract_icc_profile(exif):
    for key, value in exif.items():
        if (isinstance(key, str) and
            isinstance(value, bytes) and
                ('icc' in key.lower() or 'profile' in key.lower())):
            return value
    return None


def clean_data_for_tiff(data):
    if isinstance(data, str):
        return data.encode('ascii', 'ignore').decode('ascii')
    if isinstance(data, bytes):
        decoded = data.decode('utf-8', 'ignore')
        return decoded.encode('ascii', 'ignore').decode('ascii')
    if isinstance(data, IFDRational):
        return (data.numerator, data.denominator)
    return data


def write_image_with_exif_data_jpg(exif, image, out_filename, verbose):
    save_img = (image // 256).astype(np.uint8) if image.dtype == np.uint16 else image
    cv2.imwrite(out_filename, save_img, [cv2.IMWRITE_JPEG_QUALITY, 100])
    add_exif_data_to_jpg_file(exif, out_filename, out_filename, verbose)


def exif_extra_tags_for_tif(exif):
    res_x, res_y = exif.get(XRESOLUTION), exif.get(YRESOLUTION)
    resolution = (
        (res_x.numerator, res_x.denominator),
        (res_y.numerator, res_y.denominator)
    ) if res_x and res_y else (
        (720000, 10000), (720000, 10000)
    )
    exif_tags = {
        'resolution': resolution,
        'resolutionunit': exif.get(RESOLUTIONUNIT, 2),
        'software': clean_data_for_tiff(exif.get(SOFTWARE)) or constants.APP_TITLE,
        'photometric': exif.get(PHOTOMETRICINTERPRETATION, 2)
    }
    extra = []
    safe_tags = [
        MAKE, MODEL, SOFTWARE, DATETIME, ARTIST, COPYRIGHT,
        ISOSPEEDRATINGS, ORIENTATION, IMAGEWIDTH, IMAGELENGTH
    ]
    special_handling_tags = [
        EXPOSURETIME, FNUMBER, FOCALLENGTH, EXPOSUREBIASVALUE,
        SHUTTERSPEEDVALUE, APERTUREVALUE, MAXAPERTUREVALUE
    ]
    for tag_id in safe_tags:
        if tag_id in exif:
            data = exif[tag_id]
            processed_data = _process_tiff_data_safe(data)
            if processed_data:
                dtype, count, data_value = processed_data
                extra.append((tag_id, dtype, count, data_value, False))
    for tag_id in special_handling_tags:
        if tag_id in exif:
            data = exif[tag_id]
            processed_data = _process_rational_tag(data)
            if processed_data:
                dtype, count, data_value = processed_data
                extra.append((tag_id, dtype, count, data_value, False))
    for tag_id in exif:
        if tag_id in NO_COPY_TIFF_TAGS_ID:
            continue
        if tag_id in safe_tags or tag_id in special_handling_tags:
            continue
        tag_name = TAGS.get(tag_id, tag_id)
        if tag_name in NO_COPY_TIFF_TAGS:
            continue
        data = exif.get(tag_id)
        if _is_safe_to_write(data):
            processed_data = _process_tiff_data_safe(data)
            if processed_data:
                dtype, count, data_value = processed_data
                extra.append((tag_id, dtype, count, data_value, False))
    return extra, exif_tags


def _process_tiff_data_safe(data):
    if isinstance(data, IFDRational):
        return _process_rational_tag(data)
    if isinstance(data, (str, bytes)):
        clean_data = clean_data_for_tiff(data)
        if clean_data:
            return 2, len(clean_data) + 1, clean_data
    if isinstance(data, int):
        if 0 <= data <= 65535:
            return 3, 1, data
        return 4, 1, data
    if isinstance(data, float):
        return 11, 1, float(data)  # Use FLOAT only for actual floats
    if hasattr(data, '__iter__') and not isinstance(data, (str, bytes)):
        try:
            if all(isinstance(x, int) for x in data):
                return 3, len(data), tuple(data)  # Use SHORT array for integers
            clean_data = [float(x) for x in data]
            return 12, len(clean_data), tuple(clean_data)  # Use DOUBLE for floats
        except Exception:
            return None
    return None


def _process_rational_tag(data):
    if isinstance(data, IFDRational):
        numerator = data.numerator
        denominator = data.denominator if data.denominator != 0 else 1
        if denominator == 1:
            if 0 <= numerator <= 65535:
                return 3, 1, numerator  # SHORT
            return 4, 1, numerator  # LONG
        if abs(numerator) > 1000000 or abs(denominator) > 1000000:
            return 11, 1, float(data)  # Use FLOAT for very large values
        if numerator < 0:
            return 10, 1, (numerator, denominator)  # SRATIONAL
        return 5, 1, (numerator, denominator)   # RATIONAL
    return None


def _is_safe_to_write(data):
    if data is None:
        return False
    if isinstance(data, bytes) and len(data) > 10000:
        return False
    if hasattr(data, '__iter__') and not isinstance(data, (str, bytes, tuple, list)):
        return False
    return True


def write_image_with_exif_data_tif(exif, image, out_filename):
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    temp_filename = out_filename + ".tmp"
    try:
        metadata = {"description": f"image generated with {constants.APP_STRING} package"}
        extra_tags, exif_tags = exif_extra_tags_for_tif(exif)
        tifffile.imwrite(temp_filename, image, metadata=metadata, compression='adobe_deflate',
                         extratags=extra_tags, **exif_tags)
        if os.path.exists(out_filename):
            os.remove(out_filename)
        os.rename(temp_filename, out_filename)
    except Exception:
        if os.path.exists(temp_filename):
            try:
                os.remove(temp_filename)
            except Exception:
                pass
        tifffile.imwrite(out_filename, image, compression='adobe_deflate')
        raise


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
        write_image_with_exif_data_png(exif, image, out_filename, color_order=color_order)
    return exif


def save_exif_data(exif, in_filename, out_filename=None, verbose=False):
    if out_filename is None:
        out_filename = in_filename
    if exif is None:
        raise RuntimeError('No exif data provided.')
    use_temp = in_filename == out_filename
    temp_filename = out_filename + ".tmp" if use_temp else out_filename
    try:
        if extension_png(in_filename) or extension_tif(in_filename):
            if extension_tif(in_filename):
                image_new = tifffile.imread(in_filename)
            elif extension_png(in_filename):
                image_new = cv2.imread(in_filename, cv2.IMREAD_UNCHANGED)
            if extension_tif(in_filename):
                metadata = {"description": f"image generated with {constants.APP_STRING} package"}
                extra_tags, exif_tags = exif_extra_tags_for_tif(exif)
                tifffile.imwrite(temp_filename, image_new, metadata=metadata,
                                 compression='adobe_deflate',
                                 extratags=extra_tags, **exif_tags)
            elif extension_png(in_filename):
                write_image_with_exif_data_png(exif, image_new, temp_filename)
        else:
            add_exif_data_to_jpg_file(exif, in_filename, temp_filename, verbose)
        if use_temp:
            if os.path.exists(out_filename):
                os.remove(out_filename)
            os.rename(temp_filename, out_filename)
        return exif
    except Exception:
        if use_temp and os.path.exists(temp_filename):
            try:
                os.remove(temp_filename)
            except Exception:
                pass
        if extension_tif(in_filename):
            image_new = tifffile.imread(in_filename)
            tifffile.imwrite(out_filename, image_new, compression='adobe_deflate')
        elif extension_png(in_filename):
            image_new = cv2.imread(in_filename, cv2.IMREAD_UNCHANGED)
            write_img(out_filename, image_new)
        else:
            write_img(out_filename, read_img(in_filename))
        raise


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
        if tag_name.startswith('PNG_EXIF_'):
            standard_tag = tag_name[9:]
        elif tag_name.startswith('EXIF_'):
            standard_tag = tag_name[5:]
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
