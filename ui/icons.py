# file: ui/icons.py

"""Glyphs the stock Fluent set cannot draw at header size.

``FluentIcon.DICTIONARY_ADD`` puts its plus in a corner badge about one pixel
wide. At 16px that bar closes into a minus. AddTermIcon draws the same idea in
the outline style of the gear and theme icons beside it: a page with two text
lines, one-pixel strokes on the pixel grid, and a thin plus set in a gap cut
out of the page's corner, so the plus reads without a filled badge.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from qfluentwidgets.common.icon import FluentIconBase, Theme, getIconColor


class AddTermIcon(FluentIconBase):
    """Page with text lines and a corner plus, on the 16px grid."""

    def path(self, theme=Theme.AUTO) -> str:
        return ""

    def render(self, painter, rect, theme=Theme.AUTO, indexes=None, **attributes):
        color = QColor(attributes.get("fill") or getIconColor(theme))
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)
        rect = QRectF(rect)
        painter.translate(rect.x(), rect.y())
        painter.scale(rect.width() / 16, rect.height() / 16)

        # Coordinates sit on .5 so one-unit strokes fill whole pixels at 16px
        # (the header size) instead of smearing grey across two.
        pen = QPen(color, 1.0)
        pen.setCapStyle(Qt.FlatCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        # The page is clipped around the plus rather than erased: a clip never
        # touches what is already painted, so the glyph is safe on any
        # surface (an erase would punch a hole through the button itself).
        cx = cy = 12.5
        page_clip = QPainterPath()
        page_clip.addRect(QRectF(0, 0, 16, 16))
        gap = QPainterPath()
        gap.addEllipse(QPointF(cx, cy), 3.8, 3.8)
        painter.save()
        painter.setClipPath(page_clip.subtracted(gap), Qt.IntersectClip)
        painter.drawRoundedRect(QRectF(2.5, 1.5, 9, 13), 1.5, 1.5)
        painter.drawLine(QPointF(5, 4.5), QPointF(9, 4.5))
        painter.drawLine(QPointF(5, 7.5), QPointF(8, 7.5))
        painter.restore()

        painter.drawLine(QPointF(cx - 2.5, cy), QPointF(cx + 2.5, cy))
        painter.drawLine(QPointF(cx, cy - 2.5), QPointF(cx, cy + 2.5))
        painter.restore()
