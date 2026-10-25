"""Native text layout helpers for language labels and plain-text reading areas."""
import math

from PySide6.QtCore import QObject, Property, QPointF, Signal, Slot, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QTextBlockFormat, QTextCursor, QTextLayout, QTextOption
from PySide6.QtQuick import QQuickPaintedItem


class TextLineSpacing(QObject):
    """Apply paragraph line spacing while keeping TextArea contents plain text."""

    documentChanged = Signal()
    lineHeightChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._document = None
        self._line_height = 1.0
        self._applying = False

    def get_document(self):
        return self._document

    def set_document(self, value):
        if self._document is value:
            return
        if self._document is not None:
            self._document.textDocument().contentsChanged.disconnect(self.apply)
        self._document = value
        if value is not None:
            value.textDocument().contentsChanged.connect(self.apply)
        self.apply()
        self.documentChanged.emit()

    document = Property(QObject, get_document, set_document, notify=documentChanged)

    def get_line_height(self):
        return self._line_height

    def set_line_height(self, value):
        if value <= 0 or self._line_height == value:
            return
        self._line_height = value
        self.apply()
        self.lineHeightChanged.emit()

    lineHeight = Property(float, get_line_height, set_line_height, notify=lineHeightChanged)

    @Slot()
    def apply(self):
        if self._document is None or self._applying:
            return
        document = self._document.textDocument()
        height = self._line_height * 100
        height_type = QTextBlockFormat.LineHeightTypes.ProportionalHeight.value
        block = document.begin()
        while block.isValid():
            current = block.blockFormat()
            if current.lineHeight() != height or current.lineHeightType() != height_type:
                break
            block = block.next()
        else:
            return

        self._applying = True
        try:
            had_undo, had_redo = document.isUndoAvailable(), document.isRedoAvailable()
            cursor = QTextCursor(document)
            # Formatting follows an edit without becoming a separate Undo step.
            if had_undo:
                cursor.joinPreviousEditBlock()
            else:
                cursor.beginEditBlock()
            cursor.select(QTextCursor.SelectionType.Document)
            formatting = QTextBlockFormat()
            formatting.setLineHeight(height, height_type)
            cursor.mergeBlockFormat(formatting)
            cursor.endEditBlock()
            if not had_undo and not had_redo:
                document.clearUndoRedoStacks()
        finally:
            self._applying = False


class LanguageCaption(QQuickPaintedItem):
    """Center the visible width and optical height, including fallback/combining glyphs."""

    textChanged = Signal()
    fontChanged = Signal()
    colorChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._text = ""
        self._font = QFont("MiSans")
        self._color = QColor("#1d1d1f")
        self._render_key = None
        self._rendered = QImage()
        self.setAntialiasing(True)
        # The bitmap already contains antialiased text. Filtering it again in
        # the scene graph shifts thin strokes at fractional display scales.
        self.setSmooth(False)
        self.widthChanged.connect(self.update)
        self.heightChanged.connect(self.update)

    def get_text(self):
        return self._text

    def set_text(self, value):
        if self._text == value:
            return
        self._text = value
        self.update()
        self.textChanged.emit()

    text = Property(str, get_text, set_text, notify=textChanged)

    def get_font(self):
        return QFont(self._font)

    def set_font(self, value):
        font = QFont(value)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        if self._font == font:
            return
        self._font = font
        self.update()
        self.fontChanged.emit()

    font = Property(QFont, get_font, set_font, notify=fontChanged)

    def get_color(self):
        return QColor(self._color)

    def set_color(self, value):
        color = QColor(value)
        if self._color == color:
            return
        self._color = color
        self.update()
        self.colorChanged.emit()

    color = Property(QColor, get_color, set_color, notify=colorChanged)

    def paint(self, painter):
        if not self._text or self.width() <= 0 or self.height() <= 0:
            return
        # Qt's software scene graph can keep the image DPR at 1 while putting
        # the real, sometimes slightly anisotropic, scale in the painter.
        transform = painter.deviceTransform()
        scale_x = math.hypot(transform.m11(), transform.m12())
        scale_y = math.hypot(transform.m21(), transform.m22())
        key = (self._text, self._font.key(), self._color.rgba(), self.width(), self.height(), scale_x, scale_y)
        if key != self._render_key:
            self._rendered = self._render_caption(scale_x, scale_y)
            self._render_key = key
        # Copy the measured bitmap at its native pixel ratio. No second text
        # renderer can introduce a different baseline or fallback-font bearing.
        painter.save()
        painter.resetTransform()
        ratio = painter.device().devicePixelRatioF()
        self._rendered.setDevicePixelRatio(ratio)
        painter.drawImage(QPointF(transform.dx() / ratio, transform.dy() / ratio), self._rendered)
        painter.restore()

    def _render_caption(self, scale_x, scale_y):
        target_width = self.width() * scale_x
        target_height = self.height() * scale_y
        width = math.ceil(target_width - 1e-9)
        height = math.ceil(target_height - 1e-9)
        padding = math.ceil(4 * max(scale_x, scale_y))
        source = QImage(width + padding * 2, height + padding * 2,
                        QImage.Format.Format_ARGB32_Premultiplied)
        source.fill(Qt.GlobalColor.transparent)
        # Shape and rasterize in the paint thread: fallback glyphs and their
        # marks must come from the same layout and native rendering device.
        layout = QTextLayout(self._text, self._font)
        option = QTextOption()
        option.setWrapMode(QTextOption.WrapMode.NoWrap)
        option.setUseDesignMetrics(True)
        layout.setTextOption(option)
        layout.setCacheEnabled(True)
        layout.beginLayout()
        line = layout.createLine()
        if line.isValid():
            line.setLineWidth(100000)
            line.setPosition(QPointF())
        layout.endLayout()
        if line.isValid():
            rect = line.naturalTextRect()
            painter = QPainter(source)
            painter.scale(scale_x, scale_y)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
            painter.setPen(Qt.GlobalColor.white)
            layout.draw(painter, QPointF(source.width() / scale_x / 2 - rect.center().x(),
                                         source.height() / scale_y / 2 - rect.center().y()))
            painter.end()

        coverage = source.convertToFormat(QImage.Format.Format_Alpha8)
        pixels = bytes(coverage.constBits())
        stride = coverage.bytesPerLine()
        total = weighted_y = 0
        left, right = coverage.width(), -1
        for y in range(coverage.height()):
            row = pixels[y * stride:y * stride + coverage.width()]
            weight = sum(row)
            if weight:
                left = min(left, len(row) - len(row.lstrip(b"\0")))
                right = max(right, len(row.rstrip(b"\0")) - 1)
                total += weight
                weighted_y += weight * (y + 0.5)

        centered = QImage(width, height, QImage.Format.Format_Alpha8)
        centered.fill(0)
        if total:
            # Horizontal: center the whole word's visible extent, avoiding a
            # density-based sideways shift for uneven scripts such as Myanmar.
            start_x = round((left + right + 1) / 2 - target_width / 2)
            # Vertical: center actual stroke coverage. A bounding box alone
            # gives accents/descenders disproportionate influence on the body.
            origin_y = weighted_y / total - target_height / 2
            start_y = math.floor(origin_y)
            fraction = origin_y - start_y
            output = centered.bits()
            output_stride = centered.bytesPerLine()
            for y in range(height):
                row0, row1 = y + start_y, y + start_y + 1
                for x in range(width):
                    column = x + start_x
                    if not 0 <= column < coverage.width():
                        continue
                    a = pixels[row0 * stride + column] if 0 <= row0 < coverage.height() else 0
                    b = pixels[row1 * stride + column] if 0 <= row1 < coverage.height() else 0
                    output[y * output_stride + x] = round(a * (1 - fraction) + b * fraction)
        image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(self._color)
        painter = QPainter(image)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
        painter.drawImage(QPointF(), centered)
        painter.end()
        return image
