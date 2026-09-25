# file: ui/icons.py

"""Glyphs the stock Fluent set cannot draw at header size.

``FluentIcon.DICTIONARY_ADD`` puts its plus in a corner badge about one pixel
wide. At 16px that bar closes into a minus. Here the badge is two thirds the
height of the notebook and sits in front of it, so the plus stays readable.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath
from qfluentwidgets.common.icon import FluentIconBase, Theme, getIconColor


def _plus(cx: float, cy: float, span: float, thick: float) -> QPainterPath:
    half = span / 2
    t = thick / 2
    pts = [
        (cx - half, cy - t),
        (cx - t, cy - t),
        (cx - t, cy - half),
        (cx + t, cy - half),
        (cx + t, cy - t),
        (cx + half, cy - t),
        (cx + half, cy + t),
        (cx + t, cy + t),
        (cx + t, cy + half),
        (cx - t, cy + half),
        (cx - t, cy + t),
        (cx - half, cy + t),
    ]
    path = QPainterPath()
    path.moveTo(*pts[0])
    for x, y in pts[1:]:
        path.lineTo(x, y)
    path.closeSubpath()
    return path


class AddTermIcon(FluentIconBase):
    """Notebook with a corner plus, drawn to stay legible at 16px."""

    def path(self, theme=Theme.AUTO) -> str:
        return ""

    def render(self, painter, rect, theme=Theme.AUTO, indexes=None, **attributes):
        color = QColor(attributes.get("fill") or getIconColor(theme))
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(Qt.NoPen)
        painter.setBrush(color)
        rect = QRectF(rect)
        painter.translate(rect.x(), rect.y())
        painter.scale(rect.width() / 16, rect.height() / 16)

        # Notebook on the left, badge in front of its lower corner. The
        # circle stays two thirds of the notebook's height. Strokes are near
        # one pixel at the 18px header size so they match the gear beside it.
        page_h = 14.4
        badge = page_h * 2 / 3
        stroke = 0.92
        page = QPainterPath()
        page.addRoundedRect(QRectF(0.4, 0.35, 10.6, page_h), 1.0, 1.0)
        hole = QPainterPath()
        hole.addRoundedRect(
            QRectF(0.4 + stroke, 0.35 + stroke, 10.6 - 2 * stroke, page_h - 2 * stroke),
            0.25,
            0.25,
        )
        circle = QPainterPath()
        circle.addEllipse(QRectF(16 - 0.4 - badge, 16 - 0.4 - badge, badge, badge))
        # The page must not fill the badge, or the plus hole paints shut.
        painter.drawPath(page.subtracted(hole).subtracted(circle))
        painter.drawRoundedRect(QRectF(2.2, 1.9, 5.7, 0.95), 0.35, 0.35)
        painter.drawPath(circle)
        painter.setCompositionMode(QPainter.CompositionMode_DestinationOut)
        painter.setBrush(QColor(0, 0, 0, 255))
        cx = 16 - 0.4 - badge / 2
        cy = 16 - 0.4 - badge / 2
        painter.drawPath(_plus(cx, cy, badge * 0.78, 1.4))
        painter.restore()
