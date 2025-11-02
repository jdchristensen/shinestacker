# pylint: disable=C0114, C0115, C0116, E0611, W0718, R0912
from fractions import Fraction
from xml.dom import minidom
from PIL.TiffImagePlugin import IFDRational
from PySide6.QtWidgets import QLabel, QTextEdit
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase
from .. algorithms.exif import exif_dict
from .. gui.config_dialog import ConfigDialog


class ExifData(ConfigDialog):
    def __init__(self, exif, title="EXIF Data", parent=None, show_buttons=True):
        self.exif = exif
        super().__init__(title, parent)
        self.reset_button.setVisible(False)
        self.cancel_button.setVisible(show_buttons)
        if not show_buttons:
            self.ok_button.setFixedWidth(100)
            self.button_box.setAlignment(Qt.AlignCenter)

    def format_aperture(self, value):
        if isinstance(value, IFDRational):
            if value.denominator == 0:
                return "f/>1024"
            aperture_value = value.numerator / value.denominator
            return f"f/{aperture_value:.1f}"
        if isinstance(value, (int, float)):
            return f"f/{float(value):.1f}"
        return str(value)

    def format_exposure_time(self, value):
        if isinstance(value, IFDRational):
            exposure_time = value.numerator / value.denominator
        elif isinstance(value, (int, float)):
            exposure_time = float(value)
        else:
            return str(value)
        if exposure_time >= 0.5:
            return f"{exposure_time:.1f} s"
        if isinstance(value, IFDRational):
            return f"{value.numerator}/{value.denominator} s"
        frac = Fraction(exposure_time).limit_denominator(1000)
        return f"{frac.numerator}/{frac.denominator} s"

    def format_date_time(self, value):
        if not isinstance(value, str):
            return str(value)
        try:
            if ':' in value and ' ' in value:
                date_part, time_part = value.split(' ', 1)
                year, month, day = date_part.split(':', 2)
                return f"{day}/{month}/{year} {time_part}"
            return value
        except (ValueError, IndexError):
            return value

    def is_likely_xml(self, text):
        if not isinstance(text, str):
            return False
        text = text.strip()
        return (text.startswith('<?xml') or
                text.startswith('<x:xmpmeta') or
                text.startswith('<rdf:RDF') or
                text.startswith('<?xpacket') or
                (text.startswith('<') and text.endswith('>') and
                 any(tag in text for tag in ['<rdf:', '<xmp:', '<dc:', '<tiff:'])))

    def prettify_xml(self, xml_string):
        try:
            parsed = minidom.parseString(xml_string)
            pretty_xml = parsed.toprettyxml(indent="  ")
            lines = [line for line in pretty_xml.split('\n') if line.strip()]
            if lines and lines[0].startswith('<?xml version="1.0" ?>'):
                lines = lines[1:]
            return '\n'.join(lines)
        except Exception:
            return xml_string

    def create_form_content(self):
        if self.exif is None:
            data = {}
        else:
            data = exif_dict(self.exif)
        if len(data) > 0:
            for k, (_, d) in data.items():
                if k in ['FNumber', 'ApertureValue']:
                    display_value = self.format_aperture(d)
                elif k in ['ExposureTime', 'ShutterSpeedValue']:
                    display_value = self.format_exposure_time(d)
                elif k in ['DateTime', 'DateTimeOriginal', 'DateTimeDigitized']:
                    display_value = self.format_date_time(d)
                elif isinstance(d, IFDRational):
                    display_value = f"{d.numerator}/{d.denominator}"
                else:
                    display_value = str(d)
                d_str = display_value
                if "<<<" not in d_str and k != 'IPTCNAA':
                    if len(d_str) <= 40:
                        self.container_layout.addRow(f"<b>{k}:</b>", QLabel(d_str))
                    else:
                        if self.is_likely_xml(d_str):
                            d_str = self.prettify_xml(d_str)
                        text_edit = QTextEdit()
                        text_edit.setPlainText(d_str)
                        text_edit.setReadOnly(True)
                        text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
                        text_edit.setLineWrapMode(QTextEdit.WidgetWidth)
                        text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                        text_edit.setFixedWidth(400)
                        font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
                        font.setPointSize(10)
                        text_edit.setFont(font)
                        font.setPointSize(11)
                        text_edit.setFont(font)
                        text_edit.setFixedHeight(200)
                        text_edit.setFixedHeight(100)
                        self.container_layout.addRow(f"<b>{k}:</b>", text_edit)
        else:
            self.container_layout.addRow("No EXIF Data", QLabel(''))
