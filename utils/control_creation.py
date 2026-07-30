
from __future__ import annotations

try:
    from PySide6 import QtCore, QtWidgets
except ImportError:
    from PySide2 import QtCore, QtWidgets


# -------------------------------------------------
# Collapsible Section
# -------------------------------------------------

class CollapsibleSection(QtWidgets.QWidget):
    """Simple collapsible UI section."""

    def __init__(self, title: str = "Section"):
        super().__init__()

        self.toggle_btn = QtWidgets.QToolButton()
        self.toggle_btn.setText(title)
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setChecked(True)
        self.toggle_btn.setToolButtonStyle(
            QtCore.Qt.ToolButtonTextBesideIcon
        )
        self.toggle_btn.setArrowType(QtCore.Qt.DownArrow)
        self.toggle_btn.clicked.connect(self.toggle)

        self.content = QtWidgets.QWidget()

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
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


# -------------------------------------------------
# Control Creator UI
# -------------------------------------------------

class ControlCreatorUI(QtWidgets.QDialog):
    """UI for creating, saving, and loading control shapes."""

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Control Creator")
        self.setMinimumWidth(400)

        self.setWindowFlags(
            self.windowFlags()
            | QtCore.Qt.WindowStaysOnTopHint
        )

        self.build_ui()

    # -------------------------------------------------
    # Build UI
    # -------------------------------------------------

    def build_ui(self) -> None:
        """Build the main UI layout."""
        main_layout = QtWidgets.QVBoxLayout(self)

        self.build_scene_setup_section(main_layout)
        self.build_control_section(main_layout)

    def build_scene_setup_section(
        self,
        main_layout: QtWidgets.QVBoxLayout,
    ) -> None:
        """Build the scene setup section."""
        setup_section = CollapsibleSection("Scene Setup")
        setup_layout = QtWidgets.QVBoxLayout(
            setup_section.content
        )

        setup_btn = QtWidgets.QPushButton("Setup Scene")
        setup_btn.clicked.connect(self.setup_scene)

        setup_layout.addWidget(setup_btn)

        main_layout.addWidget(setup_section)

    def build_control_section(
        self,
        main_layout: QtWidgets.QVBoxLayout,
    ) -> None:
        """Build the control shape section."""
        control_section = CollapsibleSection("Control")
        control_layout = QtWidgets.QFormLayout(
            control_section.content
        )

        self.name_field = QtWidgets.QLineEdit()
        self.name_field.setPlaceholderText("Control Name")

        control_layout.addRow("Name", self.name_field)

        save_btn = QtWidgets.QPushButton(
            "Save Out Control"
        )
        save_btn.clicked.connect(self.save_control)

        load_btn = QtWidgets.QPushButton("Load Shape")
        load_btn.clicked.connect(self.load_shape)

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addWidget(save_btn)
        button_layout.addWidget(load_btn)

        control_layout.addRow("", button_layout)

        main_layout.addWidget(control_section)

    # -------------------------------------------------
    # UI Values
    # -------------------------------------------------

    @property
    def control_name(self) -> str:
        """Return the current text from the name field."""
        return self.name_field.text().strip()

    # -------------------------------------------------
    # Button Functions
    # -------------------------------------------------

    def setup_scene(self) -> None:
        """Set up the scene for control creation."""
        print("Setup Scene")

        # Add your scene setup code here.

    def save_control(self) -> None:
        """Save the control using the current name."""
        control_name = self.control_name

        if not control_name:
            QtWidgets.QMessageBox.warning(
                self,
                "Missing Control Name",
                "Enter a control name before saving.",
            )
            return

        print(f"Save Control: {control_name}")

        # Add your save control code here.
        #
        # Example:
        # save_control_shape(control_name)

    def load_shape(self) -> None:
        """Load the control shape using the current name."""
        control_name = self.control_name

        if not control_name:
            QtWidgets.QMessageBox.warning(
                self,
                "Missing Control Name",
                "Enter a control name before loading.",
            )
            return

        print(f"Load Shape: {control_name}")

        # Add your load control shape code here.
        #
        # Example:
        # load_control_shape(control_name)


# -------------------------------------------------
# Run
# -------------------------------------------------

def run() -> None:
    """Open the Control Creator UI."""
    global control_creator_ui

    try:
        control_creator_ui.close()
        control_creator_ui.deleteLater()
    except (NameError, RuntimeError):
        pass

    control_creator_ui = ControlCreatorUI()
    control_creator_ui.show()

