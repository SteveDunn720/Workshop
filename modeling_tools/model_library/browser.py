"""Maya / PySide browser for the Workshop starter-model library.

Install at Workshop/modeling_tools/model_library/browser.py.
The assets, metadata and thumbnails remain in the external library directory.
"""
from __future__ import annotations

from pathlib import Path
from contextlib import contextmanager

import maya.cmds as cmds
import maya.OpenMayaUI as omui

from Workshop.modeling_tools.model_library.core import ModelAsset, ModelLibrary
from Workshop.snapshots.camera_core import (
    delete_snapshot_camera,
    place_snapshot_camera,
)

try:
    from PySide6 import QtCore, QtGui, QtWidgets
    from shiboken6 import wrapInstance
    Signal = QtCore.Signal
except ImportError:
    from PySide2 import QtCore, QtGui, QtWidgets
    from shiboken2 import wrapInstance
    Signal = QtCore.Signal


# Uses the temporary path agreed on for the external model library.
MODEL_LIB_PATH = Path(r"C:\Users\sldun\Documents\maya\projects\model_library")
_WINDOW = None


def maya_main_window():
    pointer = omui.MQtUtil.mainWindow()
    if pointer is None:
        raise RuntimeError("Cannot find Maya main window")
    return wrapInstance(int(pointer), QtWidgets.QWidget)


def selected_roots() -> list[str]:
    """Selected transforms, excluding descendants of other selected transforms."""
    items = cmds.ls(selection=True, long=True, transforms=True) or []
    items = list(dict.fromkeys(items))
    return [item for item in items if not any(item.startswith(other + "|") for other in items if other != item)]


@contextmanager
def snapshot_viewport_style(panel: str, camera: str):
    """Capture from a *specific* Maya panel, restoring all affected settings."""
    flags = (
        "useDefaultMaterial", "displayAppearance", "displayTextures",
        "displayLights", "wireframeOnShaded", "selectionHiliteDisplay",
        "grid", "cameras", "imagePlane",
    )
    original = {key: cmds.modelEditor(panel, query=True, **{key: True})
                for key in flags}
    original_camera = cmds.modelEditor(panel, query=True, camera=True)
    old_gradient = cmds.displayPref(query=True, displayGradient=True)
    background_names = ("background", "backgroundTop", "backgroundBottom")
    previous_colors = {name: cmds.displayRGBColor(name, query=True)
                       for name in background_names}
    try:
        cmds.displayPref(displayGradient=False)
        for name in background_names:
            cmds.displayRGBColor(name, 0.11, 0.11, 0.13)
        cmds.modelEditor(
            panel, edit=True, camera=camera,
            displayAppearance="smoothShaded",
            useDefaultMaterial=True,
            displayTextures=False,
            displayLights="default",
            wireframeOnShaded=False,
            selectionHiliteDisplay=False,
            grid=False,
            cameras=False,
            imagePlane=False,
        )
        cmds.refresh(force=True)
        yield
    finally:
        try:
            cmds.modelEditor(panel, edit=True, camera=original_camera, **original)
        finally:
            for name, value in previous_colors.items():
                if isinstance(value, str):
                    value = [float(v) for v in value.replace(",", " ").split()]
                cmds.displayRGBColor(name, *value[:3])
            cmds.displayPref(displayGradient=old_gradient)
            cmds.refresh(force=True)


def _snapshot_panel() -> str:
    """Choose a visible panel for an explicitly targeted thumbnail playblast."""
    focused = cmds.getPanel(withFocus=True)
    candidates = ([focused] if focused else []) + (cmds.getPanel(visiblePanels=True) or [])
    candidates += cmds.getPanel(type="modelPanel") or []
    for panel in dict.fromkeys(candidates):
        if cmds.getPanel(typeOf=panel) == "modelPanel":
            return panel
    raise RuntimeError("A Maya model panel is required to capture model icons")


def capture_model_icon(
    nodes: list[str],
    path: Path,
    stem: str,
    camera_mode: str = "current",
    padding: float = 1.35,
) -> Path:
    """Capture an isolated model using the current view or a framed camera.

    Current view preserves its existing framing and ignores padding.
    Snapshot camera frames from above and applies orthographic padding.
    """
    if camera_mode not in ("current", "snapshot"):
        raise ValueError(f"Unknown camera mode: {camera_mode}")
    if padding <= 0:
        raise ValueError("Snapshot padding must be greater than zero")
    if not nodes:
        raise ValueError("Select a model before capturing its icon")
    path.mkdir(parents=True, exist_ok=True)
    previous_selection = cmds.ls(selection=True, long=True) or []
    hidden: dict[str, bool] = {}
    preview_root = None
    created_camera = False
    try:
        preview_root = cmds.group(empty=True, name="__workshop_model_preview__#")
        for node in nodes:
            duplicate = cmds.duplicate(node, returnRootsOnly=True, renameChildren=True)[0]
            cmds.parent(duplicate, preview_root)
        for assembly in cmds.ls(assemblies=True, long=True) or []:
            if assembly == cmds.ls(preview_root, long=True)[0]:
                continue
            if not cmds.listRelatives(assembly, allDescendents=True, type="mesh", fullPath=True):
                continue
            plug = assembly + ".visibility"
            if not cmds.getAttr(plug, settable=True):
                continue
            hidden[plug] = bool(cmds.getAttr(plug))
            if hidden[plug]:
                cmds.setAttr(plug, False)
        panel = _snapshot_panel()
        if camera_mode == "current":
            # Never reframe or reposition the artist's viewport camera.
            camera = cmds.modelEditor(panel, query=True, camera=True)
        else:
            camera = place_snapshot_camera(
                obj=preview_root, swivel=45.0, tilt=-45.0, orthographic=True
            )
            created_camera = True
            camera_shape = (cmds.listRelatives(
                camera, shapes=True, type="camera", fullPath=True
            ) or [None])[0]
            if not camera_shape:
                raise RuntimeError("Snapshot camera has no camera shape")
            ortho_width = cmds.getAttr(f"{camera_shape}.orthographicWidth")
            cmds.setAttr(f"{camera_shape}.orthographicWidth", ortho_width * padding)

            # Different Workshop camera conventions may invert the tilt sign.
            # Ensure that the generated view is above the model in world Y.
            bbox = cmds.exactWorldBoundingBox(preview_root)
            center = [(bbox[i] + bbox[i + 3]) * 0.5 for i in range(3)]
            camera_pos = cmds.xform(camera, query=True, worldSpace=True, translation=True)
            if camera_pos[1] < center[1]:
                camera_pos[1] = 2.0 * center[1] - camera_pos[1]
                cmds.xform(camera, worldSpace=True, translation=camera_pos)
                target = cmds.spaceLocator(name="__workshop_snapshot_target__#")[0]
                try:
                    cmds.xform(target, worldSpace=True, translation=center)
                    aim = cmds.aimConstraint(
                        target,
                        camera,
                        aimVector=(0, 0, -1),
                        upVector=(0, 1, 0),
                        worldUpType="scene",
                    )
                    cmds.delete(aim)
                finally:
                    if cmds.objExists(target):
                        cmds.delete(target)
        cmds.select(clear=True)
        # Remove prior captures so we never accidentally pick a stale icon.
        expected = path / (stem + ".png")
        for old in path.glob(stem + ".*.png"):
            old.unlink()
        if expected.exists():
            expected.unlink()
        with snapshot_viewport_style(panel, camera):
            generated = cmds.playblast(
                editorPanelName=panel,
                format="image",
                compression="png",
                filename=str(path / stem),
                frame=cmds.currentTime(query=True),
                widthHeight=(512, 512),
                percent=100,
                quality=100,
                showOrnaments=False,
                viewer=False,
                forceOverwrite=True,
                offScreen=True,
            )
        captures = sorted(path.glob(stem + ".*.png"), key=lambda f: f.stat().st_mtime)
        if not captures:
            if not expected.is_file():
                raise RuntimeError(f"Maya playblast did not create an icon: {generated}")
        else:
            captures[-1].replace(expected)
        return expected
    finally:
        try:
            if created_camera:
                delete_snapshot_camera()
        finally:
            for plug, value in hidden.items():
                if cmds.objExists(plug):
                    try:
                        cmds.setAttr(plug, value)
                    except RuntimeError:
                        cmds.warning("Could not restore visibility: " + plug)
            if preview_root and cmds.objExists(preview_root):
                cmds.delete(preview_root)
            existing = [node for node in previous_selection if cmds.objExists(node)]
            cmds.select(existing, replace=True) if existing else cmds.select(clear=True)


class ModelAssetTile(QtWidgets.QAbstractButton):
    """Square thumbnail tile, following Workshop's ControlShapeTile style."""

    MIN_TILE_SIZE = 100
    MAX_TILE_SIZE = 140
    LABEL_HEIGHT = 18

    def __init__(self, asset: ModelAsset, parent=None):
        super().__init__(parent)
        self.asset = asset
        self.pixmap = QtGui.QPixmap(str(asset.icon_path)) if asset.icon_path else QtGui.QPixmap()
        self.setCheckable(True)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setToolTip(f"{asset.name}\nTags: {', '.join(asset.tags) or 'None'}")
        self.setFixedSize(self.MIN_TILE_SIZE, self.MIN_TILE_SIZE)

    def set_tile_size(self, size: int):
        size = max(self.MIN_TILE_SIZE, min(self.MAX_TILE_SIZE, size))
        self.setFixedSize(size, size)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, True)

        rect = self.rect().adjusted(2, 2, -2, -2)

        # -------------------------------------------------------------------------
        # Background
        # -------------------------------------------------------------------------

        if self.isDown():
            color = QtGui.QColor(45, 45, 45)
        elif self.underMouse():
            color = QtGui.QColor(65, 65, 65)
        else:
            color = QtGui.QColor(38, 38, 38)

        painter.fillRect(rect, color)

        # -------------------------------------------------------------------------
        # Thumbnail
        # -------------------------------------------------------------------------

        image_rect = rect.adjusted(0, 0, 0, -self.LABEL_HEIGHT)

        if not self.pixmap.isNull():
            scaled = self.pixmap.scaled(
                image_rect.size(),
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation,
            )

            painter.drawPixmap(
                image_rect.x() + (image_rect.width() - scaled.width()) // 2,
                image_rect.y() + (image_rect.height() - scaled.height()) // 2,
                scaled,
            )
        else:
            painter.setPen(QtGui.QColor(130, 130, 130))
            painter.drawText(
                image_rect,
                QtCore.Qt.AlignCenter,
                "—",
            )

        # -------------------------------------------------------------------------
        # Label
        # -------------------------------------------------------------------------

        label_rect = QtCore.QRect(
            rect.x(),
            rect.bottom() - self.LABEL_HEIGHT + 1,
            rect.width(),
            self.LABEL_HEIGHT,
        )

        painter.fillRect(
            label_rect,
            QtGui.QColor(0, 0, 0, 170),
        )

        painter.setPen(QtGui.QColor(235, 235, 235))

        font = painter.font()
        font.setPointSize(8)
        painter.setFont(font)

        label = painter.fontMetrics().elidedText(
            self.asset.name,
            QtCore.Qt.ElideRight,
            label_rect.width() - 10,
        )

        painter.drawText(
            label_rect.adjusted(5, 0, -5, 0),
            QtCore.Qt.AlignVCenter,
            label,
        )

        # -------------------------------------------------------------------------
        # Border
        # -------------------------------------------------------------------------

        if self.isChecked():
            border_color = self.palette().color(QtGui.QPalette.Highlight)
            border_width = 2
        elif self.underMouse():
            border_color = QtGui.QColor(100, 100, 100)
            border_width = 1
        else:
            border_color = QtGui.QColor(65, 65, 65)
            border_width = 1

        painter.setPen(QtGui.QPen(border_color, border_width))

        painter.drawRect(
            self.rect().adjusted(1, 1, -2, -2)
        )

        painter.end()


class ModelAssetBrowser(QtWidgets.QWidget):
    """Search, tag filter and alphabetically sorted model thumbnails."""

    selection_changed = Signal(object)

    def __init__(self, library: ModelLibrary, parent=None):
        super().__init__(parent)
        self.library = library
        self._assets: list[ModelAsset] = []
        self._tiles: list[ModelAssetTile] = []
        self._selected_path: Path | None = None
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        controls = QtWidgets.QHBoxLayout()
        self.search_field = QtWidgets.QLineEdit()
        self.search_field.setPlaceholderText("Search models and tags...")
        self.search_field.setClearButtonEnabled(True)
        self.tag_combo = QtWidgets.QComboBox()
        self.refresh_button = QtWidgets.QPushButton("Refresh")
        controls.addWidget(self.search_field, 1)
        controls.addWidget(self.tag_combo)
        controls.addWidget(self.refresh_button)
        layout.addLayout(controls)
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scroll_widget = QtWidgets.QWidget()
        self.grid = QtWidgets.QGridLayout(self.scroll_widget)
        self.grid.setContentsMargins(2, 2, 2, 2)
        self.grid.setSpacing(4)
        self.grid.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        self.scroll_area.setWidget(self.scroll_widget)
        layout.addWidget(self.scroll_area, 1)
        self.search_field.textChanged.connect(self._apply_filters)
        self.tag_combo.currentIndexChanged.connect(self._apply_filters)
        self.refresh_button.clicked.connect(self.refresh)
        self.refresh()

    @property
    def selected_asset(self) -> ModelAsset | None:
        return next((asset for asset in self._assets if asset.usd_path == self._selected_path), None)

    def refresh(self):
        current_tag = self.tag_combo.currentText()
        self._assets = self.library.list_assets()
        self.tag_combo.blockSignals(True)
        self.tag_combo.clear()
        self.tag_combo.addItem("All Tags")
        self.tag_combo.addItems(self.library.all_tags())
        index = self.tag_combo.findText(current_tag)
        self.tag_combo.setCurrentIndex(index if index >= 0 else 0)
        self.tag_combo.blockSignals(False)
        self._clear_tiles()
        for asset in self._assets:
            tile = ModelAssetTile(asset, self.scroll_widget)
            tile.clicked.connect(lambda checked=False, t=tile: self._select(t))
            self._tiles.append(tile)
        self._apply_filters()
        if self.selected_asset is None and self._tiles:
            self._select(self._tiles[0])
        else:
            self.selection_changed.emit(self.selected_asset)

    def _select(self, selected_tile: ModelAssetTile):
        self._selected_path = selected_tile.asset.usd_path
        for tile in self._tiles:
            tile.setChecked(tile is selected_tile)
        self.selection_changed.emit(selected_tile.asset)

    def _apply_filters(self, *_):
        query = self.search_field.text().strip().casefold()
        tag = self.tag_combo.currentText()
        for tile in self._tiles:
            asset = tile.asset
            matches_query = query in asset.name.casefold() or any(query in t.casefold() for t in asset.tags)
            matches_tag = tag == "All Tags" or tag.casefold() in (t.casefold() for t in asset.tags)
            tile.setVisible(matches_query and matches_tag)
        self._rebuild_grid()

    def _clear_tiles(self):
        self._clear_grid()
        for tile in self._tiles:
            tile.deleteLater()
        self._tiles.clear()

    def _clear_grid(self):
        while self.grid.count():
            self.grid.takeAt(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QtCore.QTimer.singleShot(0, self._rebuild_grid)

    def _rebuild_grid(self):
        visible = [t for t in self._tiles if not t.isHidden()]
        self._clear_grid()
        if not visible:
            return
        available = max(1, self.scroll_area.viewport().width() - 4)
        spacing = self.grid.horizontalSpacing()
        count = max(1, (available + spacing) // (ModelAssetTile.MIN_TILE_SIZE + spacing))
        size = (available - (count - 1) * spacing) // count
        while size > ModelAssetTile.MAX_TILE_SIZE:
            count += 1
            size = (available - (count - 1) * spacing) // count
        size = max(ModelAssetTile.MIN_TILE_SIZE, min(ModelAssetTile.MAX_TILE_SIZE, size))
        for index, tile in enumerate(visible):
            tile.set_tile_size(size)
            self.grid.addWidget(tile, index // count, index % count)
        self.grid.setColumnStretch(count, 1)


class ModelLibraryWindow(QtWidgets.QDialog):
    def __init__(self, parent=None, root: str | Path = MODEL_LIB_PATH):
        super().__init__(parent or maya_main_window())
        self.library = ModelLibrary(root)
        self.setWindowTitle("Workshop | Model Library")
        self.resize(620, 700)
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowTitleHint | QtCore.Qt.WindowCloseButtonHint)
        layout = QtWidgets.QVBoxLayout(self)
        self.browser = ModelAssetBrowser(self.library)
        layout.addWidget(self.browser, 1)

        self.placement_group = QtWidgets.QGroupBox("Model Placement")
        placement_layout = QtWidgets.QVBoxLayout(self.placement_group)
        self.placement_combo = QtWidgets.QComboBox()
        self.placement_combo.addItems(["At Origin", "At Selected", "Replace Selected"])
        self.place_button = QtWidgets.QPushButton("Create Model")
        placement_layout.addWidget(self.placement_combo)
        placement_layout.addWidget(self.place_button)
        layout.addWidget(self.placement_group)

        self.authoring_toggle = QtWidgets.QToolButton()
        self.authoring_toggle.setText("Model Authoring")
        self.authoring_toggle.setCheckable(True)
        self.authoring_toggle.setChecked(False)
        self.authoring_toggle.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.authoring_toggle.setArrowType(QtCore.Qt.RightArrow)
        self.authoring_group = QtWidgets.QWidget()
        self.authoring_group.setVisible(False)
        author_layout = QtWidgets.QFormLayout(self.authoring_group)
        self.name_field = QtWidgets.QLineEdit()
        self.name_field.setPlaceholderText("Model name")
        self.tags_field = QtWidgets.QLineEdit()
        self.tags_field.setPlaceholderText("Architecture, Modular, Stone")
        self.overwrite_checkbox = QtWidgets.QCheckBox("Overwrite existing asset")
        self.capture_checkbox = QtWidgets.QCheckBox("Generate icon")
        self.capture_checkbox.setChecked(True)
        self.camera_mode_combo = QtWidgets.QComboBox()
        self.camera_mode_combo.addItem("Current View (default)", "current")
        self.camera_mode_combo.addItem("Snapshot Camera (above model)", "snapshot")
        self.padding_spinbox = QtWidgets.QDoubleSpinBox()
        self.padding_spinbox.setRange(1.0, 3.0)
        self.padding_spinbox.setSingleStep(0.05)
        self.padding_spinbox.setDecimals(2)
        self.padding_spinbox.setValue(1.35)
        self.padding_spinbox.setToolTip("Framing multiplier for Snapshot Camera only")
        self.save_button = QtWidgets.QPushButton("Save Selected Model")
        author_layout.addRow("Name", self.name_field)
        author_layout.addRow("Tags", self.tags_field)
        author_layout.addRow(self.overwrite_checkbox)
        author_layout.addRow(self.capture_checkbox)
        author_layout.addRow("Icon Camera", self.camera_mode_combo)
        author_layout.addRow("Camera Padding", self.padding_spinbox)
        self.padding_label = author_layout.labelForField(self.padding_spinbox)
        author_layout.addRow(self.save_button)
        layout.addWidget(self.authoring_toggle)
        layout.addWidget(self.authoring_group)
        self.authoring_toggle.toggled.connect(self._toggle_authoring)
        self.camera_mode_combo.currentIndexChanged.connect(self._update_camera_options)
        self.capture_checkbox.toggled.connect(self._update_camera_options)
        self._update_camera_options()
        self.browser.selection_changed.connect(self._on_asset_selected)
        self.place_button.clicked.connect(self.place_model)
        self.save_button.clicked.connect(self.save_model)
        self._on_asset_selected(self.browser.selected_asset)

    def _update_camera_options(self, *_):
        enabled = self.capture_checkbox.isChecked()
        use_snapshot = self.camera_mode_combo.currentData() == "snapshot"
        self.camera_mode_combo.setEnabled(enabled)
        self.padding_spinbox.setVisible(enabled and use_snapshot)
        if self.padding_label:
            self.padding_label.setVisible(enabled and use_snapshot)

    def _toggle_authoring(self, expanded: bool):
        self.authoring_group.setVisible(expanded)
        self.authoring_toggle.setArrowType(
            QtCore.Qt.DownArrow if expanded else QtCore.Qt.RightArrow
        )

    def _on_asset_selected(self, asset: ModelAsset | None):
        self.place_button.setEnabled(asset is not None)
        if asset is not None:
            self.place_button.setToolTip(f"Import {asset.name}")

    def place_model(self):
        asset = self.browser.selected_asset
        if not asset:
            return
        mode = self.placement_combo.currentText()
        if mode == "Replace Selected":
            targets = selected_roots()
            if not targets:
                QtWidgets.QMessageBox.warning(self, "Nothing Selected", "Select models to replace.")
                return
            answer = QtWidgets.QMessageBox.question(
                self, "Replace Selected Models",
                f"Replace and delete {len(targets)} selected object(s)?\nThis can be undone in Maya.",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No,
            )
            if answer != QtWidgets.QMessageBox.Yes:
                return
        try:
            self.library.place(asset, mode=mode)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Model Placement Failed", str(exc))
            cmds.warning(str(exc))

    def save_model(self):
        name = self.name_field.text().strip()
        roots = selected_roots()
        if not name:
            QtWidgets.QMessageBox.warning(self, "Missing Name", "Enter a model name.")
            return
        if not roots:
            QtWidgets.QMessageBox.warning(self, "Nothing Selected", "Select model geometry first.")
            return
        tags = [tag.strip() for tag in self.tags_field.text().split(",") if tag.strip()]
        try:
            asset = self.library.save(
                name=name, nodes=roots, tags=tags, overwrite=self.overwrite_checkbox.isChecked()
            )
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Model Save Failed", str(exc))
            cmds.warning(str(exc))
            return
        if self.capture_checkbox.isChecked():
            try:
                capture_model_icon(
                    roots,
                    self.library.icons,
                    asset.usd_path.stem,
                    camera_mode=self.camera_mode_combo.currentData(),
                    padding=self.padding_spinbox.value(),
                )
            except Exception as exc:
                QtWidgets.QMessageBox.warning(
                    self, "Model Saved Without Icon", f"USD and metadata saved successfully.\n\nIcon capture failed:\n{exc}"
                )
        self.browser.refresh()
        for tile in self.browser._tiles:
            if tile.asset.usd_path == asset.usd_path:
                self.browser._select(tile)
                break


def show_model_library(root: str | Path = MODEL_LIB_PATH) -> ModelLibraryWindow:
    """Launch the browser from Maya's Python script editor."""
    global _WINDOW
    if _WINDOW is not None:
        try:
            _WINDOW.close()
            _WINDOW.deleteLater()
        except RuntimeError:
            pass
    _WINDOW = ModelLibraryWindow(root=root)
    _WINDOW.show()
    return _WINDOW
