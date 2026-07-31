from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator
import maya.OpenMayaUI as omui
import maya.cmds as cmds

try:
    from PySide6 import QtCore, QtGui, QtWidgets
    from shiboken6 import wrapInstance
    Signal = QtCore.Signal
except ImportError:
    from PySide2 import QtCore, QtGui, QtWidgets
    from shiboken2 import wrapInstance
    Signal = QtCore.Signal

from Workshop.control.serialize import SHAPE_LIBRARY_DIR


WORKSHOP_ROOT = Path(__file__).resolve().parents[1]  # Adjust if needed

SHAPE_ICON_LIBRARY_DIR = WORKSHOP_ROOT / "shape_icons"

SUPPORTED_IMAGE_EXTENSIONS = (
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
)


class CollapsibleSection(QtWidgets.QWidget):
    """Simple collapsible UI section."""

    def __init__(
        self,
        title: str = "Section",
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.toggle_btn = QtWidgets.QToolButton()
        self.toggle_btn.setText(title)
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setChecked(True)

        self.toggle_btn.setToolButtonStyle(
            QtCore.Qt.ToolButtonTextBesideIcon
        )

        self.toggle_btn.setArrowType(
            QtCore.Qt.DownArrow
        )

        self.toggle_btn.clicked.connect(
            self.toggle
        )

        self.content = QtWidgets.QWidget()

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self.toggle_btn)
        layout.addWidget(self.content)

    def toggle(self) -> None:
        """Show or hide the section contents."""

        visible = self.toggle_btn.isChecked()

        self.content.setVisible(visible)

        self.toggle_btn.setArrowType(
            QtCore.Qt.DownArrow
            if visible
            else QtCore.Qt.RightArrow
        )





class ControlShapeBrowserWindow(QtWidgets.QDialog):
    def __init__(
        self,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        if parent is None:
            parent = maya_main_window()

        super().__init__(parent)

        self.setWindowTitle("Control Creator")
        self.resize(500, 600)

        self.setWindowFlags(
            QtCore.Qt.Window
            | QtCore.Qt.WindowTitleHint
            | QtCore.Qt.WindowCloseButtonHint
        )

        main_layout = QtWidgets.QVBoxLayout(self)

        self.shape_browser = ControlShapeBrowser()
        main_layout.addWidget(
            self.shape_browser,
            stretch=1,
        )

        self.control_creator = ControlCreatorWidget(
            shape_browser=self.shape_browser,
        )

        self.control_creator_section = CollapsibleSection(
            title="Control Creator",
        )

        control_creator_layout = QtWidgets.QVBoxLayout(
            self.control_creator_section.content
        )

        control_creator_layout.addWidget(
            self.control_creator
        )

        main_layout.addWidget(
            self.control_creator_section
        )




def maya_main_window() -> QtWidgets.QWidget:
    """Return Maya's main application window."""

    main_window_pointer = omui.MQtUtil.mainWindow()

    if main_window_pointer is None:
        raise RuntimeError("Could not find Maya's main window.")

    return wrapInstance(
        int(main_window_pointer),
        QtWidgets.QWidget,
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
        possible_paths = (
            icon_library / f"{shape_name}{extension}",
            icon_library / f"{shape_name}.0{extension}",
        )

        for icon_path in possible_paths:
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

    MIN_TILE_SIZE = 100
    MAX_TILE_SIZE = 140
    LABEL_HEIGHT = 18
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

        self.set_tile_size(self.MIN_TILE_SIZE)

        if shape_info.icon_path is not None:
            self._pixmap = QtGui.QPixmap(
                str(shape_info.icon_path)
            )

    @property
    def shape_name(self) -> str:
        return self.shape_info.name
    
    def set_tile_size(self, size: int) -> None:
        """Resize the tile while keeping it square."""

        size = max(
            self.MIN_TILE_SIZE,
            min(size, self.MAX_TILE_SIZE),
        )

        self.setFixedSize(size, size)

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

        self.grid_layout = QtWidgets.QGridLayout(
            self.scroll_widget
        )

        self.grid_layout.setContentsMargins(2, 2, 2, 2)
        self.grid_layout.setHorizontalSpacing(4)
        self.grid_layout.setVerticalSpacing(4)
        self.grid_layout.setAlignment(
            QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft
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

    def resizeEvent(
        self,
        event: QtGui.QResizeEvent,
    ) -> None:
        """Reorganize the tiles when the browser changes size."""

        super().resizeEvent(event)

        QtCore.QTimer.singleShot(
            0,
            self._rebuild_grid,
        )


    def _rebuild_grid(self) -> None:
        """Arrange visible tiles and softly resize them to fill the row."""

        visible_tiles = [
            tile
            for tile in self._tiles
            if tile.isVisible()
        ]

        self._clear_grid_layout()

        if not visible_tiles:
            return

        margins = self.grid_layout.contentsMargins()
        spacing = self.grid_layout.horizontalSpacing()

        available_width = (
            self.scroll_area.viewport().width()
            - margins.left()
            - margins.right()
        )

        min_size = ControlShapeTile.MIN_TILE_SIZE
        max_size = ControlShapeTile.MAX_TILE_SIZE

        # Start with the number of columns that fit at minimum tile size.
        column_count = max(
            1,
            (available_width + spacing)
            // (min_size + spacing),
        )

        # Calculate the size needed to fully occupy the available width.
        tile_size = (
            available_width
            - spacing * (column_count - 1)
        ) // column_count

        # If the tiles would become too large, add another column.
        while tile_size > max_size:
            column_count += 1

            tile_size = (
                available_width
                - spacing * (column_count - 1)
            ) // column_count

        tile_size = max(
            min_size,
            min(tile_size, max_size),
        )

        for index, tile in enumerate(visible_tiles):
            row = index // column_count
            column = index % column_count

            tile.set_tile_size(tile_size)

            self.grid_layout.addWidget(
                tile,
                row,
                column,
            )

        # Keeps incomplete final rows aligned to the left.
        self.grid_layout.setColumnStretch(
            column_count,
            1,
        )

        self.scroll_widget.updateGeometry()


    def _clear_grid_layout(self) -> None:
        """Remove widgets from the grid without deleting them."""

        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)

            if item is None:
                continue

            widget = item.widget()

            if widget is not None:
                widget.setParent(self.scroll_widget)

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

            self._tiles.append(tile)

        if previous_selection is not None:
            self.set_selected_shape(previous_selection)
        elif self._tiles:
            self._select_tile(self._tiles[0])

        self._filter_tiles(
            self.search_field.text()
        )

        self._rebuild_grid()

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

        self._rebuild_grid()

    def _clear_tiles(self) -> None:
        self._selected_shape = None

        self._clear_grid_layout()

        for tile in self._tiles:
            tile.deleteLater()

        self._tiles.clear()

    def iter_tiles(
        self,
    ) -> Iterator[ControlShapeTile]:
        yield from self._tiles

class ColorButton(QtWidgets.QPushButton):
    """Button that displays and edits a color."""

    color_changed = Signal(QtGui.QColor)

    def __init__(
        self,
        color: QtGui.QColor | None = None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._color = color or QtGui.QColor(255, 255, 0)

        self.setFixedSize(50, 30)
        self.setToolTip("Choose control color")

        self.clicked.connect(self._choose_color)

        self._update_style()

    @property
    def color(self) -> QtGui.QColor:
        """Return a copy of the currently selected color."""

        return QtGui.QColor(self._color)

    @color.setter
    def color(self, color: QtGui.QColor) -> None:
        if not color.isValid():
            return

        self._color = QtGui.QColor(color)
        self._update_style()
        self.color_changed.emit(self.color)

    def _choose_color(self) -> None:
        """Open Maya's native color editor."""

        current_color = (
            self._color.redF(),
            self._color.greenF(),
            self._color.blueF(),
        )

        result = cmds.colorEditor(
            rgbValue=current_color,
        )

        if not result:
            return

        if not cmds.colorEditor(query=True, result=True):
            return

        red, green, blue = cmds.colorEditor(
            query=True,
            rgbValue=True,
        )

        self.color = QtGui.QColor.fromRgbF(
            red,
            green,
            blue,
        )

    def _update_style(self) -> None:
        """Update the button background to display the color."""

        red = self._color.red()
        green = self._color.green()
        blue = self._color.blue()

        # Choose readable border/text based on brightness.
        brightness = (
            red * 0.299
            + green * 0.587
            + blue * 0.114
        )

        border_color = (
            "rgb(30, 30, 30)"
            if brightness > 128
            else "rgb(220, 220, 220)"
        )

        self.setStyleSheet(
            f"""
            QPushButton {{
                background-color: rgb({red}, {green}, {blue});
                border: 1px solid {border_color};
                border-radius: 3px;
            }}

            QPushButton:hover {{
                border: 2px solid rgb(90, 160, 220);
            }}
            """
        )

class ControlCreatorWidget(QtWidgets.QWidget):
    """Controls used to create a control from the selected browser shape."""

    def __init__(
        self,
        shape_browser: ControlShapeBrowser,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.shape_browser = shape_browser

        self._build_ui()
        self._connect_signals()

    @property
    def control_color(self) -> QtGui.QColor:
        """Return the currently selected control color."""

        return self.color_button.color

    @property
    def control_color_rgb(self) -> tuple[float, float, float]:
        """Return the color as normalized Maya-style RGB values."""

        color = self.control_color

        return (
            color.redF(),
            color.greenF(),
            color.blueF(),
        )

    @property
    def control_color_rgb_255(self) -> tuple[int, int, int]:
        """Return the color as RGB values from 0 to 255."""

        color = self.control_color

        return (
            color.red(),
            color.green(),
            color.blue(),
        )

    @property
    def control_color_hex(self) -> str:
        """Return the color as a hexadecimal string."""

        return self.control_color.name()

    def _build_ui(self) -> None:
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(6)

        color_layout = QtWidgets.QHBoxLayout()
        color_layout.setContentsMargins(0, 0, 0, 0)

        color_label = QtWidgets.QLabel("Color")

        self.color_button = ColorButton(
            color=QtGui.QColor(255, 255, 0),
        )

        color_layout.addWidget(color_label)
        color_layout.addStretch()
        color_layout.addWidget(self.color_button)

        main_layout.addLayout(color_layout)

        self.build_button = QtWidgets.QPushButton(
            "Build Control"
        )

        main_layout.addWidget(self.build_button)

    def _connect_signals(self) -> None:
        self.build_button.clicked.connect(
            self.build_control
        )

    def build_control(self) -> None:
        """Temporary control-building function."""

        selected_shape = self.shape_browser.selected_shape

        if selected_shape is None:
            cmds.warning("No control shape is selected.")
            return

        print("=" * 50)
        print("Building control")
        print(f"Shape: {selected_shape}")
        print(f"Color hex: {self.control_color_hex}")
        print(f"Color RGB 255: {self.control_color_rgb_255}")
        print(f"Color RGB normalized: {self.control_color_rgb}")
        print("=" * 50)
