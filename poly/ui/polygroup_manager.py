from __future__ import annotations

import maya.OpenMayaUI as omui

try:
    from PySide6 import QtCore, QtGui, QtWidgets
    from shiboken6 import wrapInstance

    Signal = QtCore.Signal

except ImportError:
    from PySide2 import QtCore, QtGui, QtWidgets
    from shiboken2 import wrapInstance

    Signal = QtCore.Signal







# -------------------------------------------------------------------------
# Workshop
# -------------------------------------------------------------------------

# Update these imports to wherever these currently live in Workshop.
from Workshop.color.palette import PaletteColor
from Workshop.color.palette_picker import PalettePickerPopup

from Workshop.poly.uv_sets import get_uv_sets, set_current_uv_set, set_primary_uv_set

from Workshop.poly.polygroups import (
    PolyGroup,
    PolyGroupLayer,
    create_polygroup_from_selection,
    create_polygroup_layer,
    fix_polygroup_shells,
    generate_polygroups_from_uv_shells,
    get_polygroup_layers_from_scene,
)
from Workshop.poly.meshes import get_selected_mesh

from Workshop.poly.ui.authoring import (
    PolyGroupAuthoringWidget,
)

from Workshop.poly.ui.layer_manager import (
    PolyGroupLayerManager,
)

from Workshop.poly.ui.polygroup_browser import (
    PolyGroupBrowser,
)

from Workshop.poly.selection import (
    select_components,
    add_components_to_selection,
    remove_components_from_selection,
)


# =============================================================================
# Shared Widgets
# =============================================================================


class CollapsibleSection(QtWidgets.QWidget):
    """Simple collapsible UI section."""

    def __init__(
        self,
        title: str = "Section",
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.toggle_button = QtWidgets.QToolButton()
        self.toggle_button.setText(title)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(True)

        self.toggle_button.setToolButtonStyle(
            QtCore.Qt.ToolButtonTextBesideIcon
        )

        self.toggle_button.setArrowType(
            QtCore.Qt.DownArrow
        )

        self.content = QtWidgets.QWidget()

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self.toggle_button)
        layout.addWidget(self.content)

        self.toggle_button.clicked.connect(
            self.toggle
        )

    def toggle(self) -> None:
        """Show or hide the section contents."""

        visible = self.toggle_button.isChecked()

        self.content.setVisible(visible)

        self.toggle_button.setArrowType(
            QtCore.Qt.DownArrow
            if visible
            else QtCore.Qt.RightArrow
        )


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


# =============================================================================
# File IO
# =============================================================================


class PolyGroupIOWidget(
    QtWidgets.QWidget
):
    """Polygroup JSON controls."""

    write_clicked = Signal()
    read_clicked = Signal()

    def __init__(
        self,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:

        super().__init__(parent)

        layout = QtWidgets.QHBoxLayout(
            self
        )

        layout.setContentsMargins(
            6,
            6,
            6,
            6,
        )

        self.write_button = (
            QtWidgets.QPushButton(
                "Write JSON"
            )
        )

        self.read_button = (
            QtWidgets.QPushButton(
                "Read JSON"
            )
        )

        layout.addWidget(
            self.write_button
        )

        layout.addWidget(
            self.read_button
        )

        self.write_button.clicked.connect(
            self.write_clicked.emit
        )

        self.read_button.clicked.connect(
            self.read_clicked.emit
        )


# =============================================================================
# Manager
# =============================================================================


class PolyGroupManagerWindow(
    QtWidgets.QDialog
):

    def __init__(
        self,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:

        if parent is None:
            parent = maya_main_window()

        super().__init__(parent)

        self.setWindowTitle(
            "PolyGroup Manager"
        )

        self.resize(
            450,
            700,
        )

        self.layers: list[
            PolyGroupLayer
        ] = []

        self.mesh: str | None = None

        self._build_ui()
        self._connect_signals()

        self.refresh_from_selection()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:

        main_layout = QtWidgets.QVBoxLayout(
            self
        )

        main_layout.setSpacing(6)

        # --------------------------------------------------------------
        # Authoring
        # --------------------------------------------------------------

        self.authoring = (
            PolyGroupAuthoringWidget()
        )

        self.authoring_section = (
            CollapsibleSection(
                title="PolyGroup Authoring"
            )
        )

        authoring_layout = (
            QtWidgets.QVBoxLayout(
                self.authoring_section.content
            )
        )

        authoring_layout.addWidget(
            self.authoring
        )

        main_layout.addWidget(
            self.authoring_section
        )

        # --------------------------------------------------------------
        # Layers
        # --------------------------------------------------------------

        self.layer_manager = (
            PolyGroupLayerManager()
        )

        self.layer_section = (
            CollapsibleSection(
                title="Layers"
            )
        )

        layer_layout = (
            QtWidgets.QVBoxLayout(
                self.layer_section.content
            )
        )

        layer_layout.addWidget(
            self.layer_manager
        )

        main_layout.addWidget(
            self.layer_section
        )

        # --------------------------------------------------------------
        # Polygroups
        # --------------------------------------------------------------

        self.polygroup_browser = (
            PolyGroupBrowser()
        )

        self.polygroup_section = (
            CollapsibleSection(
                title="Polygroups"
            )
        )

        polygroup_layout = (
            QtWidgets.QVBoxLayout(
                self.polygroup_section.content
            )
        )

        polygroup_layout.addWidget(
            self.polygroup_browser
        )

        main_layout.addWidget(
            self.polygroup_section,
            stretch=1,
        )

        # --------------------------------------------------------------
        # IO
        # --------------------------------------------------------------

        self.io_widget = (
            PolyGroupIOWidget()
        )

        self.io_section = (
            CollapsibleSection(
                title="File"
            )
        )

        io_layout = QtWidgets.QVBoxLayout(
            self.io_section.content
        )

        io_layout.addWidget(
            self.io_widget
        )

        main_layout.addWidget(
            self.io_section
        )

    def _connect_signals(self) -> None:

        self.layer_manager.selection_changed.connect(
            self._layer_changed
        )

        # Rediscover the selected mesh + its layers from Maya.
        self.layer_manager.refresh_button.clicked.connect(
            self.refresh_from_selection
        )

        self.authoring.create_from_uvs_clicked.connect(
            self._create_from_uvs
        )

        self.authoring.create_from_selection_clicked.connect(
            self._create_from_selection
        )

        self.authoring.combine_clicked.connect(
            lambda: self._dummy(
                "Combine polygroups"
            )
        )

        self.authoring.delete_clicked.connect(
            lambda: self._dummy(
                "Delete polygroup"
            )
        )

        self.authoring.display_colors_clicked.connect(
            lambda: self._dummy(
                "Toggle color display"
            )
        )

        self.authoring.refresh_colors_clicked.connect(
            lambda: self._dummy(
                "Refresh polygroup colors"
            )
        )

        self.io_widget.write_clicked.connect(
            lambda: self._dummy(
                "Write JSON"
            )
        )

        self.io_widget.read_clicked.connect(
            lambda: self._dummy(
                "Read JSON"
            )
        )

        self.authoring.fix_shells_clicked.connect(
            self._fix_polygroup_shells
        )

        self.polygroup_browser.select_clicked.connect(
            self._select_polygroup
        )

        self.polygroup_browser.add_clicked.connect(
            self._add_polygroup_to_selection
        )

        self.polygroup_browser.remove_clicked.connect(
            self._remove_polygroup_from_selection
        )

        self.authoring.create_layer_clicked.connect(
            self._create_layer
        )
    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def _create_layer(
        self,
        name: str,
    ) -> None:
        """Create a blank PolyGroup layer."""

        if self.mesh is None:
            print(
                "PolyGroup Manager: "
                "No mesh loaded."
            )
            return

        if not name:
            name = "polygroup_layer"

        layer = create_polygroup_layer(
            mesh=self.mesh,
            name=name,
        )

        self._refresh_active_layer(
            uv_set=layer.uv_set,
        )

    def _select_polygroup(
        self,
        polygroup: PolyGroup,
    ) -> None:
        """Select the faces belonging to a polygroup."""

        faces = polygroup.get_faces()

        select_components(
            components=faces,
        )


    def _add_polygroup_to_selection(
        self,
        polygroup: PolyGroup,
    ) -> None:
        """Add a polygroup's faces to the current selection."""

        faces = polygroup.get_faces()

        add_components_to_selection(
            components=faces,
        )


    def _remove_polygroup_from_selection(
        self,
        polygroup: PolyGroup,
    ) -> None:
        """Remove a polygroup's faces from the current selection."""

        faces = polygroup.get_faces()

        remove_components_from_selection(
            components=faces,
        )

    def _fix_polygroup_shells(
        self,
    ) -> None:
        """Repair UV shells for the active polygroup layer."""

        layer = self.layer_manager.current_layer

        if layer is None:
            print(
                "PolyGroup Manager: "
                "No polygroup layer selected."
            )
            return

        set_current_uv_set(
            mesh=layer.mesh,
            uv_set=layer.uv_set,
        )

        fix_polygroup_shells(
            layer=layer,
        )

        self._refresh_active_layer(
            uv_set=layer.uv_set,
        )

    def _refresh_active_layer(
        self,
        uv_set: str,
    ) -> None:
        """Refresh scene data while preserving the active layer."""

        if self.mesh is None:
            return

        layers = get_polygroup_layers_from_scene(
            mesh=self.mesh,
        )

        self.set_layers(
            layers
        )

        for index, layer in enumerate(layers):

            if layer.uv_set != uv_set:
                continue

            self.layer_manager.layer_list.setCurrentRow(
                index
            )

            set_current_uv_set(
                mesh=self.mesh,
                uv_set=layer.uv_set,
            )

            break

    def refresh_from_selection(self) -> None:
        """Load polygroup data from the selected mesh."""

        mesh = get_selected_mesh()

        if mesh is None:
            print(
                "PolyGroup Manager: "
                "No polygon mesh selected."
            )
            return

        self.mesh = mesh

        # Start from the normal modeling UV set.
        set_primary_uv_set(
            mesh=mesh,
        )

        self.authoring.set_mesh(
            mesh
        )

        layers = get_polygroup_layers_from_scene(
            mesh=mesh,
        )

        self.set_layers(
            layers
        )

    def set_mesh(
        self,
        mesh: str,
    ) -> None:

        self.mesh = mesh

        self.authoring.set_mesh(
            mesh
        )

    def set_layers(
        self,
        layers: list[PolyGroupLayer],
    ) -> None:

        self.layers = layers

        self.layer_manager.set_layers(
            layers
        )

    # ------------------------------------------------------------------
    # Layers
    # ------------------------------------------------------------------

    def _layer_changed(
        self,
        layer: PolyGroupLayer,
    ) -> None:
        """Set the active PolyGroup layer."""

        if self.mesh is None:
            return

        set_current_uv_set(
            mesh=self.mesh,
            uv_set=layer.uv_set,
        )

        self.polygroup_browser.set_layer(
            layer
        )

    # ------------------------------------------------------------------
    # Dummy Actions
    # ------------------------------------------------------------------

    def _create_from_uvs(
        self,
        name: str,
        uv_set: str,
    ) -> None:
        """Create a polygroup layer from an existing UV set."""

        if self.mesh is None:
            print(
                "PolyGroup Manager: "
                "No mesh loaded."
            )
            return

        if not uv_set:
            print(
                "PolyGroup Manager: "
                "No source UV set selected."
            )
            return

        if not name:
            name = "polygroup_layer"

        layer = generate_polygroups_from_uv_shells(
            mesh=self.mesh,
            source_uv_set=uv_set,
            name=name,
        )

        # Rediscover everything from the scene so the
        # manager stays synchronized with Maya.
        self.refresh_from_selection()

    def _create_from_selection(
        self,
        name: str,
    ) -> None:
        """Create a polygroup from the current face selection."""

        layer = self.layer_manager.current_layer

        if layer is None:
            print(
                "PolyGroup Manager: "
                "No polygroup layer selected."
            )
            return

        # IMPORTANT:
        # Explicitly activate the UV set belonging
        # to the layer we're modifying.
        set_current_uv_set(
            mesh=layer.mesh,
            uv_set=layer.uv_set,
        )

        if not name:
            name = None

        create_polygroup_from_selection(
            layer=layer,
            name=name,
        )

        self._refresh_active_layer(
            uv_set=layer.uv_set,
        )
        

    def _dummy(
        self,
        action: str,
    ) -> None:

        print(
            f"TODO: {action}"
        )


# =============================================================================
# Maya
# =============================================================================


def maya_main_window() -> QtWidgets.QWidget:

    pointer = (
        omui.MQtUtil.mainWindow()
    )

    if pointer is None:
        raise RuntimeError(
            "Could not find Maya's main window."
        )

    return wrapInstance(
        int(pointer),
        QtWidgets.QWidget,
    )


_polygroup_manager_window = None


def show_polygroup_manager() -> PolyGroupManagerWindow:
    """Show the PolyGroup Manager."""

    global _polygroup_manager_window

    if _polygroup_manager_window is not None:

        try:
            _polygroup_manager_window.close()
            _polygroup_manager_window.deleteLater()

        except RuntimeError:
            pass

    _polygroup_manager_window = (
        PolyGroupManagerWindow()
    )

    _polygroup_manager_window.show()

    return _polygroup_manager_window