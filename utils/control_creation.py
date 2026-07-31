
from __future__ import annotations


try:
    from PySide6 import QtCore, QtWidgets
except ImportError:
    from PySide2 import QtCore, QtWidgets

import maya.cmds as cmds

from Workshop.transform.utils import create_transform
from Workshop.snapshots.image_planes import create_control_helper_plane
from Workshop.control.core import  _create_control_curve
from Workshop.control.serialize import write_curve_to_library
from Workshop.snapshots.camera_core import delete_snapshot_camera, place_snapshot_camera, take_snapshot


from pathlib import Path

WORKSHOP_ROOT = Path(__file__).resolve().parents[1]  # Adjust if needed
IMAGE_PATH = WORKSHOP_ROOT / "control" / "AA_control_sizer.png"
ICON_PATH = WORKSHOP_ROOT / "control" / "shape_icons"


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

        clean_btn = QtWidgets.QPushButton("Clean Scene")
        clean_btn.clicked.connect(self.clean_scene)

        setup_layout.addWidget(setup_btn)

        setup_layout.addWidget(clean_btn)

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

        self.use_selected_checkbox = QtWidgets.QCheckBox("Use Selected")
        control_layout.addRow("", self.use_selected_checkbox)

        main_layout.addWidget(control_section)

    # -------------------------------------------------
    # UI Values
    # -------------------------------------------------

    @property
    def control_name(self) -> str:
        """Return the current text from the name field.""" #self.control_name
        return self.name_field.text().strip()
    
    @property
    def use_selected(self) -> bool:
        """Whether to use the selected object.""" #self.use_selected
        return self.use_selected_checkbox.isChecked()

    # -------------------------------------------------
    # Button Functions
    # -------------------------------------------------

    def clean_scene(self) -> None:
        """Set up the scene for control creation."""
        cmds.delete('control_creater_helper_grp')

    def setup_scene(self) -> None:
        """Set up the scene for control creation."""
        parent_tform = create_transform(name='control_creater_helper_grp')
        tform, shp = create_control_helper_plane(
            image_path=str(IMAGE_PATH),
            name="reference_image",
        )

        cmds.parent(tform, parent_tform)
        cmds.setAttr(f"{shp}.alphaGain", .5)
        

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

        if self.use_selected:
            ctrl_shp = cmds.ls(selection=True)[0]

        else:
            ctrl_shp = self.control_name
        
        write_curve_to_library(curve=str(ctrl_shp), name=self.control_name, force = True)

        if cmds.objExists('control_creater_helper_grp'):
            cmds.setAttr('control_creater_helper_grp.visibility', False)

        camera = place_snapshot_camera(
            obj=ctrl_shp,
            swivel=45.0,
            tilt=45.0,
            orthographic=True,
        )

        take_snapshot(
            camera=camera,
            path=ICON_PATH,
            name=self.control_name,
        )

        delete_snapshot_camera()
    

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
        
        _create_control_curve(
            name= control_name,
            control_shape = control_name,
        )

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

