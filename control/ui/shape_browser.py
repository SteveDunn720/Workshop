from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from turtle import shape
from typing import Iterator
import maya.OpenMayaUI as omui
import maya.cmds as cmds

from Workshop.transform.constraint import constraint
from Workshop.transform.utils import create_transform

from Workshop.snapshots.image_planes import create_control_helper_plane
from Workshop.control.core import _create_control_curve
from Workshop.control.serialize import write_curve_to_library
from Workshop.snapshots.camera_core import (
    delete_snapshot_camera,
    place_snapshot_camera,
    take_snapshot,
)
from Workshop.control.serialize import SHAPE_LIBRARY_DIR
from Workshop.control.core import create_control
from Workshop.color.palette import PaletteColor
from Workshop.color.palette_picker import PalettePickerPopup


WORKSHOP_ROOT = Path(__file__).resolve().parents[1]  # Adjust if needed
IMAGE_PATH = WORKSHOP_ROOT / "AA_control_sizer.png"
ICON_PATH = WORKSHOP_ROOT / "shape_icons"


try:
    from PySide6 import QtCore, QtGui, QtWidgets
    from shiboken6 import wrapInstance

    Signal = QtCore.Signal
except ImportError:
    from PySide2 import QtCore, QtGui, QtWidgets
    from shiboken2 import wrapInstance

    Signal = QtCore.Signal


WORKSHOP_ROOT = Path(__file__).resolve().parents[1]  # Adjust if needed

SHAPE_ICON_LIBRARY_DIR = WORKSHOP_ROOT / "shape_icons"

SUPPORTED_IMAGE_EXTENSIONS = (
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
)


@dataclass
class ShapeDisplayAttribute:
    value: float | bool
    connection: str | None = None


@dataclass
class ShapeDisplaySettings:
    line_width: ShapeDisplayAttribute
    draw_on_top: ShapeDisplayAttribute


class ControlAuthoringWidget(QtWidgets.QWidget):
    """Tools for creating and saving control shapes."""

    def __init__(
        self,
        shape_browser: ControlShapeBrowser,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._build_ui()
        self._connect_signals()
        self.shape_browser = shape_browser

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def control_name(self) -> str:
        """Return the control shape name."""

        return self.name_field.text().strip()

    @property
    def use_selected(self) -> bool:
        """Return whether the selected Maya object should be used."""

        return self.use_selected_checkbox.isChecked()

    # -------------------------------------------------------------------------
    # UI
    # -------------------------------------------------------------------------

    def _build_ui(self) -> None:
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(6)

        # ---------------------------------------------------------------------
        # Name
        # ---------------------------------------------------------------------

        name_layout = QtWidgets.QHBoxLayout()
        name_layout.setContentsMargins(0, 0, 0, 0)

        name_label = QtWidgets.QLabel("Name")

        self.name_field = QtWidgets.QLineEdit()
        self.name_field.setPlaceholderText("Control Shape Name")

        name_layout.addWidget(name_label)
        name_layout.addWidget(
            self.name_field,
            stretch=1,
        )

        main_layout.addLayout(name_layout)

        # ---------------------------------------------------------------------
        # Scene Setup
        # ---------------------------------------------------------------------

        scene_layout = QtWidgets.QHBoxLayout()
        scene_layout.setContentsMargins(0, 0, 0, 0)

        self.setup_button = QtWidgets.QPushButton("Setup Scene")

        self.clean_button = QtWidgets.QPushButton("Clean Scene")

        scene_layout.addWidget(self.setup_button)
        scene_layout.addWidget(self.clean_button)

        main_layout.addLayout(scene_layout)

        # ---------------------------------------------------------------------
        # Use Selected
        # ---------------------------------------------------------------------

        self.use_selected_checkbox = QtWidgets.QCheckBox("Use Selected")

        main_layout.addWidget(self.use_selected_checkbox)

        # ---------------------------------------------------------------------
        # Save / Load
        # ---------------------------------------------------------------------

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)

        self.save_button = QtWidgets.QPushButton("Save Shape")

        self.load_button = QtWidgets.QPushButton("Load Shape")

        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.load_button)

        main_layout.addLayout(button_layout)

    def _connect_signals(self) -> None:
        self.setup_button.clicked.connect(self.setup_scene)

        self.clean_button.clicked.connect(self.clean_scene)

        self.save_button.clicked.connect(self.save_control)

        self.load_button.clicked.connect(self.load_shape)

    # -------------------------------------------------------------------------
    # Functions
    # -------------------------------------------------------------------------

    def clean_scene(self) -> None:
        """Remove the control-authoring helper scene."""

        helper_group = "control_creater_helper_grp"

        if cmds.objExists(helper_group):
            cmds.delete(helper_group)

    def setup_scene(self) -> None:
        """Create the helper scene used for drawing controls."""

        helper_group = "control_creater_helper_grp"

        if cmds.objExists(helper_group):
            cmds.delete(helper_group)

        parent_transform = create_transform(name=helper_group)

        transform, shape = create_control_helper_plane(
            image_path=str(IMAGE_PATH),
            name="reference_image",
        )

        cmds.parent(
            transform,
            parent_transform,
        )

        cmds.setAttr(
            f"{shape}.alphaGain",
            0.5,
        )

    def save_control(self) -> None:
        """Save the current curve to the control library."""

        control_name = self.control_name

        if not control_name:
            QtWidgets.QMessageBox.warning(
                self,
                "Missing Control Name",
                "Enter a control name before saving.",
            )
            return

        if self.use_selected:
            selected = (
                cmds.ls(
                    selection=True,
                    type="transform",
                )
                or []
            )

            if not selected:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Nothing Selected",
                    "Select a control curve before saving.",
                )
                return

            control = selected[0]

        else:
            control = control_name

        if not cmds.objExists(control):
            QtWidgets.QMessageBox.warning(
                self,
                "Control Not Found",
                f"Could not find '{control}'.",
            )
            return

        write_curve_to_library(
            curve=control,
            name=control_name,
            force=True,
        )

        helper_group = "control_creater_helper_grp"

        if cmds.objExists(helper_group):
            cmds.setAttr(
                f"{helper_group}.visibility",
                False,
            )

        camera = place_snapshot_camera(
            obj=control,
            swivel=45.0,
            tilt=45.0,
            orthographic=True,
        )

        take_snapshot(
            camera=camera,
            path=ICON_PATH,
            name=control_name,
        )

        delete_snapshot_camera()
        self.shape_browser.refresh()

    def load_shape(self) -> None:
        """Create a curve from the specified library shape."""

        control_name = self.control_name

        if not control_name:
            QtWidgets.QMessageBox.warning(
                self,
                "Missing Control Name",
                "Enter a control name before loading.",
            )
            return

        _create_control_curve(
            name=control_name,
            control_shape=control_name,
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

        self.toggle_btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)

        self.toggle_btn.setArrowType(QtCore.Qt.DownArrow)

        self.toggle_btn.clicked.connect(self.toggle)

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
            QtCore.Qt.DownArrow if visible else QtCore.Qt.RightArrow
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

        control_creator_layout.addWidget(self.control_creator)

        main_layout.addWidget(self.control_creator_section)

        self.control_authoring = ControlAuthoringWidget(
            shape_browser=self.shape_browser,
        )

        self.control_authoring_section = CollapsibleSection(
            title="Shape Authoring",
        )

        control_authoring_layout = QtWidgets.QVBoxLayout(
            self.control_authoring_section.content
        )

        control_authoring_layout.addWidget(self.control_authoring)

        main_layout.addWidget(self.control_authoring_section)


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

            next_x = x + item_size.width() + self._horizontal_spacing

            if (
                next_x - self._horizontal_spacing > effective_rect.right()
                and line_height > 0
            ):
                x = effective_rect.x()
                y += line_height + self._vertical_spacing
                next_x = x + item_size.width() + self._horizontal_spacing
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

        return y + line_height - rect.y() + margins.bottom()


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
            self._pixmap = QtGui.QPixmap(str(shape_info.icon_path))

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

        background_color = palette.color(QtGui.QPalette.Button)

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

        pixmap_x = rect.x() + (rect.width() - scaled_pixmap.width()) // 2

        pixmap_y = rect.y() + (rect.height() - scaled_pixmap.height()) // 2

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

        painter.setPen(QtGui.QColor(235, 235, 235))

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
            QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft,
            text,
        )

        painter.restore()

    def _paint_border(
        self,
        painter: QtGui.QPainter,
        rect: QtCore.QRect,
    ) -> None:
        if self.isChecked():
            border_color = self.palette().color(QtGui.QPalette.Highlight)
            border_width = self.BORDER_WIDTH
        elif self.underMouse():
            border_color = self.palette().color(QtGui.QPalette.Midlight)
            border_width = 1
        else:
            border_color = self.palette().color(QtGui.QPalette.Mid)
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

        search_layout = QtWidgets.QHBoxLayout()
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(4)

        self.search_field = QtWidgets.QLineEdit()
        self.search_field.setPlaceholderText("Search control shapes...")
        self.search_field.setClearButtonEnabled(True)

        self.refresh_button = QtWidgets.QPushButton("Refresh")
        self.refresh_button.setFixedWidth(70)
        self.refresh_button.setToolTip("Refresh the control shape library")

        search_layout.addWidget(
            self.search_field,
            stretch=1,
        )

        search_layout.addWidget(
            self.refresh_button,
        )

        main_layout.addLayout(search_layout)

        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self.scroll_widget = QtWidgets.QWidget()

        self.grid_layout = QtWidgets.QGridLayout(self.scroll_widget)

        self.grid_layout.setContentsMargins(2, 2, 2, 2)
        self.grid_layout.setHorizontalSpacing(4)
        self.grid_layout.setVerticalSpacing(4)
        self.grid_layout.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)

        self.scroll_area.setWidget(self.scroll_widget)

        main_layout.addWidget(
            self.scroll_area,
            stretch=1,
        )

    def _connect_signals(self) -> None:
        self.search_field.textChanged.connect(self._filter_tiles)

        self.refresh_button.clicked.connect(self.refresh)

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

        visible_tiles = [tile for tile in self._tiles if tile.isVisible()]

        self._clear_grid_layout()

        if not visible_tiles:
            return

        margins = self.grid_layout.contentsMargins()
        spacing = self.grid_layout.horizontalSpacing()

        available_width = (
            self.scroll_area.viewport().width() - margins.left() - margins.right()
        )

        min_size = ControlShapeTile.MIN_TILE_SIZE
        max_size = ControlShapeTile.MAX_TILE_SIZE

        # Start with the number of columns that fit at minimum tile size.
        column_count = max(
            1,
            (available_width + spacing) // (min_size + spacing),
        )

        # Calculate the size needed to fully occupy the available width.
        tile_size = (available_width - spacing * (column_count - 1)) // column_count

        # If the tiles would become too large, add another column.
        while tile_size > max_size:
            column_count += 1

            tile_size = (available_width - spacing * (column_count - 1)) // column_count

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

            tile.show()
        # Keeps incomplete final rows aligned to the left.
        self.grid_layout.setColumnStretch(
            column_count,
            1,
        )

        self.scroll_widget.updateGeometry()

    def _clear_grid_layout(self) -> None:
        """Remove widgets from the grid without deleting them."""

        while self.grid_layout.count():
            self.grid_layout.takeAt(0)

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
                lambda checked=False, current_tile=tile: self._select_tile(current_tile)
            )

            self._tiles.append(tile)

        if previous_selection is not None:
            self.set_selected_shape(previous_selection)
        elif self._tiles:
            self._select_tile(self._tiles[0])

        self._filter_tiles(self.search_field.text())

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
            tile.setChecked(tile is selected_tile)

        self._selected_shape = selected_tile.shape_name

        self.selection_changed.emit(selected_tile.shape_name)

    def _filter_tiles(
        self,
        search_text: str,
    ) -> None:
        search_text = search_text.strip().lower()

        for tile in self._tiles:
            is_match = not search_text or search_text in tile.shape_name.lower()

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
        """Open the Workshop palette picker."""

        picker = PalettePickerPopup(
            parent=self,
        )

        picker.color_selected.connect(self._palette_color_selected)

        # Position the popup underneath the color button.
        popup_position = self.mapToGlobal(
            QtCore.QPoint(
                0,
                self.height(),
            )
        )

        picker.move(popup_position)

        picker.exec()

    def _palette_color_selected(
        self,
        palette_color: PaletteColor,
    ) -> None:
        """Set the button color from a palette color."""

        red, green, blue = palette_color.rgb

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
        brightness = red * 0.299 + green * 0.587 + blue * 0.114

        border_color = "rgb(30, 30, 30)" if brightness > 128 else "rgb(220, 220, 220)"

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

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

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

    @property
    def placement_mode(self) -> str:
        """Return the selected control placement mode."""

        return self.placement_combo.currentText()

    @property
    def primary_axis(self) -> str:
        """Return the selected primary axis."""

        return self.primary_axis_combo.currentText()

    @property
    def control_size(self) -> float:
        """Return the selected control size."""

        return self.size_spinbox.value()

    @property
    def use_sdk(self) -> bool:
        """Return whether an SDK offset should be created."""

        return self.sdk_checkbox.isChecked()

    @property
    def control_name(self) -> str:
        """Return the requested control name."""

        return self.name_field.text().strip()

    @property
    def position_offset(self) -> tuple[float, float, float]:
        """Return the control position offset."""

        return (
            self.position_x.value(),
            self.position_y.value(),
            self.position_z.value(),
        )

    @property
    def rotation_offset(self) -> tuple[float, float, float]:
        """Return the control rotation offset."""

        return (
            self.rotation_x.value(),
            self.rotation_y.value(),
            self.rotation_z.value(),
        )

    # -------------------------------------------------------------------------
    # UI
    # -------------------------------------------------------------------------

    def _build_ui(self) -> None:
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(6)

        # ---------------------------------------------------------------------
        # Placement
        # ---------------------------------------------------------------------

        placement_layout = QtWidgets.QHBoxLayout()
        placement_layout.setContentsMargins(0, 0, 0, 0)

        placement_label = QtWidgets.QLabel("Placement")

        self.placement_combo = QtWidgets.QComboBox()
        self.placement_combo.addItems(
            ["At_Origin", "Match_Pose", "Parent", "Parent_and_Scale"]
        )

        placement_layout.addWidget(placement_label)
        placement_layout.addStretch()
        placement_layout.addWidget(self.placement_combo)

        main_layout.addLayout(placement_layout)

        name_layout = QtWidgets.QHBoxLayout()
        name_layout.setContentsMargins(0, 0, 0, 0)

        name_label = QtWidgets.QLabel("Name")

        self.name_field = QtWidgets.QLineEdit()
        self.name_field.setPlaceholderText("control_name")

        name_layout.addWidget(name_label)
        name_layout.addStretch()
        name_layout.addWidget(self.name_field)

        main_layout.addLayout(name_layout)

        # ---------------------------------------------------------------------
        # Position Offset
        # ---------------------------------------------------------------------

        position_layout = QtWidgets.QHBoxLayout()
        position_layout.setContentsMargins(0, 0, 0, 0)

        position_label = QtWidgets.QLabel("Position Offset")

        self.position_x = QtWidgets.QDoubleSpinBox()
        self.position_y = QtWidgets.QDoubleSpinBox()
        self.position_z = QtWidgets.QDoubleSpinBox()

        for spinbox in (
            self.position_x,
            self.position_y,
            self.position_z,
        ):
            spinbox.setRange(-10000.0, 10000.0)
            spinbox.setDecimals(3)
            spinbox.setSingleStep(0.1)
            spinbox.setValue(0.0)

        position_layout.addWidget(position_label)
        position_layout.addStretch()

        position_layout.addWidget(QtWidgets.QLabel("X"))
        position_layout.addWidget(self.position_x)

        position_layout.addWidget(QtWidgets.QLabel("Y"))
        position_layout.addWidget(self.position_y)

        position_layout.addWidget(QtWidgets.QLabel("Z"))
        position_layout.addWidget(self.position_z)

        main_layout.addLayout(position_layout)

        # ---------------------------------------------------------------------
        # Rotation Offset
        # ---------------------------------------------------------------------

        rotation_layout = QtWidgets.QHBoxLayout()
        rotation_layout.setContentsMargins(0, 0, 0, 0)

        rotation_label = QtWidgets.QLabel("Rotation Offset")

        self.rotation_x = QtWidgets.QDoubleSpinBox()
        self.rotation_y = QtWidgets.QDoubleSpinBox()
        self.rotation_z = QtWidgets.QDoubleSpinBox()

        for spinbox in (
            self.rotation_x,
            self.rotation_y,
            self.rotation_z,
        ):
            spinbox.setRange(-360.0, 360.0)
            spinbox.setDecimals(3)
            spinbox.setSingleStep(1.0)
            spinbox.setValue(0.0)

        rotation_layout.addWidget(rotation_label)
        rotation_layout.addStretch()

        rotation_layout.addWidget(QtWidgets.QLabel("X"))
        rotation_layout.addWidget(self.rotation_x)

        rotation_layout.addWidget(QtWidgets.QLabel("Y"))
        rotation_layout.addWidget(self.rotation_y)

        rotation_layout.addWidget(QtWidgets.QLabel("Z"))
        rotation_layout.addWidget(self.rotation_z)

        main_layout.addLayout(rotation_layout)

        # ---------------------------------------------------------------------
        # Primary Axis
        # ---------------------------------------------------------------------

        axis_layout = QtWidgets.QHBoxLayout()
        axis_layout.setContentsMargins(0, 0, 0, 0)

        axis_label = QtWidgets.QLabel("Primary Axis")

        self.primary_axis_combo = QtWidgets.QComboBox()
        self.primary_axis_combo.addItems(
            [
                "x",
                "y",
                "z",
                "-x",
                "-y",
                "-z",
            ]
        )

        axis_layout.addWidget(axis_label)
        axis_layout.addStretch()
        axis_layout.addWidget(self.primary_axis_combo)

        main_layout.addLayout(axis_layout)

        # ---------------------------------------------------------------------
        # Size
        # ---------------------------------------------------------------------

        size_layout = QtWidgets.QHBoxLayout()
        size_layout.setContentsMargins(0, 0, 0, 0)

        size_label = QtWidgets.QLabel("Size")

        self.size_spinbox = QtWidgets.QDoubleSpinBox()
        self.size_spinbox.setRange(0.1, 1000.0)
        self.size_spinbox.setValue(1.0)
        self.size_spinbox.setSingleStep(0.1)
        self.size_spinbox.setDecimals(2)

        size_layout.addWidget(size_label)
        size_layout.addStretch()
        size_layout.addWidget(self.size_spinbox)

        main_layout.addLayout(size_layout)

        # ---------------------------------------------------------------------
        # SDK
        # ---------------------------------------------------------------------

        sdk_layout = QtWidgets.QHBoxLayout()
        sdk_layout.setContentsMargins(0, 0, 0, 0)

        sdk_label = QtWidgets.QLabel("SDK")

        self.sdk_checkbox = QtWidgets.QCheckBox()
        self.sdk_checkbox.setChecked(False)

        sdk_layout.addWidget(sdk_label)
        sdk_layout.addStretch()
        sdk_layout.addWidget(self.sdk_checkbox)

        main_layout.addLayout(sdk_layout)

        # ---------------------------------------------------------------------
        # Color
        # ---------------------------------------------------------------------

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

        # ---------------------------------------------------------------------
        # Build
        # ---------------------------------------------------------------------

        self.build_button = QtWidgets.QPushButton("Build Control")

        self.swap_shape_button = QtWidgets.QPushButton("Swap Shape")

        self.swap_color_checkbox = QtWidgets.QCheckBox("Swap Color")

        swap_shape_layout = QtWidgets.QHBoxLayout()
        swap_shape_layout.setContentsMargins(0, 0, 0, 0)

        swap_shape_layout.addWidget(
            self.swap_shape_button,
            stretch=1,
        )

        swap_shape_layout.addWidget(
            self.swap_color_checkbox,
        )

        self.swap_color_button = QtWidgets.QPushButton("Swap Color")

        main_layout.addWidget(self.build_button)

        main_layout.addLayout(swap_shape_layout)

        main_layout.addWidget(self.swap_color_button)

    def _connect_signals(self) -> None:
        self.build_button.clicked.connect(self.build_control)
        self.swap_color_button.clicked.connect(self.swap_color)
        self.swap_shape_button.clicked.connect(self.swap_shape)

    # -------------------------------------------------------------------------
    # Build
    # -------------------------------------------------------------------------

    def swap_shape(self) -> None:
        color_on_shapes = True
        """Replace the NURBS curve shapes of selected controls."""

        selected_shape = self.shape_browser.selected_shape
        primary_axis = self.primary_axis
        size = self.control_size

        position_offset = self.position_offset
        rotation_offset = self.rotation_offset

        selected = (
            cmds.ls(
                selection=True,
                type="transform",
            )
            or []
        )

        if not selected:
            cmds.warning("No controls selected.")
            return

        for control in selected:
            old_shapes = (
                cmds.listRelatives(
                    control,
                    shapes=True,
                    fullPath=True,
                    type="nurbsCurve",
                )
                or []
            )

            if not old_shapes:
                cmds.warning(f"{control} has no NURBS curve shapes. Skipping.")
                continue

            # --------------------------------------------------------------
            # Store existing shape display settings
            # --------------------------------------------------------------

            display_settings = self._get_shape_display_settings(old_shapes[0])

            if color_on_shapes:
                color = cmds.getAttr(f"{old_shapes[0]}.overrideColorRGB")
            else:
                color = None

            # --------------------------------------------------------------
            # Create replacement shape
            # --------------------------------------------------------------

            temp_ctrl = create_control(
                transform=None,
                name="TEMP_shape_swap",
                parent=None,
                sdk_offset=False,
                control_shape=selected_shape,
                direction=primary_axis,
                size=size,
                shape_position_offset=position_offset,
                shape_rotation_offset=rotation_offset,
            )

            new_shapes = (
                cmds.listRelatives(
                    temp_ctrl.ctrl,
                    shapes=True,
                    fullPath=True,
                    type="nurbsCurve",
                )
                or []
            )

            if not new_shapes:
                cmds.warning(f"Could not create replacement shape for {control}.")

                if cmds.objExists(temp_ctrl.top):
                    cmds.delete(temp_ctrl.top)

                continue

            # --------------------------------------------------------------
            # Remove old shapes
            # --------------------------------------------------------------

            cmds.delete(old_shapes)

            # --------------------------------------------------------------
            # Parent new shapes under existing control
            # --------------------------------------------------------------

            for new_shape in new_shapes:
                parented_shape = cmds.parent(
                    new_shape,
                    control,
                    shape=True,
                    relative=True,
                )

                if color_on_shapes:
                    cmds.setAttr(f"{parented_shape[0]}.overrideEnabled", 1)
                    cmds.setAttr(f"{parented_shape[0]}.overrideRGBColors", 1)
                    cmds.setAttr(
                        f"{parented_shape[0]}.overrideColorRGB",
                        *color[0],
                        type="double3",
                    )

            # --------------------------------------------------------------
            # Get newly parented shapes
            # --------------------------------------------------------------

            new_shapes = (
                cmds.listRelatives(
                    control,
                    shapes=True,
                    fullPath=False,
                    type="nurbsCurve",
                )
                or []
            )

            # --------------------------------------------------------------
            # Restore old line width / draw-on-top setup
            # --------------------------------------------------------------

            for new_shape in new_shapes:
                self._apply_shape_display_settings(
                    shape=new_shape,
                    settings=display_settings,
                )

            # --------------------------------------------------------------
            # Rename shapes
            # --------------------------------------------------------------

            renamed_shapes: list[str] = []

            for index, shape in enumerate(new_shapes):
                if index == 0:
                    new_name = f"{control}Shape"
                else:
                    new_name = f"{control}Shape{index + 1}"

                renamed_shape = cmds.rename(
                    shape,
                    new_name,
                )

                renamed_shapes.append(renamed_shape)

            # --------------------------------------------------------------
            # Optionally replace color
            # --------------------------------------------------------------

            if self.swap_color_checkbox.isChecked():
                self._apply_control_color(control)

            # --------------------------------------------------------------
            # Remove leftover temporary hierarchy
            # --------------------------------------------------------------

            if cmds.objExists(temp_ctrl.top):
                cmds.delete(temp_ctrl.top)

        # --------------------------------------------------------------
        # Restore original selection
        # --------------------------------------------------------------

        cmds.select(
            selected,
            replace=True,
        )

    def swap_color(self) -> None:
        """Apply the selected palette color to selected controls."""

        selected = (
            cmds.ls(
                selection=True,
                type="transform",
            )
            or []
        )

        if not selected:
            cmds.warning("No controls selected.")
            return

        for control in selected:
            self._apply_control_color(control)

    def _apply_control_color(
        self,
        control: str,
    ) -> None:
        """
        Apply the currently selected color to a control's shapes.

        Shapes with an incoming color connection are left alone.
        """

        shapes = (
            cmds.listRelatives(
                control,
                shapes=True,
                fullPath=True,
                type="nurbsCurve",
            )
            or []
        )

        for shape in shapes:
            if self._has_color_connection(shape):
                continue

            cmds.setAttr(
                f"{shape}.overrideEnabled",
                1,
            )

            cmds.setAttr(
                f"{shape}.overrideRGBColors",
                1,
            )

            cmds.setAttr(  # type:ignore
                f"{shape}.overrideColorRGB",
                *self.control_color_rgb,
            )

    def _has_color_connection(
        self,
        shape: str,
    ) -> bool:
        """Return whether the shape's override color is driven."""

        color_attributes = (
            "overrideColorRGB",
            "overrideColorR",
            "overrideColorG",
            "overrideColorB",
        )

        for attribute in color_attributes:
            plug = f"{shape}.{attribute}"

            if not cmds.objExists(plug):
                continue

            connections = (
                cmds.listConnections(
                    plug,
                    source=True,
                    destination=False,
                    plugs=True,
                )
                or []
            )

            if connections:
                return True

        return False

    def _get_display_attribute(
        self,
        plug: str,
    ) -> ShapeDisplayAttribute:
        """Capture either the incoming connection or current value."""

        connections = (
            cmds.listConnections(
                plug,
                source=True,
                destination=False,
                plugs=True,
            )
            or []
        )

        connection = connections[0] if connections else None

        value = cmds.getAttr(plug)

        return ShapeDisplayAttribute(
            value=value,
            connection=connection,
        )

    def _get_shape_display_settings(
        self,
        shape: str,
    ) -> ShapeDisplaySettings:
        """Store display settings from an existing control shape."""

        return ShapeDisplaySettings(
            line_width=self._get_display_attribute(f"{shape}.lineWidth"),
            draw_on_top=self._get_display_attribute(f"{shape}.alwaysDrawOnTop"),
        )

    def _apply_shape_display_settings(
        self,
        shape: str,
        settings: ShapeDisplaySettings,
    ) -> None:
        """Apply stored display settings to a new curve shape."""

        self._apply_display_attribute(
            target=f"{shape}.lineWidth",
            settings=settings.line_width,
        )

        self._apply_display_attribute(
            target=f"{shape}.alwaysDrawOnTop",
            settings=settings.draw_on_top,
        )

    def _apply_display_attribute(
        self,
        target: str,
        settings: ShapeDisplayAttribute,
    ) -> None:
        """Restore a connection if one existed, otherwise restore the value."""

        if settings.connection:
            cmds.connectAttr(
                settings.connection,
                target,
                force=True,
            )

            return

        cmds.setAttr(
            target,
            settings.value,
        )

    def build_control(self) -> None:
        selected_shape = self.shape_browser.selected_shape
        name = self.control_name
        placement_mode = self.placement_mode
        primary_axis = self.primary_axis
        size = self.control_size
        sdk = self.use_sdk

        position_offset = self.position_offset
        rotation_offset = self.rotation_offset

        def get_available_name(base_name: str) -> str:
            """Return an available control base name."""

            if not cmds.objExists(f"{base_name}_ctrl"):
                return base_name

            index = 1

            while cmds.objExists(f"{base_name}{index}_ctrl"):
                index += 1

            return f"{base_name}{index}"

        if placement_mode == "At_Origin":
            if name == "":
                name = "new_control"

            name = get_available_name(name)

            transform = None

            ctrl = create_control(
                transform=transform,
                name=name,
                parent=None,
                sdk_offset=sdk,
                control_shape=selected_shape,
                direction=primary_axis,
                size=size,
                shape_position_offset=position_offset,
                shape_rotation_offset=rotation_offset,
            )

            cmds.setAttr(
                ctrl.ctrl + ".overrideEnabled",
                1,
            )
            cmds.setAttr(
                ctrl.ctrl + ".overrideRGBColors",
                1,
            )
            cmds.setAttr(
                ctrl.ctrl + ".overrideColorRGB",
                *self.control_color_rgb,
            )

        else:
            selected = cmds.ls(selection=True) or []

            for transform in selected:
                if name == "":
                    ctrl_name = transform

                    suffixes = (
                        "_jnt",
                        "_guide",
                        "_ctrl",
                        "_grp",
                    )

                    for suffix in suffixes:
                        if ctrl_name.endswith(suffix):
                            ctrl_name = ctrl_name.removesuffix(suffix)
                            break

                else:
                    ctrl_name = name

                ctrl_name = get_available_name(ctrl_name)

                ctrl = create_control(
                    transform=transform,
                    name=ctrl_name,
                    parent=None,
                    sdk_offset=sdk,
                    control_shape=selected_shape,
                    direction=primary_axis,
                    size=size,
                    shape_position_offset=position_offset,
                    shape_rotation_offset=rotation_offset,
                )

                cmds.setAttr(
                    ctrl.ctrl + ".overrideEnabled",
                    1,
                )
                cmds.setAttr(
                    ctrl.ctrl + ".overrideRGBColors",
                    1,
                )
                cmds.setAttr(
                    ctrl.ctrl + ".overrideColorRGB",
                    *self.control_color_rgb,
                )

                if placement_mode == "Parent":
                    constraint(
                        drivers=[ctrl.ctrl],
                        driven=transform,
                        parent=None,
                        constraint_type="parent",
                    )
