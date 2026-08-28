from __future__ import annotations

from functools import partial

try:
    from PySide6 import QtCore, QtGui, QtWidgets
except ImportError:
    from PySide2 import QtCore, QtGui, QtWidgets

from .palette import (
    PALETTE_FOLDER,
    Palette,
    PaletteColor,
    load_palette,
    save_palette,
)


# ----------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------

WINDOW_OBJECT_NAME = "workshop_palette_manager"
WINDOW_TITLE = "Workshop Palette Manager"

SWATCH_SIZE = 64
SWATCH_COLUMNS = 6


# ----------------------------------------------------------------------
# Palette Color Button
# ----------------------------------------------------------------------

class PaletteColorButton(QtWidgets.QPushButton):
    """Clickable color swatch used by the palette browser."""

    def __init__(
        self,
        color: PaletteColor,
        index: int,
        parent: QtWidgets.QWidget | None = None,
    ):
        super().__init__(parent)

        self.color = color
        self.index = index
        self.selected = False

        self.setFixedSize(
            SWATCH_SIZE,
            SWATCH_SIZE,
        )

        self.setToolTip(
            color.name or f"Color {index + 1}"
        )

        self.update_style()

    def update_style(self) -> None:
        """Update the button appearance from the stored color."""

        r = round(self.color.rgb[0] * 255)
        g = round(self.color.rgb[1] * 255)
        b = round(self.color.rgb[2] * 255)

        border_width = 4 if self.selected else 1
        border_color = "white" if self.selected else "#555555"

        self.setStyleSheet(
            f"""
            QPushButton {{
                background-color: rgb({r}, {g}, {b});
                border: {border_width}px solid {border_color};
                border-radius: 4px;
            }}

            QPushButton:hover {{
                border: 3px solid #CCCCCC;
            }}
            """
        )

    def set_selected(
        self,
        selected: bool,
    ) -> None:
        self.selected = selected
        self.update_style()


# ----------------------------------------------------------------------
# Palette Browser
# ----------------------------------------------------------------------

class PaletteBrowser(QtWidgets.QWidget):
    """Displays all colors in a palette as clickable swatches."""

    color_clicked = QtCore.Signal(int)

    def __init__(
        self,
        parent: QtWidgets.QWidget | None = None,
    ):
        super().__init__(parent)

        self.palette: Palette | None = None
        self.buttons: list[PaletteColorButton] = []

        self.selected_index: int | None = None

        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self.main_layout = QtWidgets.QVBoxLayout(self)

        self.main_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        self.scroll_widget = QtWidgets.QWidget()

        self.grid_layout = QtWidgets.QGridLayout(
            self.scroll_widget
        )

        self.grid_layout.setContentsMargins(
            8,
            8,
            8,
            8,
        )

        self.grid_layout.setSpacing(8)

        self.grid_layout.setAlignment(
            QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft
        )

        self.scroll_area.setWidget(
            self.scroll_widget
        )

        self.main_layout.addWidget(
            self.scroll_area
        )

    # ------------------------------------------------------------------
    # Palette
    # ------------------------------------------------------------------

    def set_palette(
        self,
        palette: Palette,
    ) -> None:
        self.palette = palette
        self.selected_index = None

        self.refresh()

    def refresh(self) -> None:
        """Rebuild the color swatches."""

        self._clear_buttons()

        if not self.palette:
            return

        for index, color in enumerate(
            self.palette.colors
        ):
            button = PaletteColorButton(
                color=color,
                index=index,
            )

            button.clicked.connect(
                partial(
                    self._on_color_clicked,
                    index,
                )
            )

            row = index // SWATCH_COLUMNS
            column = index % SWATCH_COLUMNS

            self.grid_layout.addWidget(
                button,
                row,
                column,
            )

            self.buttons.append(button)

        self.update_selection()

    def _clear_buttons(self) -> None:
        for button in self.buttons:
            button.deleteLater()

        self.buttons.clear()

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    def _on_color_clicked(
        self,
        index: int,
    ) -> None:
        """
        Clicking an unselected color selects it.

        Clicking the selected color again clears the selection.
        """

        if self.selected_index == index:
            self.selected_index = None
        else:
            self.selected_index = index

        self.update_selection()

        self.color_clicked.emit(index)

    def update_selection(self) -> None:
        for button in self.buttons:
            button.set_selected(
                button.index == self.selected_index
            )

    def clear_selection(self) -> None:
        self.selected_index = None
        self.update_selection()


# ----------------------------------------------------------------------
# Palette Manager
# ----------------------------------------------------------------------

class PaletteManagerUI(QtWidgets.QDialog):
    """UI for creating and editing normal Workshop color palettes."""

    def __init__(
        self,
        parent: QtWidgets.QWidget | None = None,
    ):
        super().__init__(parent)

        self.current_palette = Palette(
            name="",
            colors=[],
            is_rig_palette=False,
        )

        self.current_color = (
            0.5,
            0.5,
            0.5,
        )

        self.palette_names: list[str] = []

        self.setObjectName(
            WINDOW_OBJECT_NAME
        )

        self.setWindowTitle(
            WINDOW_TITLE
        )

        self.resize(
            560,
            650,
        )

        self._build_ui()
        self._connect_signals()

        self.refresh_palette_list()
        self.reset_color_editor()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self.main_layout = QtWidgets.QVBoxLayout(
            self
        )

        self.main_layout.setSpacing(10)

        # --------------------------------------------------------------
        # Palette selection
        # --------------------------------------------------------------

        palette_group = QtWidgets.QGroupBox(
            "Palette"
        )

        palette_layout = QtWidgets.QVBoxLayout(
            palette_group
        )

        self.palette_combo = QtWidgets.QComboBox()
        self.palette_combo.setEditable(True)

        self.palette_combo.setInsertPolicy(
            QtWidgets.QComboBox.NoInsert
        )

        self.palette_combo.setPlaceholderText(
            "Choose or enter a palette name..."
        )

        palette_layout.addWidget(
            self.palette_combo
        )

        self.palette_status = QtWidgets.QLabel(
            "New Palette"
        )

        palette_layout.addWidget(
            self.palette_status
        )

        self.main_layout.addWidget(
            palette_group
        )

        # --------------------------------------------------------------
        # Palette browser
        # --------------------------------------------------------------

        browser_group = QtWidgets.QGroupBox(
            "Colors"
        )

        browser_layout = QtWidgets.QVBoxLayout(
            browser_group
        )

        self.palette_browser = PaletteBrowser()

        self.palette_browser.setMinimumHeight(
            250
        )

        browser_layout.addWidget(
            self.palette_browser
        )

        self.main_layout.addWidget(
            browser_group,
            1,
        )

        # --------------------------------------------------------------
        # Color editor
        # --------------------------------------------------------------

        editor_group = QtWidgets.QGroupBox(
            "Color"
        )

        editor_layout = QtWidgets.QVBoxLayout(
            editor_group
        )

        # Color name
        name_layout = QtWidgets.QHBoxLayout()

        name_label = QtWidgets.QLabel(
            "Name"
        )

        self.color_name_field = QtWidgets.QLineEdit()

        self.color_name_field.setPlaceholderText(
            "Optional color name..."
        )

        name_layout.addWidget(
            name_label
        )

        name_layout.addWidget(
            self.color_name_field,
            1,
        )

        editor_layout.addLayout(
            name_layout
        )

        # Color preview + picker
        color_layout = QtWidgets.QHBoxLayout()

        self.color_preview = QtWidgets.QPushButton()
        self.color_preview.setFixedHeight(42)

        self.pick_color_button = QtWidgets.QPushButton(
            "Pick Color"
        )

        color_layout.addWidget(
            self.color_preview,
            1,
        )

        color_layout.addWidget(
            self.pick_color_button
        )

        editor_layout.addLayout(
            color_layout
        )

        # RGB display
        self.rgb_label = QtWidgets.QLabel()

        editor_layout.addWidget(
            self.rgb_label
        )

        # Hex display
        self.hex_label = QtWidgets.QLabel()

        editor_layout.addWidget(
            self.hex_label
        )

        # Buttons
        button_layout = QtWidgets.QHBoxLayout()

        self.add_button = QtWidgets.QPushButton(
            "Add Color"
        )

        self.remove_button = QtWidgets.QPushButton(
            "Remove Color"
        )

        button_layout.addWidget(
            self.add_button
        )

        button_layout.addWidget(
            self.remove_button
        )

        editor_layout.addLayout(
            button_layout
        )

        self.main_layout.addWidget(
            editor_group
        )

        # --------------------------------------------------------------
        # Palette actions
        # --------------------------------------------------------------

        action_layout = QtWidgets.QHBoxLayout()

        self.refresh_button = QtWidgets.QPushButton(
            "Refresh"
        )

        self.save_button = QtWidgets.QPushButton(
            "Save Palette"
        )

        action_layout.addWidget(
            self.refresh_button
        )

        action_layout.addStretch()

        action_layout.addWidget(
            self.save_button
        )

        self.main_layout.addLayout(
            action_layout
        )

    # ------------------------------------------------------------------
    # Signals
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        self.palette_combo.activated.connect(
            self._palette_activated
        )

        line_edit = self.palette_combo.lineEdit()

        if line_edit:
            line_edit.editingFinished.connect(
                self._palette_editing_finished
            )

        self.palette_browser.color_clicked.connect(
            self._color_clicked
        )

        self.color_preview.clicked.connect(
            self.pick_color
        )

        self.pick_color_button.clicked.connect(
            self.pick_color
        )

        self.add_button.clicked.connect(
            self.add_or_update_color
        )

        self.remove_button.clicked.connect(
            self.remove_color
        )

        self.save_button.clicked.connect(
            self.save_current_palette
        )

        self.refresh_button.clicked.connect(
            self.refresh_palette_list
        )

    # ------------------------------------------------------------------
    # Palette list
    # ------------------------------------------------------------------

    def get_palette_names(self) -> list[str]:
        """Get all normal palette files."""

        PALETTE_FOLDER.mkdir(
            parents=True,
            exist_ok=True,
        )

        return sorted(
            path.stem
            for path in PALETTE_FOLDER.glob(
                "*.json"
            )
        )

    def refresh_palette_list(self) -> None:
        """Refresh palette names and autocomplete."""

        current_text = (
            self.palette_combo.currentText()
        )

        self.palette_names = (
            self.get_palette_names()
        )

        self.palette_combo.blockSignals(True)

        self.palette_combo.clear()
        self.palette_combo.addItems(
            self.palette_names
        )

        self.palette_combo.setEditText(
            current_text
        )

        self.palette_combo.blockSignals(False)

        completer = QtWidgets.QCompleter(
            self.palette_names,
            self.palette_combo,
        )

        completer.setCaseSensitivity(
            QtCore.Qt.CaseInsensitive
        )

        completer.setFilterMode(
            QtCore.Qt.MatchContains
        )

        completer.setCompletionMode(
            QtWidgets.QCompleter.PopupCompletion
        )

        self.palette_combo.setCompleter(
            completer
        )

    # ------------------------------------------------------------------
    # Palette selection
    # ------------------------------------------------------------------

    def _palette_activated(
        self,
        index: int,
    ) -> None:
        if index < 0:
            return

        name = self.palette_combo.itemText(
            index
        )

        self.set_palette_from_name(
            name
        )

    def _palette_editing_finished(self) -> None:
        name = (
            self.palette_combo.currentText()
            .strip()
        )

        if not name:
            return

        self.set_palette_from_name(
            name
        )

    def set_palette_from_name(
        self,
        name: str,
    ) -> None:
        """
        Load an existing palette or initialize a new palette.
        """

        filename_name = self._palette_filename(
            name
        )

        matching_palette = None

        for palette_name in self.palette_names:
            if (
                palette_name.lower()
                == filename_name.lower()
            ):
                matching_palette = palette_name
                break

        if matching_palette:
            self.current_palette = load_palette(
                matching_palette,
                rig_palette=False,
            )

            self.palette_status.setText(
                f"Editing: {self.current_palette.name}"
            )

        else:
            self.current_palette = Palette(
                name=name,
                colors=[],
                is_rig_palette=False,
            )

            self.palette_status.setText(
                f"New Palette: {name}"
            )

        self.palette_browser.set_palette(
            self.current_palette
        )

        self.reset_color_editor()

    @staticmethod
    def _palette_filename(
        name: str,
    ) -> str:
        return (
            name
            .strip()
            .lower()
            .replace(" ", "_")
        )

    # ------------------------------------------------------------------
    # Color selection
    # ------------------------------------------------------------------

    def _color_clicked(
        self,
        index: int,
    ) -> None:
        """
        Handle color swatch selection.

        PaletteBrowser has already toggled its selected index.
        """

        selected_index = (
            self.palette_browser.selected_index
        )

        if selected_index is None:
            self.reset_color_editor()
            return

        self.load_color_into_editor(
            selected_index
        )

    def load_color_into_editor(
        self,
        index: int,
    ) -> None:
        if not (
            0 <= index < len(
                self.current_palette.colors
            )
        ):
            return

        color = self.current_palette.colors[
            index
        ]

        self.current_color = color.rgb

        self.color_name_field.setText(
            color.name or ""
        )

        self.update_color_display()

        self.add_button.setText(
            "Update Color"
        )

        self.remove_button.setEnabled(
            True
        )

    def reset_color_editor(self) -> None:
        """Return the editor to new-color mode."""

        self.palette_browser.clear_selection()

        self.current_color = (
            0.5,
            0.5,
            0.5,
        )

        self.color_name_field.clear()

        self.add_button.setText(
            "Add Color"
        )

        self.remove_button.setEnabled(
            False
        )

        self.update_color_display()

    # ------------------------------------------------------------------
    # Color picker
    # ------------------------------------------------------------------

    def pick_color(self) -> None:
        initial_color = QtGui.QColor.fromRgbF(
            self.current_color[0],
            self.current_color[1],
            self.current_color[2],
        )

        color = QtWidgets.QColorDialog.getColor(
            initial_color,
            self,
            "Choose Color",
        )

        if not color.isValid():
            return

        self.current_color = (
            color.redF(),
            color.greenF(),
            color.blueF(),
        )

        self.update_color_display()

    def update_color_display(self) -> None:
        r, g, b = self.current_color

        rgb_255 = (
            round(r * 255),
            round(g * 255),
            round(b * 255),
        )

        hex_value = "#{:02X}{:02X}{:02X}".format(
            *rgb_255
        )

        self.color_preview.setStyleSheet(
            f"""
            QPushButton {{
                background-color: rgb(
                    {rgb_255[0]},
                    {rgb_255[1]},
                    {rgb_255[2]}
                );
                border: 1px solid #555555;
                border-radius: 4px;
            }}

            QPushButton:hover {{
                border: 2px solid #BBBBBB;
            }}
            """
        )

        self.rgb_label.setText(
            "RGB: "
            f"{r:.3f}, "
            f"{g:.3f}, "
            f"{b:.3f}"
        )

        self.hex_label.setText(
            f"Hex: {hex_value}"
        )

    # ------------------------------------------------------------------
    # Add / Update
    # ------------------------------------------------------------------

    def add_or_update_color(self) -> None:
        """Add a new color or update the selected one."""

        palette_name = (
            self.palette_combo.currentText()
            .strip()
        )

        if not palette_name:
            QtWidgets.QMessageBox.warning(
                self,
                "Palette Name Required",
                "Enter a palette name first.",
            )
            return

        self.current_palette.name = palette_name

        color_name = (
            self.color_name_field.text()
            .strip()
        )

        selected_index = (
            self.palette_browser.selected_index
        )

        # --------------------------------------------------------------
        # Update existing
        # --------------------------------------------------------------

        if selected_index is not None:
            color = self.current_palette.colors[
                selected_index
            ]

            color.rgb = self.current_color
            color.name = color_name or None

        # --------------------------------------------------------------
        # Add new
        # --------------------------------------------------------------

        else:
            if not color_name:
                color_name = self._generate_color_name()

            color = PaletteColor(
                name=color_name,
                rgb=self.current_color,
            )

            self.current_palette.add_color(
                color
            )

        self.palette_browser.refresh()

        self.reset_color_editor()

    def _generate_color_name(self) -> str:
        """Generate color_01, color_02, etc."""

        index = 1

        existing_names = {
            color.name
            for color in self.current_palette.colors
            if color.name
        }

        while True:
            name = f"color_{index:02d}"

            if name not in existing_names:
                return name

            index += 1

    # ------------------------------------------------------------------
    # Remove
    # ------------------------------------------------------------------

    def remove_color(self) -> None:
        selected_index = (
            self.palette_browser.selected_index
        )

        if selected_index is None:
            return

        if not (
            0 <= selected_index
            < len(self.current_palette.colors)
        ):
            return

        self.current_palette.colors.pop(
            selected_index
        )

        self.palette_browser.refresh()
        self.reset_color_editor()

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def save_current_palette(self) -> None:
        palette_name = (
            self.palette_combo.currentText()
            .strip()
        )

        if not palette_name:
            QtWidgets.QMessageBox.warning(
                self,
                "Palette Name Required",
                "Enter a palette name before saving.",
            )
            return

        self.current_palette.name = (
            palette_name
        )

        self.current_palette.is_rig_palette = (
            False
        )

        path = save_palette(
            self.current_palette
        )

        self.refresh_palette_list()

        self.palette_combo.setEditText(
            self.current_palette.name
        )

        self.palette_status.setText(
            f"Editing: {self.current_palette.name}"
        )

        QtWidgets.QMessageBox.information(
            self,
            "Palette Saved",
            f"Saved palette:\n{path}",
        )


# ----------------------------------------------------------------------
# Maya UI
# ----------------------------------------------------------------------

_palette_manager_window: PaletteManagerUI | None = None


def show_palette_manager() -> PaletteManagerUI:
    """Show the Workshop Palette Manager."""

    global _palette_manager_window

    if _palette_manager_window is not None:
        try:
            _palette_manager_window.close()
            _palette_manager_window.deleteLater()
        except RuntimeError:
            pass

    _palette_manager_window = PaletteManagerUI()
    _palette_manager_window.show()
    _palette_manager_window.raise_()
    _palette_manager_window.activateWindow()

    return _palette_manager_window