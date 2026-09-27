from __future__ import annotations

try:
    from PySide6 import QtCore, QtWidgets
except ImportError:
    from PySide2 import QtCore, QtWidgets

from Workshop.poly.uv_sets import get_uv_sets


Signal = QtCore.Signal


class PolyGroupAuthoringWidget(
    QtWidgets.QWidget
):
    """Polygroup creation and editing tools."""

    create_from_uvs_clicked = Signal(
        str,
        str,
    )

    create_from_selection_clicked = Signal(
        str
    )

    delete_clicked = Signal()
    combine_clicked = Signal()

    display_colors_clicked = Signal()
    refresh_colors_clicked = Signal()

    fix_shells_clicked = Signal()

    create_layer_clicked = Signal(str)

    def __init__(
        self,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:

        super().__init__(parent)

        self.mesh: str | None = None

        self._build_ui()
        self._connect_signals()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:

        main_layout = QtWidgets.QVBoxLayout(
            self
        )

        main_layout.setContentsMargins(
            6,
            6,
            6,
            6,
        )

        main_layout.setSpacing(6)

        # --------------------------------------------------------------
        # Layer Creation
        # --------------------------------------------------------------

        layer_name_layout = (
            QtWidgets.QHBoxLayout()
        )

        layer_name_layout.addWidget(
            QtWidgets.QLabel(
                "Layer Name"
            )
        )

        self.layer_name_field = (
            QtWidgets.QLineEdit()
        )

        self.create_layer_button = QtWidgets.QPushButton(
            "Create Blank Layer"
        )

        self.create_layer_button.setToolTip(
            "Create a new PolyGroup layer "
            "with the entire mesh in the default polygroup."
        )

        self.layer_name_field.setPlaceholderText(
            "polygroup_layer"
        )

        layer_name_layout.addWidget(
            self.layer_name_field,
            stretch=1,
        )

        main_layout.addLayout(
            layer_name_layout
        )

        main_layout.addWidget(
            self.create_layer_button
        )

        # --------------------------------------------------------------
        # Source UV Set
        # --------------------------------------------------------------

        uv_layout = QtWidgets.QHBoxLayout()

        uv_layout.addWidget(
            QtWidgets.QLabel(
                "Source UV"
            )
        )

        self.uv_combo = (
            QtWidgets.QComboBox()
        )

        uv_layout.addWidget(
            self.uv_combo,
            stretch=1,
        )

        self.refresh_uv_button = (
            QtWidgets.QPushButton(
                "Refresh"
            )
        )

        uv_layout.addWidget(
            self.refresh_uv_button
        )

        main_layout.addLayout(
            uv_layout
        )

        # --------------------------------------------------------------
        # Create Layer From UVs
        # --------------------------------------------------------------

        self.create_uv_button = (
            QtWidgets.QPushButton(
                "Create From UVs"
            )
        )

        main_layout.addWidget(
            self.create_uv_button
        )

        # --------------------------------------------------------------
        # PolyGroup Creation
        # --------------------------------------------------------------

        polygroup_name_layout = (
            QtWidgets.QHBoxLayout()
        )

        polygroup_name_layout.addWidget(
            QtWidgets.QLabel(
                "PolyGroup Name"
            )
        )

        self.polygroup_name_field = (
            QtWidgets.QLineEdit()
        )

        self.polygroup_name_field.setPlaceholderText(
            "Optional"
        )

        polygroup_name_layout.addWidget(
            self.polygroup_name_field,
            stretch=1,
        )

        main_layout.addLayout(
            polygroup_name_layout
        )

        self.create_selection_button = (
            QtWidgets.QPushButton(
                "Create From Selection"
            )
        )

        main_layout.addWidget(
            self.create_selection_button
        )

        # --------------------------------------------------------------
        # Management
        # --------------------------------------------------------------

        manage_layout = (
            QtWidgets.QHBoxLayout()
        )

        self.combine_button = (
            QtWidgets.QPushButton(
                "Combine"
            )
        )

        self.delete_button = (
            QtWidgets.QPushButton(
                "Delete"
            )
        )

        manage_layout.addWidget(
            self.combine_button
        )

        manage_layout.addWidget(
            self.delete_button
        )

        main_layout.addLayout(
            manage_layout
        )

        # --------------------------------------------------------------
        # Color Display
        # --------------------------------------------------------------

        color_layout = (
            QtWidgets.QHBoxLayout()
        )

        self.display_button = (
            QtWidgets.QPushButton(
                "Toggle Colors"
            )
        )

        self.refresh_color_button = (
            QtWidgets.QPushButton(
                "Refresh Colors"
            )
        )

        color_layout.addWidget(
            self.display_button
        )

        color_layout.addWidget(
            self.refresh_color_button
        )

        main_layout.addLayout(
            color_layout
        )


        self.fix_shells_button = (
            QtWidgets.QPushButton(
                "Fix PolyGroup Shells"
            )
        )

        self.fix_shells_button.setToolTip(
            "Rebuild and refit all polygroups "
            "into their assigned UDIM tiles."
        )

        main_layout.addWidget(
            self.fix_shells_button
        )

    # ------------------------------------------------------------------
    # Signals
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:

        self.refresh_uv_button.clicked.connect(
            self.refresh_uv_sets
        )

        self.create_uv_button.clicked.connect(
            self._create_from_uvs
        )

        self.create_selection_button.clicked.connect(
            self._create_from_selection
        )

        self.combine_button.clicked.connect(
            self.combine_clicked.emit
        )

        self.delete_button.clicked.connect(
            self.delete_clicked.emit
        )

        self.display_button.clicked.connect(
            self.display_colors_clicked.emit
        )

        self.refresh_color_button.clicked.connect(
            self.refresh_colors_clicked.emit
        )

        self.fix_shells_button.clicked.connect(
            self.fix_shells_clicked.emit
        )

        self.create_layer_button.clicked.connect(
            self._create_layer
        )

    # ------------------------------------------------------------------
    # Mesh
    # ------------------------------------------------------------------

    def _create_layer(self) -> None:
        """Request creation of a blank PolyGroup layer."""

        name = self.layer_name_field.text().strip()

        self.create_layer_clicked.emit(
            name
    )

    def set_mesh(
        self,
        mesh: str | None,
    ) -> None:
        """Set the mesh used by the authoring widget."""

        self.mesh = mesh

        self.refresh_uv_sets()

    def refresh_uv_sets(self) -> None:
        """Refresh the source UV-set dropdown."""

        current_uv_set = (
            self.uv_combo.currentText()
        )

        self.uv_combo.clear()

        if self.mesh is None:
            return

        uv_sets = get_uv_sets(
            mesh=self.mesh
        )

        for uv_set in uv_sets:
            self.uv_combo.addItem(
                uv_set
            )

        # Try to preserve the previous selection.
        if current_uv_set in uv_sets:

            index = self.uv_combo.findText(
                current_uv_set
            )

            if index >= 0:
                self.uv_combo.setCurrentIndex(
                    index
                )

    # ------------------------------------------------------------------
    # Creation
    # ------------------------------------------------------------------

    def _create_from_uvs(self) -> None:
        """Emit a request to create a layer from a UV set."""

        layer_name = (
            self.layer_name_field
            .text()
            .strip()
        )

        source_uv_set = (
            self.uv_combo.currentText()
        )

        self.create_from_uvs_clicked.emit(
            layer_name,
            source_uv_set,
        )

    def _create_from_selection(
        self,
    ) -> None:
        """Emit a request to create a polygroup from selected faces."""

        polygroup_name = (
            self.polygroup_name_field
            .text()
            .strip()
        )

        self.create_from_selection_clicked.emit(
            polygroup_name
        )