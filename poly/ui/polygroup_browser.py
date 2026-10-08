from __future__ import annotations

from Workshop.poly.polygroup_metadata import set_polygroup_data

try:
    from PySide6 import QtCore, QtGui, QtWidgets
except ImportError:
    from PySide2 import QtCore, QtGui, QtWidgets

from Workshop.color.palette import PaletteColor
from Workshop.color.palette_picker import PalettePickerPopup

from Workshop.poly.polygroups import (
    PolyGroup,
    PolyGroupLayer,
)


Signal = QtCore.Signal


class ColorButton(QtWidgets.QPushButton):
    """Button that displays and edits a color."""

    color_changed = Signal(QtGui.QColor)

    def __init__(
        self,
        color: QtGui.QColor | None = None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._color = (
            color
            or QtGui.QColor(255, 255, 0)
        )

        self.setFixedSize(50, 30)
        self.setToolTip("Choose polygroup color")

        self.clicked.connect(
            self._choose_color
        )

        self._update_style()

    @property
    def color(self) -> QtGui.QColor:
        return QtGui.QColor(self._color)

    @color.setter
    def color(
        self,
        color: QtGui.QColor,
    ) -> None:

        if not color.isValid():
            return

        self._color = QtGui.QColor(color)

        self._update_style()

        self.color_changed.emit(
            self.color
        )

    def _choose_color(self) -> None:
        """Open the Workshop palette picker."""

        picker = PalettePickerPopup(
            parent=self,
        )

        picker.color_selected.connect(
            self._palette_color_selected
        )

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

        red, green, blue = palette_color.rgb

        self.color = QtGui.QColor.fromRgbF(
            red,
            green,
            blue,
        )

    def _update_style(self) -> None:

        red = self._color.red()
        green = self._color.green()
        blue = self._color.blue()

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


class PolyGroupBrick(QtWidgets.QFrame):
    """UI item representing one polygroup."""

    clicked = Signal(object)
    name_changed = Signal(object, str)
    color_changed = Signal(object, object)

    select_clicked = Signal(object)
    add_clicked = Signal(object)
    remove_clicked = Signal(object)
    hide_clicked = Signal(object)

    def __init__(
        self,
        polygroup: PolyGroup,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.polygroup = polygroup
        self._selected = False

        self.setFrameShape(
            QtWidgets.QFrame.StyledPanel
        )

        self._build_ui()
        self._connect_signals()

        self.refresh()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:

        main_layout = QtWidgets.QHBoxLayout(self)

        main_layout.setContentsMargins(
            5,
            5,
            5,
            5,
        )

        main_layout.setSpacing(6)

        # --------------------------------------------------------------
        # Color
        # --------------------------------------------------------------

        self.color_button = ColorButton()
        self.color_button.setFixedSize(45, 45)

        main_layout.addWidget(
            self.color_button
        )

        # --------------------------------------------------------------
        # Center
        # --------------------------------------------------------------

        center_layout = QtWidgets.QVBoxLayout()

        center_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        center_layout.setSpacing(4)

        self.name_field = QtWidgets.QLineEdit()

        center_layout.addWidget(
            self.name_field
        )

        # --------------------------------------------------------------
        # Selection buttons
        # --------------------------------------------------------------

        button_layout = QtWidgets.QHBoxLayout()

        button_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        button_layout.setSpacing(3)

        self.select_button = QtWidgets.QPushButton(
            "Select"
        )

        self.add_button = QtWidgets.QPushButton(
            "+"
        )

        self.remove_button = QtWidgets.QPushButton(
            "-"
        )

        self.hide_button = QtWidgets.QPushButton(
            "Hide"
        )

        self.add_button.setToolTip(
            "Add polygroup to selection"
        )

        self.remove_button.setToolTip(
            "Remove polygroup from selection"
        )

        for button in (
            self.add_button,
            self.remove_button,
        ):
            button.setFixedWidth(30)

        button_layout.addWidget(
            self.select_button,
            stretch=1,
        )

        button_layout.addWidget(
            self.add_button
        )

        button_layout.addWidget(
            self.remove_button
        )

        button_layout.addWidget(
            self.hide_button
        )

        center_layout.addLayout(
            button_layout
        )

        main_layout.addLayout(
            center_layout,
            stretch=1,
        )

    def _connect_signals(self) -> None:

        self.name_field.editingFinished.connect(
            self._name_edited
        )

        self.color_button.color_changed.connect(
            self._color_edited
        )

        self.select_button.clicked.connect(
            lambda: self.select_clicked.emit(
                self.polygroup
            )
        )

        self.add_button.clicked.connect(
            lambda: self.add_clicked.emit(
                self.polygroup
            )
        )

        self.remove_button.clicked.connect(
            lambda: self.remove_clicked.emit(
                self.polygroup
            )
        )

        self.hide_button.clicked.connect(
            lambda: self.hide_clicked.emit(
                self.polygroup
            )
        )


    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        """Refresh the brick from its polygroup."""

        self.name_field.setText(
            self.polygroup.name
        )

        red, green, blue = (
            self.polygroup.color
        )

        self.color_button._color = (
            QtGui.QColor.fromRgbF(
                red,
                green,
                blue,
            )
        )

        self.color_button._update_style()

    def set_selected(
        self,
        selected: bool,
    ) -> None:

        self._selected = selected

        if selected:
            self.setStyleSheet(
                """
                PolyGroupBrick {
                    border: 2px solid palette(highlight);
                    border-radius: 3px;
                }
                """
            )

        else:
            self.setStyleSheet("")

    # ------------------------------------------------------------------
    # Editing
    # ------------------------------------------------------------------

    def _name_edited(self) -> None:

        name = self.name_field.text().strip()

        if not name:
            self.name_field.setText(
                self.polygroup.name
            )
            return

        self.name_changed.emit(
            self.polygroup,
            name,
        )

    def _color_edited(
        self,
        color: QtGui.QColor,
    ) -> None:

        self.color_changed.emit(
            self.polygroup,
            color,
        )

    def mousePressEvent(
        self,
        event: QtGui.QMouseEvent,
    ) -> None:

        super().mousePressEvent(event)

        self.clicked.emit(
            self.polygroup
        )


# =============================================================================
# PolyGroup Browser
# =============================================================================


class PolyGroupBrowser(QtWidgets.QWidget):
    """Scrollable browser displaying the polygroups in a layer."""

    select_clicked = Signal(object)
    add_clicked = Signal(object)
    remove_clicked = Signal(object)
    hide_clicked = Signal(object)

    selection_changed = Signal(object)

    def __init__(
        self,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.layer: PolyGroupLayer | None = None

        self._bricks: list[
            PolyGroupBrick
        ] = []

        self._selected_polygroup: (
            PolyGroup | None
        ) = None

        self._build_ui()

    @property
    def selected_polygroup(
        self,
    ) -> PolyGroup | None:

        return self._selected_polygroup

    def _build_ui(self) -> None:

        main_layout = QtWidgets.QVBoxLayout(
            self
        )

        main_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        main_layout.setSpacing(4)

        # --------------------------------------------------------------
        # Header
        # --------------------------------------------------------------

        header_layout = QtWidgets.QHBoxLayout()

        self.group_count_label = QtWidgets.QLabel(
            "No Layer"
        )

        self.refresh_button = (
            QtWidgets.QPushButton(
                "Refresh"
            )
        )

        self.refresh_button.setFixedWidth(
            70
        )

        header_layout.addWidget(
            self.group_count_label
        )

        header_layout.addStretch()

        header_layout.addWidget(
            self.refresh_button
        )

        main_layout.addLayout(
            header_layout
        )

        # --------------------------------------------------------------
        # Scroll
        # --------------------------------------------------------------

        self.scroll_area = (
            QtWidgets.QScrollArea()
        )

        self.scroll_area.setWidgetResizable(
            True
        )

        self.scroll_area.setFrameShape(
            QtWidgets.QFrame.NoFrame
        )

        self.scroll_widget = (
            QtWidgets.QWidget()
        )

        self.brick_layout = (
            QtWidgets.QVBoxLayout(
                self.scroll_widget
            )
        )

        self.brick_layout.setContentsMargins(
            2,
            2,
            2,
            2,
        )

        self.brick_layout.setSpacing(4)

        self.brick_layout.setAlignment(
            QtCore.Qt.AlignTop
        )

        self.scroll_area.setWidget(
            self.scroll_widget
        )

        main_layout.addWidget(
            self.scroll_area,
            stretch=1,
        )
    # ------------------------------------------------------------------
    # Layer
    # ------------------------------------------------------------------

    def set_layer(
        self,
        layer: PolyGroupLayer | None,
    ) -> None:

        self.layer = layer
        self._selected_polygroup = None

        self.refresh()

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def refresh(self) -> None:

        self._clear_bricks()

        if self.layer is None:
            self.group_count_label.setText(
                "No Layer"
            )
            return

        self.group_count_label.setText(
            f"{self.layer.name} "
            f"({len(self.layer.polygroups)})"
        )

        for polygroup in (
            self.layer.polygroups
        ):

            brick = PolyGroupBrick(
                polygroup=polygroup
            )

            brick.select_clicked.connect(
                self.select_clicked.emit
            )

            brick.add_clicked.connect(
                self.add_clicked.emit
            )

            brick.remove_clicked.connect(
                self.remove_clicked.emit
            )

            brick.hide_clicked.connect(
                self.hide_clicked.emit
            )

            brick.clicked.connect(
                self._select_polygroup
            )

            brick.name_changed.connect(
                self._rename_polygroup
            )

            brick.color_changed.connect(
                self._change_color
            )

            brick.select_clicked.connect(
                self._dummy_select
            )

            brick.add_clicked.connect(
                self._dummy_add
            )

            brick.remove_clicked.connect(
                self._dummy_remove
            )

            brick.hide_clicked.connect(
                self._dummy_hide
            )

            self._bricks.append(
                brick
            )

            self.brick_layout.addWidget(
                brick
            )

    def _clear_bricks(self) -> None:

        for brick in self._bricks:
            brick.deleteLater()

        self._bricks.clear()

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    def _select_polygroup(
        self,
        polygroup: PolyGroup,
    ) -> None:

        self._selected_polygroup = (
            polygroup
        )

        for brick in self._bricks:
            brick.set_selected(
                brick.polygroup
                is polygroup
            )

        self.selection_changed.emit(
            polygroup
        )

    # ------------------------------------------------------------------
    # Editing
    # ------------------------------------------------------------------

    def _rename_polygroup(
        self,
        polygroup: PolyGroup,
        name: str,
    ) -> None:
        """Rename a PolyGroup."""

        polygroup.name = name

        set_polygroup_data(
            mesh=polygroup.mesh,
            uv_set=polygroup.uv_set,
            index=polygroup.index,
            name=polygroup.name,
            color=polygroup.color,
        )


    def _change_color(
        self,
        polygroup: PolyGroup,
        color: QtGui.QColor,
    ) -> None:
        """Change a PolyGroup's color."""

        polygroup.color = (
            color.redF(),
            color.greenF(),
            color.blueF(),
        )

        set_polygroup_data(
            mesh=polygroup.mesh,
            uv_set=polygroup.uv_set,
            index=polygroup.index,
            name=polygroup.name,
            color=polygroup.color,
        )

        polygroup.apply_color()
    # ------------------------------------------------------------------
    # Dummy Functions
    # ------------------------------------------------------------------

    def _dummy_select(
        self,
        polygroup: PolyGroup,
    ) -> None:

        print(
            f"TODO: Select "
            f"'{polygroup.name}'"
        )

    def _dummy_add(
        self,
        polygroup: PolyGroup,
    ) -> None:

        print(
            f"TODO: Add "
            f"'{polygroup.name}' "
            f"to selection"
        )

    def _dummy_remove(
        self,
        polygroup: PolyGroup,
    ) -> None:

        print(
            f"TODO: Remove "
            f"'{polygroup.name}' "
            f"from selection"
        )

    def _dummy_hide(
        self,
        polygroup: PolyGroup,
    ) -> None:

        print(
            f"TODO: Hide "
            f"'{polygroup.name}'"
        )
