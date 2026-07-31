from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

try:
    from PySide6 import QtCore, QtGui, QtWidgets
    Signal = QtCore.Signal
except ImportError:
    from PySide2 import QtCore, QtGui, QtWidgets
    Signal = QtCore.Signal

from Workshop.control.serialize import SHAPE_LIBRARY_DIR


SHAPE_ICON_LIBRARY_DIR = Path(__file__).resolve().parent / "shape_icon_library"

SUPPORTED_IMAGE_EXTENSIONS = (
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
)


@dataclass(frozen=True)
class ControlShapeInfo:
    """Information about one available control shape."""

    name: str
    json_path: Path
    icon_path: Path | None = None


def find_shape_icon(
    shape_name: str,
    icon_library: Path,
) -> Path | None:
    """Find an icon matching a control shape name."""

    for extension in SUPPORTED_IMAGE_EXTENSIONS:
        icon_path = icon_library / f"{shape_name}{extension}"

        if icon_path.exists():
            return icon_path

    return None


def get_control_shape_library(
    shape_library: Path = SHAPE_LIBRARY_DIR,
    icon_library: Path = SHAPE_ICON_LIBRARY_DIR,
) -> list[ControlShapeInfo]:
    """Read all available control shapes from the JSON shape library."""

    if not shape_library.exists():
        return []

    shape_info: list[ControlShapeInfo] = []

    for json_path in sorted(
        shape_library.glob("*.json"),
        key=lambda path: path.stem.lower(),
    ):
        shape_name = json_path.stem

        shape_info.append(
            ControlShapeInfo(
                name=shape_name,
                json_path=json_path,
                icon_path=find_shape_icon(
                    shape_name=shape_name,
                    icon_library=icon_library,
                ),
            )
        )

    return shape_info

class FlowLayout(QtWidgets.QLayout):
    """A layout that wraps widgets onto new rows."""

    def __init__(
        self,
        parent: QtWidgets.QWidget | None = None,
        margin: int = 0,
        horizontal_spacing: int = 4,
        vertical_spacing: int = 4,
    ) -> None:
        super().__init__(parent)

        self._items: list[QtWidgets.QLayoutItem] = []
        self._horizontal_spacing = horizontal_spacing
        self._vertical_spacing = vertical_spacing

        self.setContentsMargins(margin, margin, margin, margin)

    def __del__(self) -> None:
        while self.count():
            self.takeAt(0)

    def addItem(self, item: QtWidgets.QLayoutItem) -> None:
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int) -> QtWidgets.QLayoutItem | None:
        if 0 <= index < len(self._items):
            return self._items[index]

        return None

    def takeAt(self, index: int) -> QtWidgets.QLayoutItem | None:
        if 0 <= index < len(self._items):
            return self._items.pop(index)

        return None

    def expandingDirections(self) -> QtCore.Qt.Orientations:
        return QtCore.Qt.Orientations()

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._do_layout(
            QtCore.QRect(0, 0, width, 0),
            test_only=True,
        )

    def setGeometry(self, rect: QtCore.QRect) -> None:
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self) -> QtCore.QSize:
        return self.minimumSize()

    def minimumSize(self) -> QtCore.QSize:
        size = QtCore.QSize()

        for item in self._items:
            size = size.expandedTo(item.minimumSize())

        margins = self.contentsMargins()

        size += QtCore.QSize(
            margins.left() + margins.right(),
            margins.top() + margins.bottom(),
        )

        return size

    def _do_layout(
        self,
        rect: QtCore.QRect,
        test_only: bool,
    ) -> int:
        margins = self.contentsMargins()

        effective_rect = rect.adjusted(
            margins.left(),
            margins.top(),
            -margins.right(),
            -margins.bottom(),
        )

        x = effective_rect.x()
        y = effective_rect.y()
        line_height = 0

        for item in self._items:
            widget = item.widget()

            if widget is not None and widget.isHidden():
                continue

            item_size = item.sizeHint()

            next_x = (
                x
                + item_size.width()
                + self._horizontal_spacing
            )

            if (
                next_x - self._horizontal_spacing
                > effective_rect.right()
                and line_height > 0
            ):
                x = effective_rect.x()
                y += line_height + self._vertical_spacing
                next_x = (
                    x
                    + item_size.width()
                    + self._horizontal_spacing
                )
                line_height = 0

            if not test_only:
                item.setGeometry(
                    QtCore.QRect(
                        QtCore.QPoint(x, y),
                        item_size,
                    )
                )

            x = next_x
            line_height = max(
                line_height,
                item_size.height(),
            )

        return (
            y
            + line_height
            - rect.y()
            + margins.bottom()
        )
    

class ControlShapeTile(QtWidgets.QAbstractButton):
    """Clickable tile representing one control shape."""

    TILE_SIZE = 110
    LABEL_HEIGHT = 24
    BORDER_WIDTH = 2

    def __init__(
        self,
        shape_info: ControlShapeInfo,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.shape_info = shape_info
        self._pixmap = QtGui.QPixmap()

        self.setCheckable(True)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setToolTip(shape_info.name)

        self.setFixedSize(
            self.TILE_SIZE,
            self.TILE_SIZE,
        )

        if shape_info.icon_path is not None:
            self._pixmap = QtGui.QPixmap(
                str(shape_info.icon_path)
            )

    @property
    def shape_name(self) -> str:
        return self.shape_info.name

    def paintEvent(
        self,
        event: QtGui.QPaintEvent,
    ) -> None:
        del event

        painter = QtGui.QPainter(self)
        painter.setRenderHint(
            QtGui.QPainter.Antialiasing,
            True,
        )
        painter.setRenderHint(
            QtGui.QPainter.SmoothPixmapTransform,
            True,
        )

        rect = self.rect()
        image_rect = rect.adjusted(
            self.BORDER_WIDTH,
            self.BORDER_WIDTH,
            -self.BORDER_WIDTH,
            -self.BORDER_WIDTH,
        )

        palette = self.palette()

        background_color = palette.color(
            QtGui.QPalette.Button
        )

        if self.isDown():
            background_color = background_color.darker(115)
        elif self.underMouse():
            background_color = background_color.lighter(110)

        painter.fillRect(
            image_rect,
            background_color,
        )

        self._paint_thumbnail(
            painter=painter,
            rect=image_rect,
        )

        self._paint_name_overlay(
            painter=painter,
            rect=image_rect,
        )

        self._paint_border(
            painter=painter,
            rect=rect,
        )

    def _paint_thumbnail(
        self,
        painter: QtGui.QPainter,
        rect: QtCore.QRect,
    ) -> None:
        if self._pixmap.isNull():
            self._paint_blank_thumbnail(
                painter=painter,
                rect=rect,
            )
            return

        scaled_pixmap = self._pixmap.scaled(
            rect.size(),
            QtCore.Qt.KeepAspectRatio,
            QtCore.Qt.SmoothTransformation,
        )

        pixmap_x = (
            rect.x()
            + (rect.width() - scaled_pixmap.width()) // 2
        )

        pixmap_y = (
            rect.y()
            + (rect.height() - scaled_pixmap.height()) // 2
        )

        painter.drawPixmap(
            pixmap_x,
            pixmap_y,
            scaled_pixmap,
        )

    def _paint_blank_thumbnail(
        self,
        painter: QtGui.QPainter,
        rect: QtCore.QRect,
    ) -> None:
        painter.save()

        text_color = self.palette().color(
            QtGui.QPalette.Disabled,
            QtGui.QPalette.Text,
        )

        painter.setPen(text_color)

        font = painter.font()
        font.setBold(True)
        font.setPointSize(18)
        painter.setFont(font)

        placeholder_rect = rect.adjusted(
            0,
            0,
            0,
            -self.LABEL_HEIGHT,
        )

        painter.drawText(
            placeholder_rect,
            QtCore.Qt.AlignCenter,
            "—",
        )

        painter.restore()

    def _paint_name_overlay(
        self,
        painter: QtGui.QPainter,
        rect: QtCore.QRect,
    ) -> None:
        label_rect = QtCore.QRect(
            rect.x(),
            rect.bottom() - self.LABEL_HEIGHT + 1,
            rect.width(),
            self.LABEL_HEIGHT,
        )

        overlay_color = QtGui.QColor(0, 0, 0, 170)

        painter.fillRect(
            label_rect,
            overlay_color,
        )

        painter.save()

        painter.setPen(
            QtGui.QColor(235, 235, 235)
        )

        font = painter.font()
        font.setPointSize(8)
        painter.setFont(font)

        text = painter.fontMetrics().elidedText(
            self.shape_name,
            QtCore.Qt.ElideRight,
            label_rect.width() - 10,
        )

        painter.drawText(
            label_rect.adjusted(5, 0, -5, 0),
            QtCore.Qt.AlignVCenter
            | QtCore.Qt.AlignLeft,
            text,
        )

        painter.restore()

    def _paint_border(
        self,
        painter: QtGui.QPainter,
        rect: QtCore.QRect,
    ) -> None:
        if self.isChecked():
            border_color = self.palette().color(
                QtGui.QPalette.Highlight
            )
            border_width = self.BORDER_WIDTH
        elif self.underMouse():
            border_color = self.palette().color(
                QtGui.QPalette.Midlight
            )
            border_width = 1
        else:
            border_color = self.palette().color(
                QtGui.QPalette.Mid
            )
            border_width = 1

        painter.setPen(
            QtGui.QPen(
                border_color,
                border_width,
            )
        )

        painter.drawRect(
            rect.adjusted(
                border_width // 2,
                border_width // 2,
                -(border_width // 2) - 1,
                -(border_width // 2) - 1,
            )
        )

class ControlShapeBrowser(QtWidgets.QWidget):
    """Scrollable browser for control shapes."""

    selection_changed = Signal(str)

    def __init__(
        self,
        shape_library: Path = SHAPE_LIBRARY_DIR,
        icon_library: Path = SHAPE_ICON_LIBRARY_DIR,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.shape_library = shape_library
        self.icon_library = icon_library

        self._tiles: list[ControlShapeTile] = []
        self._selected_shape: str | None = None

        self._build_ui()
        self._connect_signals()
        self.refresh()

    @property
    def selected_shape(self) -> str | None:
        """Return the currently selected shape name."""

        return self._selected_shape

    def _build_ui(self) -> None:
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(4)

        self.search_field = QtWidgets.QLineEdit()
        self.search_field.setPlaceholderText(
            "Search control shapes..."
        )
        self.search_field.setClearButtonEnabled(True)

        main_layout.addWidget(self.search_field)

        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(
            QtWidgets.QFrame.NoFrame
        )
        self.scroll_area.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarAlwaysOff
        )

        self.scroll_widget = QtWidgets.QWidget()

        self.flow_layout = FlowLayout(
            parent=self.scroll_widget,
            margin=2,
            horizontal_spacing=4,
            vertical_spacing=4,
        )

        self.scroll_area.setWidget(
            self.scroll_widget
        )

        main_layout.addWidget(
            self.scroll_area,
            stretch=1,
        )

    def _connect_signals(self) -> None:
        self.search_field.textChanged.connect(
            self._filter_tiles
        )

    def refresh(self) -> None:
        """Rebuild the browser from the shape library."""

        previous_selection = self._selected_shape

        self._clear_tiles()

        shape_library = get_control_shape_library(
            shape_library=self.shape_library,
            icon_library=self.icon_library,
        )

        for shape_info in shape_library:
            tile = ControlShapeTile(
                shape_info=shape_info,
            )

            tile.clicked.connect(
                lambda checked=False, current_tile=tile: (
                    self._select_tile(current_tile)
                )
            )

            self.flow_layout.addWidget(tile)
            self._tiles.append(tile)

        if previous_selection is not None:
            self.set_selected_shape(previous_selection)
        elif self._tiles:
            self._select_tile(self._tiles[0])

        self._filter_tiles(
            self.search_field.text()
        )

        self.scroll_widget.updateGeometry()

    def set_selected_shape(
        self,
        shape_name: str,
    ) -> bool:
        """Select a shape by name."""

        for tile in self._tiles:
            if tile.shape_name == shape_name:
                self._select_tile(tile)
                return True

        return False

    def _select_tile(
        self,
        selected_tile: ControlShapeTile,
    ) -> None:
        for tile in self._tiles:
            tile.setChecked(
                tile is selected_tile
            )

        self._selected_shape = (
            selected_tile.shape_name
        )

        self.selection_changed.emit(
            selected_tile.shape_name
        )

    def _filter_tiles(
        self,
        search_text: str,
    ) -> None:
        search_text = search_text.strip().lower()

        for tile in self._tiles:
            is_match = (
                not search_text
                or search_text in tile.shape_name.lower()
            )

            tile.setVisible(is_match)

        self.scroll_widget.updateGeometry()
        self.flow_layout.invalidate()

    def _clear_tiles(self) -> None:
        self._selected_shape = None

        while self.flow_layout.count():
            item = self.flow_layout.takeAt(0)

            if item is None:
                continue

            widget = item.widget()

            if widget is not None:
                widget.deleteLater()

        self._tiles.clear()

    def iter_tiles(
        self,
    ) -> Iterator[ControlShapeTile]:
        yield from self._tiles


