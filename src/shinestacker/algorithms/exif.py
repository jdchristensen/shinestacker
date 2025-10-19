# pylint: disable=C0114, C0116, W0718, R0911, R0912, E1101, R0915, R1702, R0914, R0917, R0913
import os
import re
import io
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
    size = len(foot.decode('ascii'))
    xmp_start, xmp_end = data.find(head), data.find(foot)
    if xmp_start != -1 and xmp_end != -1:
        return re.sub(
            b'[^\x20-\x7E]', b'',
            data[xmp_start:xmp_end + size]
        ).decode().replace('\x00', '').encode()
    return None


def get_exif(exif_filename):
    if not os.path.isfile(exif_filename):
        raise RuntimeError(f"File does not exist: {exif_filename}")
    image = Image.open(exif_filename)
    if extension_tif(exif_filename):
        return image.tag_v2 if hasattr(image, 'tag_v2') else image.getexif()
    if extension_jpg(exif_filename):
        exif_data = image.getexif()
        with open(exif_filename, 'rb') as f:
            data = extract_enclosed_data_for_jpg(f.read(), b'<?xpacket', b'<?xpacket end="w"?>')
            if data is not None:
                exif_data[XMLPACKET] = data
        return exif_data
    if extension_png(exif_filename):
        exif_data = get_exif_from_png(image)
        return exif_data if exif_data else image.getexif()
    return image.getexif()


def get_exif_from_png(image):
    exif_data = {}
    try:
        exif_from_image = image.getexif()
        if exif_from_image:
            exif_data.update(dict(exif_from_image))
    except Exception:
        pass
    try:
        if hasattr(image, 'text') and image.text:
            for key, value in image.text.items():
                exif_data[f"PNG_{key}"] = value
        if hasattr(image, 'info') and image.info:
            for key, value in image.info.items():
                if key not in ['dpi', 'gamma']:
                    exif_data[f"PNG_{key}"] = value
    except Exception:
        pass
    return exif_data


def exif_extra_tags_for_tif(exif):
    logger = logging.getLogger(__name__)
    res_x, res_y = exif.get(RESOLUTIONX), exif.get(RESOLUTIONY)
    if not (res_x is None or res_y is None):
        resolution = ((res_x.numerator, res_x.denominator), (res_y.numerator, res_y.denominator))
    else:
        resolution = ((720000, 10000), (720000, 10000))
    res_u = exif.get(RESOLUTIONUNIT)
    resolutionunit = res_u if res_u is not None else 'inch'
    sw = exif.get(SOFTWARE)
    software = sw if sw is not None else "N/A"
    phint = exif.get(PHOTOMETRICINTERPRETATION)
    photometric = phint if phint is not None else None
    extra = []
    for tag_id in exif:
        tag, data = TAGS.get(tag_id, tag_id), exif.get(tag_id)
        if isinstance(data, bytes):
            try:
                if tag_id not in (IMAGERESOURCES, INTERCOLORPROFILE):
                    if tag_id == XMLPACKET:
                        data = re.sub(b'[^\x20-\x7E]', b'', data)
                    data = data.decode()
            except Exception:
                logger.warning(msg=f"Copy: can't decode EXIF tag {tag:25} [#{tag_id}]")
                data = '<<< decode error >>>'
        if isinstance(data, IFDRational):
            data = (data.numerator, data.denominator)
        if tag not in NO_COPY_TIFF_TAGS and tag_id not in NO_COPY_TIFF_TAGS_ID:
            extra.append((tag_id, *get_tiff_dtype_count(data), data, False))
        else:
            logger.debug(msg=f"Skip tag {tag:25} [#{tag_id}]")
    return extra, {'resolution': resolution, 'resolutionunit': resolutionunit,
                   'software': software, 'photometric': photometric}


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


def add_exif_data_to_jpg_file(exif, in_filenama, out_filename, verbose=False):
    logger = logging.getLogger(__name__)
    if exif is None:
        raise RuntimeError('No exif data provided.')
    if verbose:
        print_exif(exif)
    xmp_data = extract_enclosed_data_for_jpg(exif[XMLPACKET], b'<x:xmpmeta', b'</x:xmpmeta>')
    with Image.open(in_filenama) as image:
        with io.BytesIO() as buffer:
            image.save(buffer, format="JPEG", exif=exif.tobytes(), quality=100)
            jpeg_data = buffer.getvalue()
            if xmp_data is not None:
                app1_marker_pos = jpeg_data.find(b'\xFF\xE1')
                if app1_marker_pos == -1:
                    app1_marker_pos = len(jpeg_data) - 2
                updated_data = (
                    jpeg_data[:app1_marker_pos] +
                    b'\xFF\xE1' + len(xmp_data).to_bytes(2, 'big') +
                    xmp_data + jpeg_data[app1_marker_pos:]
                )
            else:
                logger.warning("Copy: can't find XMLPacket in JPG EXIF data")
                updated_data = jpeg_data
            with open(out_filename, 'wb') as f:
                f.write(updated_data)
    return exif


def create_xmp_from_exif(exif_data):
    xmp_elements = []
    if exif_data:
        for tag_id, value in exif_data.items():
            if isinstance(tag_id, int):
                if tag_id == 270 and value:  # ImageDescription
                    desc = value
                    if isinstance(desc, bytes):
                        desc = desc.decode('utf-8', errors='ignore')
                    xmp_elements.append(
                        f'<dc:description><rdf:Alt><rdf:li xml:lang="x-default">{desc}</rdf:li>'
                        '</rdf:Alt></dc:description>')
                elif tag_id == 315 and value:  # Artist
                    artist = value
                    if isinstance(artist, bytes):
                        artist = artist.decode('utf-8', errors='ignore')
                    xmp_elements.append(
                        f'<dc:creator><rdf:Seq><rdf:li>{artist}</rdf:li>'
                        '</rdf:Seq></dc:creator>')
                elif tag_id == 33432 and value:  # Copyright
                    copyright_tag = value
                    if isinstance(copyright_tag, bytes):
                        copyright_tag = copyright_tag.decode('utf-8', errors='ignore')
                    xmp_elements.append(
                        f'<dc:rights><rdf:Alt><rdf:li xml:lang="x-default">{copyright_tag}</rdf:li>'
                        '</rdf:Alt></dc:rights>')
                elif tag_id == 271 and value:  # Make
                    make = value
                    if isinstance(make, bytes):
                        make = make.decode('utf-8', errors='ignore')
                    xmp_elements.append(f'<tiff:Make>{make}</tiff:Make>')
                elif tag_id == 272 and value:  # Model
                    model = value
                    if isinstance(model, bytes):
                        model = model.decode('utf-8', errors='ignore')
                    xmp_elements.append(f'<tiff:Model>{model}</tiff:Model>')
                elif tag_id == 306 and value:  # DateTime
                    datetime_val = value
                    if isinstance(datetime_val, bytes):
                        datetime_val = datetime_val.decode('utf-8', errors='ignore')
                    if ':' in datetime_val:
                        datetime_val = datetime_val.replace(':', '-', 2).replace(' ', 'T')
                    xmp_elements.append(f'<xmp:CreateDate>{datetime_val}</xmp:CreateDate>')
                elif tag_id == 305 and value:  # Software
                    software = value
                    if isinstance(software, bytes):
                        software = software.decode('utf-8', errors='ignore')
                    xmp_elements.append(f'<xmp:CreatorTool>{software}</xmp:CreatorTool>')
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
    xmlns:exif='http://ns.adobe.com/exif/1.0/'>
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
    pil_image = _convert_to_pil_image(image, color_order, verbose, logger)
    pnginfo, icc_profile = _prepare_png_metadata(exif, verbose, logger)
    _save_png_with_metadata(pil_image, out_filename, pnginfo, icc_profile, verbose, logger)


def _convert_to_pil_image(image, color_order, verbose, logger):
    if isinstance(image, np.ndarray):
        if len(image.shape) == 3 and image.shape[2] == 3:
            if color_order in ['auto', 'bgr']:
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                if verbose:
                    logger.info(msg="Converted BGR to RGB for PIL")
                return Image.fromarray(image_rgb)
        return Image.fromarray(image)
    return image


def _prepare_png_metadata(exif, verbose, logger):
    pnginfo = PngInfo()
    icc_profile = None
    xmp_data = _extract_xmp_data(exif, verbose, logger)
    if xmp_data:
        pnginfo.add_text("XML:com.adobe.xmp", xmp_data)
        if verbose:
            logger.info(msg="Added XMP data to PNG info")
    _add_exif_tags_to_pnginfo(exif, pnginfo, verbose, logger)
    icc_profile = _extract_icc_profile(exif, verbose, logger)
    return pnginfo, icc_profile


def _extract_xmp_data(exif, verbose, logger):
    for key, value in exif.items():
        if isinstance(key, str) and ('xmp' in key.lower() or 'xml' in key.lower()):
            if isinstance(value, bytes):
                try:
                    xmp_data = value.decode('utf-8', errors='ignore')
                    if verbose:
                        logger.info(msg=f"Found existing XMP data in source: {key}")
                    return xmp_data
                except Exception:
                    continue
            elif isinstance(value, str):
                if verbose:
                    logger.info(msg=f"Found existing XMP data in source: {key}")
                return value
    if verbose:
        logger.info("Generated new XMP data from EXIF")
    return create_xmp_from_exif(exif)


def _add_exif_tags_to_pnginfo(exif, pnginfo, verbose, logger):
    for tag_id, value in exif.items():
        if value is None:
            continue
        if isinstance(tag_id, int):
            _add_exif_tag(pnginfo, tag_id, value, verbose, logger)
        elif isinstance(tag_id, str) and not tag_id.lower().startswith(('xmp', 'xml')):
            _add_png_text_tag(pnginfo, tag_id, value, verbose, logger)


def _add_exif_tag(pnginfo, tag_id, value, verbose, logger):
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
        elif hasattr(value, 'numerator'):  # IFDRational
            rational_str = f"{value.numerator}/{value.denominator}"
            pnginfo.add_text(tag_name, rational_str)
        else:
            pnginfo.add_text(tag_name, str(value))
    except Exception as e:
        if verbose:
            logger.warning(f"Could not store EXIF tag {tag_id}: {e}")


def _add_png_text_tag(pnginfo, key, value, verbose, logger):
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
    except Exception as e:
        if verbose:
            logger.warning(msg=f"Could not store PNG metadata {key}: {e}")


def _extract_icc_profile(exif, verbose, logger):
    for key, value in exif.items():
        if (isinstance(key, str) and
            isinstance(value, bytes) and
                ('icc' in key.lower() or 'profile' in key.lower())):
            if verbose:
                logger.info(f"Found ICC profile: {key}")
            return value
    return None


def _save_png_with_metadata(pil_image, out_filename, pnginfo, icc_profile, verbose, logger):
    try:
        save_args = {'format': 'PNG', 'pnginfo': pnginfo}
        if icc_profile:
            save_args['icc_profile'] = icc_profile
            if verbose:
                logger.info(msg="Saved PNG with ICC profile and metadata")
        else:
            if verbose:
                logger.info(msg="Saved PNG without ICC profile but with metadata")
        pil_image.save(out_filename, **save_args)
        if verbose:
            logger.info(msg=f"Successfully wrote PNG with metadata: {out_filename}")
    except Exception as e:
        if verbose:
            logger.error(msg=f"Failed to write PNG with metadata: {e}")
            logger.error(traceback.format_exc())
        pil_image.save(out_filename, format='PNG')


def write_image_with_exif_data(exif, image, out_filename, verbose=False, color_order='auto'):
    if exif is None:
        write_img(out_filename, image)
        return None
    if verbose:
        print_exif(exif)
    if extension_jpg(out_filename):
        cv2.imwrite(out_filename, image, [int(cv2.IMWRITE_JPEG_QUALITY), 100])
        add_exif_data_to_jpg_file(exif, out_filename, out_filename, verbose)
    elif extension_tif(out_filename):
        metadata = {"description": f"image generated with {constants.APP_STRING} package"}
        extra_tags, exif_tags = exif_extra_tags_for_tif(exif)
        tifffile.imwrite(out_filename, image, metadata=metadata, compression='adobe_deflate',
                         extratags=extra_tags, **exif_tags)
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
    if extension_tif(in_filename):
        image_new = tifffile.imread(in_filename)
    elif extension_jpg(in_filename):
        image_new = Image.open(in_filename)
    elif extension_png(in_filename):
        image_new = cv2.imread(in_filename, cv2.IMREAD_UNCHANGED)
    if extension_jpg(in_filename):
        add_exif_data_to_jpg_file(exif, in_filename, out_filename, verbose)
    elif extension_tif(in_filename):
        metadata = {"description": f"image generated with {constants.APP_STRING} package"}
        extra_tags, exif_tags = exif_extra_tags_for_tif(exif)
        tifffile.imwrite(out_filename, image_new, metadata=metadata, compression='adobe_deflate',
                         extratags=extra_tags, **exif_tags)
    elif extension_png(in_filename):
        write_image_with_exif_data_png(exif, image_new, out_filename, verbose)
    return exif


def copy_exif_from_file_to_file(exif_filename, in_filename, out_filename=None, verbose=False):
    if not os.path.isfile(exif_filename):
        raise RuntimeError(f"File does not exist: {exif_filename}")
    if not os.path.isfile(in_filename):
        raise RuntimeError(f"File does not exist: {in_filename}")
    exif = get_exif(exif_filename)
    return save_exif_data(exif, in_filename, out_filename, verbose)


def exif_dict(exif, hide_xml=True):
    if exif is None:
        return None
    exif_data = {}
    for tag_id in exif:
        tag = TAGS.get(tag_id, tag_id)
        if tag_id == XMLPACKET and hide_xml:
            data = "<<< XML data >>>"
        elif tag_id in (IMAGERESOURCES, INTERCOLORPROFILE):
            data = "<<< Photoshop data >>>"
        elif tag_id == STRIPOFFSETS:
            data = "<<< Strip offsets >>>"
        elif tag_id == STRIPBYTECOUNTS:
            data = "<<< Strip byte counts >>>"
        else:
            data = exif.get(tag_id) if hasattr(exif, 'get') else exif[tag_id]
        if isinstance(data, bytes):
            try:
                data = data.decode()
            except Exception:
                pass
        exif_data[tag] = (tag_id, data)
    return exif_data


def print_exif(exif, hide_xml=True):
    exif_data = exif_dict(exif, hide_xml)
    if exif_data is None:
        raise RuntimeError('Image has no exif data.')
    logger = logging.getLogger(__name__)
    for tag, (tag_id, data) in exif_data.items():
        if isinstance(data, IFDRational):
            data = f"{data.numerator}/{data.denominator}"
        if isinstance(tag_id, int):
            logger.info(msg=f"{tag:25} [#{tag_id:5d}]: {data}")
        else:
            logger.info(msg=f"{tag:25} [ {tag_id:20} ]: {str(data)[:100]}...")
