from __future__ import annotations

try:
    from PySide6 import QtCore, QtGui, QtWidgets
except ImportError:
    from PySide2 import QtCore, QtGui, QtWidgets


from Workshop.color.palette import (
    PALETTE_FOLDER,
    Palette,
    PaletteColor,
    load_palette,
)

from Workshop.color.palette_manager import show_palette_manager


Signal = QtCore.Signal


# ----------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------

MAKE_NEW_PALETTE = "(Make New Palette)"

LAST_PALETTE: str | None = None

SWATCH_SIZE = 34
SWATCH_SPACING = 4
SWATCH_COLUMNS = 8


# ----------------------------------------------------------------------
# Color Swatch
# ----------------------------------------------------------------------

class PaletteSwatch(QtWidgets.QPushButton):
    """Small clickable color swatch."""

    color_selected = Signal(object)

    def __init__(
        self,
        color: PaletteColor,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.palette_color = color

        self.setFixedSize(
            SWATCH_SIZE,
            SWATCH_SIZE,
        )

        self.setCursor(
            QtCore.Qt.PointingHandCursor
        )

        self.setToolTip(
            self._build_tooltip()
        )

        self.clicked.connect(
            self._emit_color
        )

        self._update_style()

    def _build_tooltip(self) -> str:
        """Build the swatch tooltip."""

        name = (
            self.palette_color.name
            or "Unnamed Color"
        )

        r, g, b = self.palette_color.rgb

        return (
            f"{name}\n"
            f"RGB: "
            f"{r:.3f}, "
            f"{g:.3f}, "
            f"{b:.3f}"
        )

    def _emit_color(self) -> None:
        """Emit this swatch's PaletteColor."""

        self.color_selected.emit(
            self.palette_color
        )

    def _update_style(self) -> None:
        """Display the palette color."""

        r, g, b = self.palette_color.rgb

        red = round(r * 255)
        green = round(g * 255)
        blue = round(b * 255)

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
                background-color: rgb(
                    {red},
                    {green},
                    {blue}
                );
                border: 1px solid {border_color};
                border-radius: 3px;
            }}

            QPushButton:hover {{
                border: 2px solid rgb(90, 160, 220);
            }}
            """
        )


# ----------------------------------------------------------------------
# Palette Picker
# ----------------------------------------------------------------------

class PalettePickerPopup(QtWidgets.QDialog):
    """Reusable popup for selecting a color from a Workshop palette."""

    color_selected = Signal(object)

    def __init__(
        self,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.current_palette: Palette | None = None

        self._swatches: list[PaletteSwatch] = []

        self.setWindowTitle(
            "Choose Color"
        )

        self.setWindowFlags(
            QtCore.Qt.Popup
        )

        self.setMinimumWidth(330)

        self._build_ui()
        self._connect_signals()

        self.refresh_palettes()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        main_layout = QtWidgets.QVBoxLayout(
            self
        )

        main_layout.setContentsMargins(
            8,
            8,
            8,
            8,
        )

        main_layout.setSpacing(6)

        # --------------------------------------------------------------
        # Palette selector
        # --------------------------------------------------------------

        self.palette_combo = QtWidgets.QComboBox()

        main_layout.addWidget(
            self.palette_combo
        )

        # --------------------------------------------------------------
        # Swatches
        # --------------------------------------------------------------

        self.scroll_area = QtWidgets.QScrollArea()

        self.scroll_area.setWidgetResizable(
            True
        )

        self.scroll_area.setFrameShape(
            QtWidgets.QFrame.NoFrame
        )

        self.scroll_area.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarAlwaysOff
        )

        self.scroll_widget = QtWidgets.QWidget()

        self.swatch_layout = QtWidgets.QGridLayout(
            self.scroll_widget
        )

        self.swatch_layout.setContentsMargins(
            2,
            2,
            2,
            2,
        )

        self.swatch_layout.setHorizontalSpacing(
            SWATCH_SPACING
        )

        self.swatch_layout.setVerticalSpacing(
            SWATCH_SPACING
        )

        self.swatch_layout.setAlignment(
            QtCore.Qt.AlignTop
            | QtCore.Qt.AlignLeft
        )

        self.scroll_area.setWidget(
            self.scroll_widget
        )

        self.scroll_area.setMinimumHeight(
            100
        )

        self.scroll_area.setMaximumHeight(
            220
        )

        main_layout.addWidget(
            self.scroll_area
        )

        # --------------------------------------------------------------
        # Status
        # --------------------------------------------------------------

        self.status_label = QtWidgets.QLabel()

        self.status_label.setAlignment(
            QtCore.Qt.AlignCenter
        )

        main_layout.addWidget(
            self.status_label
        )

    # ------------------------------------------------------------------
    # Signals
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        self.palette_combo.currentTextChanged.connect(
            self._palette_changed
        )

    # ------------------------------------------------------------------
    # Palette Library
    # ------------------------------------------------------------------

    def get_palette_names(self) -> list[str]:
        """Return all available normal palettes."""

        PALETTE_FOLDER.mkdir(
            parents=True,
            exist_ok=True,
        )

        return sorted(
            (
                path.stem
                for path in PALETTE_FOLDER.glob(
                    "*.json"
                )
            ),
            key=str.lower,
        )

    def refresh_palettes(self) -> None:
        """Refresh the palette dropdown."""

        global LAST_PALETTE

        palette_names = self.get_palette_names()

        self.palette_combo.blockSignals(
            True
        )

        self.palette_combo.clear()

        self.palette_combo.addItems(
            palette_names
        )

        self.palette_combo.addItem(
            MAKE_NEW_PALETTE
        )

        # --------------------------------------------------------------
        # Restore last-used palette
        # --------------------------------------------------------------

        if (
            LAST_PALETTE
            and LAST_PALETTE in palette_names
        ):
            index = self.palette_combo.findText(
                LAST_PALETTE
            )

            self.palette_combo.setCurrentIndex(
                index
            )

        elif palette_names:
            # Default to the first palette for a new Maya session.
            self.palette_combo.setCurrentIndex(
                0
            )

        self.palette_combo.blockSignals(
            False
        )

        self._palette_changed(
            self.palette_combo.currentText()
        )
    # ------------------------------------------------------------------
    # Palette Selection
    # ------------------------------------------------------------------

    def _palette_changed(
        self,
        palette_name: str,
    ) -> None:
        global LAST_PALETTE

        if not palette_name:
            self.current_palette = None
            self._clear_swatches()

            self.status_label.setText(
                "No palettes available."
            )
            return

        if palette_name == MAKE_NEW_PALETTE:
            self._open_palette_manager()
            return

        try:
            self.current_palette = load_palette(
                palette_name,
                rig_palette=False,
            )

        except (
            FileNotFoundError,
            ValueError,
            KeyError,
        ) as error:
            self.current_palette = None
            self._clear_swatches()

            self.status_label.setText(
                f"Could not load palette: {error}"
            )
            return

        # Remember this palette for the current Maya session.
        LAST_PALETTE = palette_name

        self._rebuild_swatches()

    # ------------------------------------------------------------------
    # Swatches
    # ------------------------------------------------------------------

    def _rebuild_swatches(self) -> None:
        """Rebuild the swatches for the current palette."""

        self._clear_swatches()

        if self.current_palette is None:
            return

        if not self.current_palette.colors:
            self.status_label.setText(
                "This palette has no colors."
            )

            return

        self.status_label.setText(
            f"{self.current_palette.color_count} colors"
        )

        for index, color in enumerate(
            self.current_palette.colors
        ):
            swatch = PaletteSwatch(
                color=color,
                parent=self.scroll_widget,
            )

            swatch.color_selected.connect(
                self._color_selected
            )

            row = (
                index
                // SWATCH_COLUMNS
            )

            column = (
                index
                % SWATCH_COLUMNS
            )

            self.swatch_layout.addWidget(
                swatch,
                row,
                column,
            )

            self._swatches.append(
                swatch
            )

    def _clear_swatches(self) -> None:
        """Delete all existing swatches."""

        while self.swatch_layout.count():
            item = self.swatch_layout.takeAt(
                0
            )

            widget = item.widget()

            if widget is not None:
                widget.deleteLater()

        self._swatches.clear()

    # ------------------------------------------------------------------
    # Color Selection
    # ------------------------------------------------------------------

    def _color_selected(
        self,
        color: PaletteColor,
    ) -> None:
        """Return the selected color to the caller."""

        self.color_selected.emit(
            color
        )

        self.accept()

    # ------------------------------------------------------------------
    # Palette Manager
    # ------------------------------------------------------------------

    def _open_palette_manager(self) -> None:
        """Open the normal palette manager."""

        manager = show_palette_manager()

        # Refresh our list when the manager is destroyed.
        manager.destroyed.connect(
            self.refresh_palettes
        )

        # A Popup closes itself when another window receives focus.
        # Opening the manager therefore finishes this picker.
        self.close()