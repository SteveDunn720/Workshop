from __future__ import annotations

import maya.cmds as cmds

try:
    from PySide6 import QtCore, QtWidgets
except ImportError:
    from PySide2 import QtCore, QtWidgets


from Workshop.snapshots import camera_core as utils


class CollapsibleSection(QtWidgets.QWidget):
    def __init__(self, title: str = "Section", parent=None) -> None:
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
        layout.addWidget(self.toggle_btn)
        layout.addWidget(self.content)

    def toggle(self) -> None:
        visible = self.toggle_btn.isChecked()
        self.content.setVisible(visible)
        self.toggle_btn.setArrowType(
            QtCore.Qt.DownArrow if visible else QtCore.Qt.RightArrow
        )


class SnapshotUI(QtWidgets.QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.setWindowTitle("Snapshot Tool")
        self.setMinimumWidth(400)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)

        main_layout = QtWidgets.QVBoxLayout(self)
        self._build_mode_section(main_layout)
        self._build_camera_section(main_layout)
        self._build_output_section(main_layout)
        self._build_capture_section(main_layout)
        self._build_manual_section(main_layout)

    def _build_mode_section(self, main_layout) -> None:
        section = CollapsibleSection("Snapshot Mode")
        layout = QtWidgets.QVBoxLayout(section.content)

        self.mode_dropdown = QtWidgets.QComboBox()
        self.mode_dropdown.addItems(
            ["Headshot", "Front", "3_Quarters", "Turntable", "Manual"]
        )
        self.mode_dropdown.currentIndexChanged.connect(self.apply_mode_preset)
        layout.addWidget(self.mode_dropdown)

        object_layout = QtWidgets.QHBoxLayout()
        self.obj_field = QtWidgets.QLineEdit()
        self.pick_btn = QtWidgets.QPushButton("Pick")
        self.pick_btn.clicked.connect(self.pick_object)
        object_layout.addWidget(self.obj_field)
        object_layout.addWidget(self.pick_btn)
        layout.addLayout(object_layout)

        main_layout.addWidget(section)

    def _build_camera_section(self, main_layout) -> None:
        section = CollapsibleSection("Camera Settings")
        layout = QtWidgets.QFormLayout(section.content)

        self.swivel = QtWidgets.QDoubleSpinBox()
        self.swivel.setRange(-360, 360)

        self.tilt = QtWidgets.QDoubleSpinBox()
        self.tilt.setRange(-360, 360)

        self.focal_length = QtWidgets.QDoubleSpinBox()
        self.focal_length.setRange(1, 300)
        self.focal_length.setValue(35)

        self.orthographic = QtWidgets.QCheckBox("Orthographic Camera")

        self.img_width = QtWidgets.QSpinBox()
        self.img_width.setRange(16, 8192)
        self.img_width.setValue(512)

        self.img_height = QtWidgets.QSpinBox()
        self.img_height.setRange(16, 8192)
        self.img_height.setValue(512)

        size_layout = QtWidgets.QHBoxLayout()
        size_layout.addWidget(self.img_width)
        size_layout.addWidget(self.img_height)

        layout.addRow("Swivel", self.swivel)
        layout.addRow("Tilt", self.tilt)
        layout.addRow("Focal Length", self.focal_length)
        layout.addRow("Orthographic", self.orthographic)
        layout.addRow("Image Size", size_layout)
        main_layout.addWidget(section)

    def _build_output_section(self, main_layout) -> None:
        section = CollapsibleSection("Output Settings")
        layout = QtWidgets.QFormLayout(section.content)

        default_path = (
            r"G:\dragonkisser\pipeline\pipeline\software\maya\scripts\rjg\camera_util"
        )
        self.path_field = QtWidgets.QLineEdit(default_path)

        browse_btn = QtWidgets.QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_folder)

        path_layout = QtWidgets.QHBoxLayout()
        path_layout.addWidget(self.path_field)
        path_layout.addWidget(browse_btn)

        self.snapshot_name = QtWidgets.QLineEdit("snapshot")
        self.export_json = QtWidgets.QCheckBox("Export Camera JSON")

        layout.addRow("Output Folder", path_layout)
        layout.addRow("File Name", self.snapshot_name)
        layout.addRow("", self.export_json)
        main_layout.addWidget(section)

    def _build_capture_section(self, main_layout) -> None:
        section = CollapsibleSection("Capture Options")
        layout = QtWidgets.QVBoxLayout(section.content)

        frame_layout = QtWidgets.QHBoxLayout()
        self.start_frame = QtWidgets.QSpinBox()
        self.start_frame.setValue(1)
        self.end_frame = QtWidgets.QSpinBox()
        self.end_frame.setValue(30)

        timeline_btn = QtWidgets.QPushButton("Use Timeline")
        timeline_btn.clicked.connect(self.copy_timeline_range)
        frame_layout.addWidget(self.start_frame)
        frame_layout.addWidget(self.end_frame)
        frame_layout.addWidget(timeline_btn)
        layout.addLayout(frame_layout)

        snapshot_btn = QtWidgets.QPushButton("Take Snapshot")
        snapshot_btn.clicked.connect(self.snapshot)
        playblast_btn = QtWidgets.QPushButton("Playblast")
        playblast_btn.clicked.connect(self.playblast)
        layout.addWidget(snapshot_btn)
        layout.addWidget(playblast_btn)
        main_layout.addWidget(section)

    def _build_manual_section(self, main_layout) -> None:
        section = CollapsibleSection("Manual Mode")
        layout = QtWidgets.QVBoxLayout(section.content)

        manual_camera_btn = QtWidgets.QPushButton("Manual Camera")
        manual_camera_btn.clicked.connect(self.manual_camera)
        manual_snapshot_btn = QtWidgets.QPushButton("Manual Snapshot")
        manual_snapshot_btn.clicked.connect(self.manual_snapshot)
        layout.addWidget(manual_camera_btn)
        layout.addWidget(manual_snapshot_btn)
        main_layout.addWidget(section)

    def apply_mode_preset(self) -> None:
        presets = {
            "Front": (0, 0),
            "Headshot": (0, 10),
            "3_Quarters": (45, 10),
            "Turntable": (0, 10),
        }
        preset = presets.get(self.mode_dropdown.currentText())
        if preset:
            self.swivel.setValue(preset[0])
            self.tilt.setValue(preset[1])

    def pick_object(self) -> None:
        selection = cmds.ls(selection=True) or []
        if not selection:
            return

        self.obj_field.setText(selection[0])
        self.obj_field.setStyleSheet(
            "QLineEdit { background-color: rgb(60,120,60); color: white; }"
        )

    def browse_folder(self) -> None:
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "Select Output Folder",
        )
        if folder:
            self.path_field.setText(folder)

    def copy_timeline_range(self) -> None:
        start = cmds.playbackOptions(query=True, min=True)
        end = cmds.playbackOptions(query=True, max=True)
        self.start_frame.setValue(int(start))
        self.end_frame.setValue(int(end))

    def confirm_camera_replacement(self) -> bool:
        if not utils.snapshot_camera_exists():
            return True

        message = QtWidgets.QMessageBox(self)
        message.setWindowTitle("Snapshot Camera Exists")
        message.setText("A snapshot camera already exists.")
        clear_btn = message.addButton(
            "Clear Camera",
            QtWidgets.QMessageBox.AcceptRole,
        )
        message.addButton("Cancel", QtWidgets.QMessageBox.RejectRole)
        message.exec_()

        if message.clickedButton() != clear_btn:
            return False

        utils.delete_snapshot_camera()
        return True

    def build_camera(self) -> str | None:
        if not self.confirm_camera_replacement():
            return None

        obj = self.obj_field.text().strip()
        if not cmds.objExists(obj):
            cmds.warning("Object does not exist.")
            return None

        try:
            camera = utils.place_snapshot_camera(
                obj,
                swivel=self.swivel.value(),
                tilt=self.tilt.value(),
                focal_length=self.focal_length.value(),
                orthographic=self.orthographic.isChecked(),
            )

            if self.mode_dropdown.currentText() == "Turntable":
                utils.build_turntable(
                    self.start_frame.value(),
                    self.end_frame.value(),
                )
        except (RuntimeError, ValueError) as error:
            cmds.warning(str(error))
            return None

        return camera

    def snapshot(self) -> None:
        camera = self.build_camera()
        if not camera:
            return

        path = self.path_field.text().strip()
        name = self.snapshot_name.text().strip() or "snapshot"
        utils.take_snapshot(
            camera,
            path,
            self.img_width.value(),
            self.img_height.value(),
            name,
        )

        if self.export_json.isChecked():
            utils.export_camera_json(camera, path, f"{name}_camera")

    def playblast(self) -> None:
        camera = self.build_camera()
        if not camera:
            return

        path = self.path_field.text().strip()
        name = self.snapshot_name.text().strip() or "playblast"
        utils.take_playblast(
            camera,
            path,
            self.start_frame.value(),
            self.end_frame.value(),
            self.img_width.value(),
            self.img_height.value(),
            name,
        )

        if self.export_json.isChecked():
            utils.export_camera_json(camera, path, f"{name}_camera")

    def manual_camera(self) -> None:
        if not self.confirm_camera_replacement():
            return

        obj = self.obj_field.text().strip()
        if not cmds.objExists(obj):
            cmds.warning("Object does not exist.")
            return

        try:
            utils.place_snapshot_camera(
                obj,
                swivel=self.swivel.value(),
                tilt=self.tilt.value(),
                focal_length=self.focal_length.value(),
                orthographic=self.orthographic.isChecked(),
            )
        except (RuntimeError, ValueError) as error:
            cmds.warning(str(error))

    def manual_snapshot(self) -> None:
        if not cmds.objExists(utils.SNAPSHOT_CAMERA):
            cmds.warning("Snapshot camera does not exist.")
            return

        path = self.path_field.text().strip()
        name = self.snapshot_name.text().strip() or "snapshot"
        utils.take_snapshot(
            utils.SNAPSHOT_CAMERA,
            path,
            self.img_width.value(),
            self.img_height.value(),
            name,
        )

        if self.export_json.isChecked():
            utils.export_camera_json(
                utils.SNAPSHOT_CAMERA,
                path,
                f"{name}_camera",
            )


snapshot_ui = None


def run() -> None:
    global snapshot_ui

    if snapshot_ui is not None:
        snapshot_ui.close()
        snapshot_ui.deleteLater()

    snapshot_ui = SnapshotUI()
    snapshot_ui.show()