# file: ui/history_dialog.py

"""
Full history: search, filters and per-day volume over the Pro encrypted store.

Opens on every tier. On Free the form is there but locked — filters, the
volume chart and per-entry delete are disabled under a "this is Pro" banner,
and the list shows only the current session. Seeing the tool is the pitch.

Results load in pages of `PAGE_SIZE` as the list is scrolled, so a year of
history never builds thousands of rows up front.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import List, Optional, Tuple

from PySide6.QtCore import QDate, QPoint, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from qframelesswindow import FramelessDialog, StandardTitleBar
from qfluentwidgets import (
    Action,
    CalendarPicker,
    ComboBox,
    FluentIcon as FIF,
    MessageBox,
    PrimaryPushButton,
    PushButton,
    RoundMenu,
    SearchLineEdit,
    Theme,
    setTheme,
)

from i18n import t
from ui import style
from ui.history_manager import ALL_KINDS, HistoryEntry, HistoryManager, kind_label
from ui.style import dialog_qss

PAGE_SIZE = 200
SEARCH_DEBOUNCE_MS = 250

# Period combo: (catalog key, days back or None). "custom" shows the pickers.
PERIODS = (
    ("history_dialog.period.today", 0),
    ("history_dialog.period.week", 6),
    ("history_dialog.period.month", 29),
    ("history_dialog.period.all", None),
    ("history_dialog.period.custom", "custom"),
)
_DEFAULT_PERIOD = 2  # last 30 days


def _fmt_chars(n: int) -> str:
    return f"{n:,}".replace(",", " ")


class _VolumeBars(QWidget):
    """Per-day bar chart (characters per day). Click a bar → `day_clicked`."""

    day_clicked = Signal(object)  # datetime.date

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(64)
        self.setMouseTracking(True)
        self._days: List[Tuple[date, int, int]] = []
        self._selected: Optional[date] = None

    def set_data(self, days: List[Tuple[date, int, int]], selected: Optional[date] = None):
        self._days = days
        self._selected = selected
        self.update()

    def _layout(self) -> List[Tuple[QRect, Tuple[date, int, int]]]:
        if not self._days:
            return []
        w, h = self.width(), self.height() - 4
        n = len(self._days)
        slot = w / n
        bar_w = max(1, min(18, int(slot * 0.7)))
        top = max(c for _, _, c in self._days) or 1
        rects = []
        for i, day in enumerate(self._days):
            bh = max(2, int(h * day[2] / top))
            x = int(i * slot + (slot - bar_w) / 2)
            rects.append((QRect(x, h - bh + 2, bar_w, bh), day))
        return rects

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        accent = QColor(style.palette().ACCENT)
        muted = QColor(accent)
        muted.setAlpha(110 if self.isEnabled() else 40)
        for rect, day in self._layout():
            color = accent if (self._selected == day[0] and self.isEnabled()) else muted
            p.setPen(Qt.NoPen)
            p.setBrush(color)
            p.drawRoundedRect(rect, 2, 2)
        p.end()

    def _day_at(self, pos: QPoint):
        for rect, day in self._layout():
            hit = QRect(rect.x() - 2, 0, rect.width() + 4, self.height())
            if hit.contains(pos):
                return day
        return None

    def mouseMoveEvent(self, event):
        day = self._day_at(event.position().toPoint())
        if day is None:
            self.setToolTip("")
            self.unsetCursor()
        else:
            self.setCursor(Qt.PointingHandCursor)
            self.setToolTip(t(
                "history_dialog.volume.tooltip",
                day=day[0].strftime("%d.%m.%Y"), count=day[1], chars=_fmt_chars(day[2]),
            ))
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.isEnabled():
            day = self._day_at(event.position().toPoint())
            if day is not None:
                self.day_clicked.emit(day[0])
        super().mouseReleaseEvent(event)


class HistoryDialog(FramelessDialog):
    """Search and browse the history. `entry_chosen` loads one into the main
    window (same path as a feed click); `license_requested` opens the License
    page from the Free banner."""

    entry_chosen = Signal(HistoryEntry)
    license_requested = Signal()

    def __init__(self, history: HistoryManager, parent=None):
        super().__init__(parent)
        self._history = history
        self._pro = history.persistent
        self._offset = 0
        self._exhausted = False
        self._day_filter: Optional[date] = None
        self._closed = False

        self.setTitleBar(StandardTitleBar(self))
        self.titleBar.minBtn.hide()
        self.titleBar.setDoubleClickEnabled(False)
        try:
            self.titleBar.iconLabel.hide()
        except Exception:
            pass
        self.setWindowTitle(t("history_dialog.title"))
        self.titleBar.setTitle(t("history_dialog.title"))
        self.setMinimumSize(640, 560)
        self.resize(760, 680)

        setTheme(Theme.DARK if style.is_dark() else Theme.LIGHT)
        self.setStyleSheet(dialog_qss(style.palette()))

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(SEARCH_DEBOUNCE_MS)
        self._search_timer.timeout.connect(self.reload)

        self._build_ui()
        self._apply_gate()
        self._history.changed.connect(self.reload)
        self.reload()

    # ---------- UI ----------

    def _build_ui(self):
        root = QVBoxLayout(self)
        title_bar_h = max(self.titleBar.height(), 32)
        root.setContentsMargins(20, title_bar_h + 6, 20, 18)
        root.setSpacing(10)

        title = QLabel(t("history_dialog.title"))
        title.setObjectName("sectionTitle")
        root.addWidget(title)

        # Free banner — the pitch, with a way to act on it.
        self.pro_banner = QFrame()
        self.pro_banner.setObjectName("card")
        banner = QHBoxLayout(self.pro_banner)
        banner.setContentsMargins(14, 10, 14, 10)
        banner_text = QLabel(t("history_dialog.pro_banner"))
        banner_text.setWordWrap(True)
        banner.addWidget(banner_text, stretch=1)
        self.get_pro_btn = PrimaryPushButton(t("license.button.buy"))
        self.get_pro_btn.clicked.connect(self._on_get_pro)
        banner.addWidget(self.get_pro_btn)
        root.addWidget(self.pro_banner)

        # Filters.
        filters = QHBoxLayout()
        filters.setSpacing(8)
        self.search_edit = SearchLineEdit()
        self.search_edit.setPlaceholderText(t("history_dialog.search.placeholder"))
        self.search_edit.textChanged.connect(lambda _: self._search_timer.start())
        self.search_edit.searchSignal.connect(lambda _: self.reload())
        self.search_edit.clearSignal.connect(self.reload)
        filters.addWidget(self.search_edit, stretch=1)

        self.kind_combo = ComboBox()
        self.kind_combo.addItem(t("history_dialog.kind.all"))
        for kind in ALL_KINDS:
            self.kind_combo.addItem(kind_label(kind))
        self.kind_combo.currentIndexChanged.connect(lambda _: self.reload())
        filters.addWidget(self.kind_combo)

        self.period_combo = ComboBox()
        for key, _days in PERIODS:
            self.period_combo.addItem(t(key))
        self.period_combo.setCurrentIndex(_DEFAULT_PERIOD)
        self.period_combo.currentIndexChanged.connect(self._on_period_changed)
        filters.addWidget(self.period_combo)
        root.addLayout(filters)

        # Custom range pickers (shown for the "custom" period only).
        self.range_row = QWidget()
        range_layout = QHBoxLayout(self.range_row)
        range_layout.setContentsMargins(0, 0, 0, 0)
        range_layout.setSpacing(8)
        range_layout.addWidget(QLabel(t("history_dialog.range.from")))
        self.from_picker = CalendarPicker()
        self.from_picker.setDate(QDate.currentDate().addDays(-29))
        self.from_picker.dateChanged.connect(lambda _: self.reload())
        range_layout.addWidget(self.from_picker)
        range_layout.addWidget(QLabel(t("history_dialog.range.to")))
        self.to_picker = CalendarPicker()
        self.to_picker.setDate(QDate.currentDate())
        self.to_picker.dateChanged.connect(lambda _: self.reload())
        range_layout.addWidget(self.to_picker)
        range_layout.addStretch(1)
        self.range_row.hide()
        root.addWidget(self.range_row)

        # Volume by day.
        vol_head = QHBoxLayout()
        vol_title = QLabel(t("history_dialog.volume.title"))
        vol_title.setObjectName("fieldLabel")
        vol_head.addWidget(vol_title)
        vol_head.addStretch(1)
        self.day_reset_btn = PushButton(t("history_dialog.volume.reset_day"))
        self.day_reset_btn.clicked.connect(self._clear_day_filter)
        self.day_reset_btn.hide()
        vol_head.addWidget(self.day_reset_btn)
        root.addLayout(vol_head)
        self.volume = _VolumeBars()
        self.volume.day_clicked.connect(self._on_day_clicked)
        root.addWidget(self.volume)

        self.summary_label = QLabel("")
        self.summary_label.setObjectName("sectionHint")
        root.addWidget(self.summary_label)

        # Results.
        self.list = QListWidget()
        self.list.setObjectName("historyList")
        self.list.setWordWrap(True)
        self.list.setUniformItemSizes(False)
        self.list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._on_context_menu)
        # itemActivated alone: on Windows it already fires on double-click (and
        # Enter). Wiring itemDoubleClicked too ran the handler twice per click.
        self.list.itemActivated.connect(self._on_item_activated)
        self.list.verticalScrollBar().valueChanged.connect(self._maybe_load_more)
        root.addWidget(self.list, stretch=1)

        self.empty_label = QLabel(t("history_dialog.empty"))
        self.empty_label.setObjectName("sectionHint")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.hide()
        root.addWidget(self.empty_label)

        # Footer.
        footer = QHBoxLayout()
        self.total_label = QLabel("")
        self.total_label.setObjectName("sectionHint")
        footer.addWidget(self.total_label, stretch=1)
        self.clear_btn = PushButton(FIF.DELETE, t("history.clear.button"))
        self.clear_btn.clicked.connect(self._on_clear)
        footer.addWidget(self.clear_btn)
        close_btn = PushButton(t("history_dialog.close"))
        close_btn.clicked.connect(self.accept)
        footer.addWidget(close_btn)
        root.addLayout(footer)

    def _apply_gate(self):
        """Free: everything that is a Pro capability is visibly there but off."""
        pro = self._pro
        self.pro_banner.setVisible(not pro)
        for w in (self.search_edit, self.kind_combo, self.period_combo,
                  self.range_row, self.volume, self.day_reset_btn):
            w.setEnabled(pro)
        if not pro:
            self.search_edit.setToolTip(t("history_dialog.locked_tooltip"))
            self.kind_combo.setToolTip(t("history_dialog.locked_tooltip"))
            self.period_combo.setToolTip(t("history_dialog.locked_tooltip"))
            self.volume.setToolTip(t("history_dialog.locked_tooltip"))

    # ---------- filters ----------

    def _date_range(self) -> Tuple[Optional[date], Optional[date]]:
        if self._day_filter is not None:
            return self._day_filter, self._day_filter
        _key, days = PERIODS[self.period_combo.currentIndex()]
        today = date.today()
        if days == "custom":
            lo = self.from_picker.getDate().toPython()
            hi = self.to_picker.getDate().toPython()
            if lo > hi:
                lo, hi = hi, lo
            return lo, hi
        if days is None:
            return None, None
        return today - timedelta(days=days), today

    def _filters(self) -> dict:
        lo, hi = self._date_range()
        i = self.kind_combo.currentIndex()
        return {
            "text": self.search_edit.text().strip() or None,
            "kinds": [ALL_KINDS[i - 1]] if i > 0 else None,
            "date_from": lo,
            "date_to": hi,
        }

    def _on_period_changed(self, index: int):
        self.range_row.setVisible(PERIODS[index][1] == "custom")
        self._day_filter = None
        self.day_reset_btn.hide()
        self.reload()

    def _on_day_clicked(self, day: date):
        self._day_filter = day
        self.day_reset_btn.show()
        self.reload()

    def _clear_day_filter(self):
        self._day_filter = None
        self.day_reset_btn.hide()
        self.reload()

    # ---------- data ----------

    def reload(self):
        self._pro = self._history.persistent
        self._apply_gate()
        self.list.clear()
        self._offset = 0
        self._exhausted = False
        if self._pro:
            self._load_page()
            self._refresh_volume()
        else:
            for entry in self._history.query():
                self._add_item(entry)
            self._exhausted = True
            # A faded sample, not real data: shows what the locked chart does.
            today = date.today()
            sample = (3, 5, 2, 6, 4, 7, 3, 8, 5, 4, 6, 9, 5, 3, 7, 6, 4, 8, 6, 5)
            self.volume.set_data([
                (today - timedelta(days=len(sample) - 1 - i), 1, v)
                for i, v in enumerate(sample)
            ])
            self.summary_label.setText("")
        self._refresh_totals()
        empty = self.list.count() == 0
        self.empty_label.setVisible(empty)

    def _load_page(self):
        if self._exhausted:
            return
        page = self._history.query(limit=PAGE_SIZE, offset=self._offset, **self._filters())
        for entry in page:
            self._add_item(entry)
        self._offset += len(page)
        if len(page) < PAGE_SIZE:
            self._exhausted = True

    def _maybe_load_more(self, value: int):
        bar = self.list.verticalScrollBar()
        if self._pro and not self._exhausted and value >= bar.maximum() - 40:
            self._load_page()

    def _refresh_volume(self):
        # The chart always spans the whole period, even with one day selected.
        saved, self._day_filter = self._day_filter, None
        lo, hi = self._date_range()
        self._day_filter = saved
        days = self._history.daily_volume(lo, hi)
        chart = days
        if lo is not None and hi is not None and (hi - lo).days <= 92:
            # Short ranges show empty days too, so the chart reads as a calendar.
            by_day = {d[0]: d for d in days}
            chart = [by_day.get(lo + timedelta(days=i), (lo + timedelta(days=i), 0, 0))
                     for i in range((hi - lo).days + 1)]
        self.volume.set_data(chart, selected=self._day_filter)
        filt = self._filters()
        if self._day_filter is not None:
            days = [d for d in days if d[0] == self._day_filter]
        count = sum(d[1] for d in days)
        chars = sum(d[2] for d in days)
        if filt["text"] or filt["kinds"]:
            self.summary_label.setText(t(
                "history_dialog.summary.filtered",
                count=count, chars=_fmt_chars(chars), shown=self.list.count(),
            ))
        else:
            self.summary_label.setText(t(
                "history_dialog.summary", count=count, chars=_fmt_chars(chars),
            ))

    def _refresh_totals(self):
        count, chars, oldest = self._history.totals()
        if count == 0:
            self.total_label.setText(t("history.status.empty"))
        elif self._pro:
            self.total_label.setText(t(
                "history.status.stored",
                count=count, chars=_fmt_chars(chars),
                since=oldest.strftime("%d.%m.%Y") if oldest else "—",
            ))
        else:
            self.total_label.setText(t("history.status.session", count=count))

    def _add_item(self, entry: HistoryEntry):
        label = kind_label(entry.kind, entry.kind.title())
        direction = entry.meta.get("direction") if entry.meta else None
        if direction:
            label = f"{label} · {direction}"
        flat = " ".join(entry.text.split())
        if len(flat) > 240:
            flat = flat[:240].rstrip() + "…"
        stamp = entry.timestamp.strftime("%d.%m.%Y %H:%M")
        item = QListWidgetItem(f"{stamp}  ·  {label}\n{flat}")
        item.setData(Qt.UserRole, entry)
        self.list.addItem(item)

    # ---------- actions ----------

    def _entry_of(self, item: Optional[QListWidgetItem]) -> Optional[HistoryEntry]:
        return item.data(Qt.UserRole) if item is not None else None

    def _on_item_activated(self, item: QListWidgetItem):
        entry = self._entry_of(item)
        if entry is not None:
            self.entry_chosen.emit(entry)
            self.accept()

    def _on_context_menu(self, pos: QPoint):
        item = self.list.itemAt(pos)
        entry = self._entry_of(item)
        if entry is None:
            return
        menu = RoundMenu(parent=self)
        open_action = Action(FIF.EDIT, t("history_dialog.menu.open"))
        open_action.triggered.connect(lambda: self._on_item_activated(item))
        menu.addAction(open_action)
        copy_action = Action(FIF.COPY, t("history_dialog.menu.copy"))
        copy_action.triggered.connect(lambda: QApplication.clipboard().setText(entry.text))
        menu.addAction(copy_action)
        delete_action = Action(FIF.DELETE, t("history_dialog.menu.delete"))
        delete_action.setEnabled(self._pro and entry.id is not None)
        delete_action.triggered.connect(lambda: self._history.delete(entry.id))
        menu.addAction(delete_action)
        menu.exec(self.list.mapToGlobal(pos))

    def _on_clear(self):
        box = MessageBox(
            t("history.clear.confirm.title"),
            t("history.clear.confirm.text"),
            self,
        )
        box.yesButton.setText(t("history.clear.button"))
        box.cancelButton.setText(t("common.cancel"))
        if box.exec():
            self._history.clear()

    def _on_get_pro(self):
        self.license_requested.emit()
        self.accept()

    def done(self, result):
        # done() can run more than once (accept, then the window closing); a
        # second disconnect makes PySide print a RuntimeWarning, so do it once.
        if not self._closed:
            self._closed = True
            try:
                self._history.changed.disconnect(self.reload)
            except (RuntimeError, TypeError):
                pass
        super().done(result)
