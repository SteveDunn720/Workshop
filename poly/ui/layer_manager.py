from __future__ import annotations

try:
    from PySide6 import QtCore, QtWidgets
except ImportError:
    from PySide2 import QtCore, QtWidgets

from Workshop.poly.polygroups import PolyGroupLayer


Signal = QtCore.Signal


class PolyGroupLayerManager(
    QtWidgets.QWidget
):
    """Display available polygroup layers."""

    selection_changed = Signal(object)

    def __init__(
        self,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:

        super().__init__(parent)

        self.layers: list[
            PolyGroupLayer
        ] = []

        self._build_ui()

    def _build_ui(self) -> None:

        layout = QtWidgets.QVBoxLayout(
            self
        )

        layout.setContentsMargins(
            6,
            6,
            6,
            6,
        )

        layout.setSpacing(4)

        self.layer_list = (
            QtWidgets.QListWidget()
        )

        self.layer_list.setMaximumHeight(
            120
        )

        self.refresh_button = (
            QtWidgets.QPushButton(
                "Refresh Layers"
            )
        )

        layout.addWidget(
            self.layer_list
        )

        layout.addWidget(
            self.refresh_button
        )

        self.layer_list.currentRowChanged.connect(
            self._selection_changed
        )


    def set_layers(
        self,
        layers: list[PolyGroupLayer],
    ) -> None:

        self.layers = layers
        self.refresh()

    def refresh(self) -> None:

        current_layer = self.current_layer

        self.layer_list.clear()

        for layer in self.layers:
            self.layer_list.addItem(
                layer.name
            )

        if current_layer in self.layers:

            self.layer_list.setCurrentRow(
                self.layers.index(
                    current_layer
                )
            )

        elif self.layers:

            self.layer_list.setCurrentRow(
                0
            )

    @property
    def current_layer(
        self,
    ) -> PolyGroupLayer | None:

        row = (
            self.layer_list.currentRow()
        )

        if (
            row < 0
            or row >= len(self.layers)
        ):
            return None

        return self.layers[row]

    def _selection_changed(
        self,
        row: int,
    ) -> None:

        if (
            row < 0
            or row >= len(self.layers)
        ):
            return

        self.selection_changed.emit(
            self.layers[row]
        )
