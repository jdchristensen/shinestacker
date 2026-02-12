# pylint: disable=C0114, C0116, C0302, W0718, R0911, R0912, E1101
import os
import re
from PIL.TiffImagePlugin import IFDRational
from . import exif_constants as ec


def parse_xmp_to_exif(xmp_data):
    exif_data = {}
    if not xmp_data:
        return exif_data
    if isinstance(xmp_data, bytes):
        xmp_data = xmp_data.decode('utf-8', errors='ignore')
    for xmp_tag, exif_tag in ec.XMP_TO_EXIF_MAP.items():
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
    if exif_tag in [ec.EXPOSURETIME, ec.FNUMBER, ec.FOCALLENGTH]:
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
    if exif_tag == ec.ISOSPEEDRATINGS:  # ISO
        if '<rdf:li>' in value:
            matches = re.findall(r'<rdf:li>([^<]+)</rdf:li>', value)
            if matches:
                value = matches[0]
        try:
            return int(value)
        except ValueError:
            return value
    if exif_tag in [ec.DATETIME, ec.DATETIMEORIGINAL]:  # DateTime and DateTimeOriginal
        if 'T' in value:
            value = value.replace('T', ' ').replace('-', ':')
        return value
    return value


def safe_write_with_temp(out_filename, write_func, fallback_func=None):
    temp_filename = out_filename + ".tmp"
    try:
        write_func(temp_filename)
        if os.path.exists(out_filename):
            os.remove(out_filename)
        os.rename(temp_filename, out_filename)
    except Exception:
        if os.path.exists(temp_filename):
            try:
                os.remove(temp_filename)
            except Exception:
                pass
        if fallback_func:
            fallback_func(out_filename)
        raise
