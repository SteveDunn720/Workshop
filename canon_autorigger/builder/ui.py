"""Workshop Rig Builder UI (Maya 2023+ with PySide2/6)."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

import maya.OpenMayaUI as omui

try:
    from PySide6 import QtCore, QtGui, QtWidgets
    from shiboken6 import wrapInstance
except ImportError:
    from PySide2 import QtCore, QtGui, QtWidgets
    from shiboken2 import wrapInstance

from Workshop import config
from Workshop.canon_autorigger.builder import assets
from.capture import capture_perspective_profile


# Optional integration: pass a Workshop snapshot callable to show_ui(),
# signature snapshot_callback(destination: pathlib.Path, size: int) -> None.
SnapshotCallback = Callable[[Path, int], None]
_WINDOW = None


def maya_main_window():
    ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(int(ptr), QtWidgets.QWidget) if ptr else None


class CollapsibleSection(QtWidgets.QWidget):
    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 2, 0, 2)
        outer.setSpacing(3)
        self.toggle = QtWidgets.QToolButton(text=label, checkable=True, checked=False)
        self.toggle.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.toggle.setArrowType(QtCore.Qt.RightArrow)
        self.toggle.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        outer.addWidget(self.toggle)
        self.body = QtWidgets.QWidget()
        self.content = QtWidgets.QVBoxLayout(self.body)
        self.content.setContentsMargins(8, 5, 8, 7)
        self.content.setSpacing(6)
        self.body.setVisible(False)
        outer.addWidget(self.body)
        self.toggle.toggled.connect(self._toggle)

    def _toggle(self, expanded):
        self.body.setVisible(expanded)
        self.toggle.setArrowType(QtCore.Qt.DownArrow if expanded else QtCore.Qt.RightArrow)


def _button(label: str, callback, tooltip: str = ''):
    button = QtWidgets.QPushButton(label)
    button.setToolTip(tooltip)
    button.clicked.connect(callback)
    return button


class AssetTab(QtWidgets.QWidget):
    def __init__(self, category: str, snapshot_callback: SnapshotCallback | None, parent=None):
        super().__init__(parent)
        self.category = category
        self.snapshot_callback = snapshot_callback
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(9, 9, 9, 9)
        outer.setSpacing(7)

        top = QtWidgets.QHBoxLayout()
        fields = QtWidgets.QVBoxLayout()
        self.asset_combo = QtWidgets.QComboBox()
        self.asset_combo.setEditable(True)
        self.asset_combo.setInsertPolicy(QtWidgets.QComboBox.NoInsert)
        self.asset_combo.setMinimumWidth(215)
        self.asset_combo.setPlaceholderText('Select or type an asset') if hasattr(self.asset_combo, 'setPlaceholderText') else None
        fields.addWidget(QtWidgets.QLabel('Asset'))
        fields.addWidget(self.asset_combo)
        self.variant_combo = QtWidgets.QComboBox()
        self.variant_combo.setEditable(True)
        self.variant_combo.addItem('main')
        self.variant_combo.setInsertPolicy(QtWidgets.QComboBox.NoInsert)
        fields.addWidget(QtWidgets.QLabel('Variant (placeholder)'))
        fields.addWidget(self.variant_combo)
        fields.addStretch()
        top.addLayout(fields, 1)

        profile_col = QtWidgets.QVBoxLayout()
        self.profile = QtWidgets.QLabel('No image')
        self.profile.setAlignment(QtCore.Qt.AlignCenter)
        self.profile.setFixedSize(125, 125)
        self.profile.setObjectName('profilePreview')
        profile_col.addWidget(self.profile, alignment=QtCore.Qt.AlignCenter)
        profile_col.addWidget(_button('Save Snapshot', self.take_snapshot))
        top.addLayout(profile_col)
        outer.addLayout(top)

        self.build_rig_button = _button('Build Rig', self.build_rig)
        self.build_rig_button.setMinimumHeight(32)
        self.build_rig_button.setToolTip('Build the selected rig (integration coming later).')
        outer.addWidget(self.build_rig_button)

        self.status = QtWidgets.QLabel('')
        self.status.setWordWrap(True)
        outer.addWidget(self.status)

        actions = QtWidgets.QGridLayout()
        action_names = [
            ('Validate / Initialize', self.validate_initialize),
            ('Export Skins', lambda: self.placeholder('Export Skins')),
            ('Load Guides File', lambda: self.placeholder('Load Guides File')),
            ('Export Defaults', lambda: self.placeholder('Export Defaults')),
            ('Generate Guides', lambda: self.placeholder('Generate Guides')),
            ('Export Control Shapes', lambda: self.placeholder('Export Control Shapes')),
            ('Open Guide Editor', lambda: self.placeholder('Open Guide Editor')),
            ('Export PSD / Shapes', lambda: self.placeholder('Export PSD / Shapes')),
            ('Export Guides', lambda: self.placeholder('Export Guides')),
        ]
        for index, (label, callback) in enumerate(action_names):
            actions.addWidget(_button(label, callback), index // 2, index % 2)
        outer.addLayout(actions)

        section = CollapsibleSection('Build Configs')
        self.face = QtWidgets.QCheckBox('Face')
        self.face.setChecked(True)
        section.content.addWidget(self.face)
        outer.addWidget(section)

        tests = CollapsibleSection('Tests')
        tests.content.addWidget(QtWidgets.QLabel('Rig tests'))
        self.rig_test = QtWidgets.QComboBox()
        self.rig_test.addItems(['Select rig test...', 'All Tests', 'Build Validation', 'Hierarchy', 'Skin Weights', 'Controls'])
        tests.content.addWidget(self.rig_test)
        tests.content.addWidget(_button('Run Rig Test', lambda: self.placeholder(f'Rig test: {self.rig_test.currentText()}')))
        tests.content.addWidget(QtWidgets.QLabel('Animation tests'))
        self.anim_test = QtWidgets.QComboBox()
        self.anim_test.addItems(['Select animation test...', 'Load Animation Test', 'Walk Cycle', 'Range of Motion'])
        tests.content.addWidget(self.anim_test)
        tests.content.addWidget(_button('Run Animation Test', lambda: self.placeholder(f'Animation test: {self.anim_test.currentText()}')))
        outer.addWidget(tests)

        publish = CollapsibleSection('Publish')
        publish.content.addWidget(_button('Validate Publish', lambda: self.placeholder('Validate Publish')))
        publish.content.addWidget(_button('Publish Rig', lambda: self.placeholder('Publish Rig')))
        outer.addWidget(publish)
        outer.addStretch()

        self.asset_combo.currentTextChanged.connect(self.update_state)
        self.refresh_assets()

    @property
    def name(self) -> str:
        return self.asset_combo.currentText().strip()

    def refresh_assets(self, selected: str | None = None):
        selected = self.name if selected is None else selected
        self.asset_combo.blockSignals(True)
        self.asset_combo.clear()
        names = assets.list_assets(self.category)
        self.asset_combo.addItems(names)
        completer = QtWidgets.QCompleter(names, self.asset_combo)
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        completer.setFilterMode(QtCore.Qt.MatchContains)
        self.asset_combo.setCompleter(completer)
        if selected:
            self.asset_combo.setEditText(selected)
        self.asset_combo.blockSignals(False)
        self.update_state()

    def update_state(self, *_):
        self.load_profile()
        if not self.name:
            self.status.setText('Select or type a name to get started.')
            return
        try:
            result = assets.validate_asset(self.category, self.name)
        except ValueError:
            self.status.setText('Invalid asset name. Use letters, numbers, _ or - (start with a letter).')
            return
        if result.valid:
            self.status.setText('Ready: required asset files are present.')
        elif not result.exists:
            self.status.setText('New asset — select Validate / Initialize to create it.')
        else:
            self.status.setText('Missing: ' + ', '.join(result.missing))

    def load_profile(self):
        self.profile.setPixmap(QtGui.QPixmap())
        self.profile.setText('No image')
        try:
            path = config.profile_path(self.category, assets.validate_name(self.name))
        except ValueError:
            return
        if path.is_file():
            pixmap = QtGui.QPixmap(str(path))
            if not pixmap.isNull():
                self.profile.setPixmap(pixmap.scaled(125, 125, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))

    def take_snapshot(self):
        try:
            path = config.profile_path(self.category, assets.validate_name(self.name))
        except ValueError as exc:
            QtWidgets.QMessageBox.warning(self, 'Snapshot', str(exc))
            return
        if path.exists():
            decision = QtWidgets.QMessageBox.question(
                self, 'Replace profile?', f'Replace existing profile image for {self.name}?',
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No,
            )
            if decision != QtWidgets.QMessageBox.Yes:
                return
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            if self.snapshot_callback is not None:
                self.snapshot_callback(path, config.SNAPSHOT_SIZE)
                generated = path
            else:
                generated = self._capture_profile(path)
            image = QtGui.QImage(str(generated))
            if image.isNull():
                raise RuntimeError(f'Snapshot image is not readable: {generated}')
            image = image.scaled(
                config.PROFILE_SIZE, config.PROFILE_SIZE,
                QtCore.Qt.KeepAspectRatioByExpanding,
                QtCore.Qt.SmoothTransformation,
            )
            x = (image.width() - config.PROFILE_SIZE) // 2
            y = (image.height() - config.PROFILE_SIZE) // 2
            image = image.copy(x, y, config.PROFILE_SIZE, config.PROFILE_SIZE)
            if not image.save(str(path), 'PNG'):
                raise RuntimeError(f'Could not save profile image: {path}')
            self.load_profile()
            print(f'[Workshop Builder] Saved profile image: {path}')
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, 'Snapshot failed', str(exc))

    def _capture_profile(self, target: Path) -> Path:
        """Capture the currently framed Maya perspective viewport."""
        return capture_perspective_profile(target, config.SNAPSHOT_SIZE)

    def validate_initialize(self):
        try:
            result = assets.validate_asset(self.category, self.name)
        except ValueError as exc:
            QtWidgets.QMessageBox.warning(self, 'Invalid asset name', str(exc))
            return
        if result.valid:
            QtWidgets.QMessageBox.information(self, 'Validation succeeded', f'{self.name} is initialized.\n{result.directory}')
            return
        title = 'Initialize Asset' if not result.exists else 'Repair Asset'
        description = ('Create a new asset directory?' if not result.exists
                       else 'Existing asset is missing required items:')
        if result.missing:
            description += '\n\n' + '\n'.join('• ' + item for item in result.missing)
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle(title)
        layout = QtWidgets.QVBoxLayout(dialog)
        label = QtWidgets.QLabel(f'{description}\n\nDestination: {result.directory}')
        label.setWordWrap(True)
        layout.addWidget(label)
        layout.addWidget(QtWidgets.QLabel('How should missing items be created?'))
        options = QtWidgets.QComboBox()
        options.addItems(['Create blank files', 'Copy available files from another asset'])
        layout.addWidget(options)
        source_combo = QtWidgets.QComboBox()
        source_combo.setEditable(True)
        source_combo.setInsertPolicy(QtWidgets.QComboBox.NoInsert)
        candidates = [x for x in assets.list_assets(self.category) if x != self.name]
        source_combo.addItems(candidates)
        default_source = config.DEFAULT_TEMPLATE.get(self.category)
        if default_source:
            source_combo.setEditText(default_source)
        source_combo.setEnabled(False)
        options.currentIndexChanged.connect(lambda index: source_combo.setEnabled(index == 1))
        layout.addWidget(source_combo)
        note = QtWidgets.QLabel('Existing files are preserved. Missing source files become blank Maya ASCII scenes.')
        note.setWordWrap(True)
        layout.addWidget(note)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return
        source = source_combo.currentText().strip() if options.currentIndex() == 1 else None
        if options.currentIndex() == 1 and not source:
            QtWidgets.QMessageBox.warning(self, 'Source required', 'Select an existing source asset.')
            return
        try:
            updated = assets.initialize_asset(self.category, self.name, source=source)
        except (OSError, ValueError) as exc:
            QtWidgets.QMessageBox.critical(self, 'Initialization failed', str(exc))
            return
        self.refresh_assets(self.name)
        if updated.valid:
            QtWidgets.QMessageBox.information(self, 'Initialized', f'Asset is ready:\n{updated.directory}')
        else:
            QtWidgets.QMessageBox.warning(self, 'Incomplete', 'Still missing: ' + ', '.join(updated.missing))

    def build_rig(self):
        """Placeholder for the Canon rig build entry point."""
        self.placeholder(f'Build Rig (face={self.face.isChecked()})')

    def placeholder(self, action: str):
        print(f'[Workshop Builder] {self.category} / {self.name} / {self.variant_combo.currentText()} : {action} (placeholder)')


class WorkshopBuilderUI(QtWidgets.QDialog):
    def __init__(self, snapshot_callback: SnapshotCallback | None = None, parent=None):
        super().__init__(parent or maya_main_window())
        self.setWindowTitle('Workshop | Rig Builder')
        self.setObjectName('workshopRigBuilder')
        self.setMinimumWidth(485)
        self.resize(520, 590)
        layout = QtWidgets.QVBoxLayout(self)
        self.tabs = QtWidgets.QTabWidget()
        self.asset_tabs = {}
        for category in config.ASSET_CATEGORIES:
            tab = AssetTab(category, snapshot_callback, self)
            self.asset_tabs[category] = tab
            self.tabs.addTab(tab, category)
        layout.addWidget(self.tabs)
        refresh = _button('Refresh Assets', self.refresh_assets)
        layout.addWidget(refresh)

    def refresh_assets(self):
        for tab in self.asset_tabs.values():
            tab.refresh_assets()


def show_ui(snapshot_callback: SnapshotCallback | None = None):
    """Open a single Maya-owned instance. Example: show_ui(snapshot_callback=my_capture)."""
    global _WINDOW
    if _WINDOW is not None:
        try:
            _WINDOW.close()
            _WINDOW.deleteLater()
        except RuntimeError:
            pass
    _WINDOW = WorkshopBuilderUI(snapshot_callback=snapshot_callback)
    _WINDOW.show()
    return _WINDOW
