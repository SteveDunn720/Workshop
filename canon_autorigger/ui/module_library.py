from __future__ import annotations

import maya.OpenMayaUI as omui
import maya.cmds as cmds

from Workshop.guide.module import get_module_relationships, get_module_settings, get_modules, set_module_setting, set_module_relationship
from Workshop.guide.resolver import resolve_module_instances

try:
    from PySide6 import QtCore, QtWidgets, QtGui
    from PySide6.QtCore import Signal
    from shiboken6 import wrapInstance

except ImportError:
    from PySide2 import QtCore, QtWidgets, QtGui
    from PySide2.QtCore import Signal
    from shiboken2 import wrapInstance

from Workshop.canon_autorigger.modules import (
    MODULE_REGISTRY,
    get_module_class,
)
from Workshop.canon_autorigger.module_schema import (
    ModuleGuideArray,
)
from Workshop.canon_autorigger.module_guides import (
    create_module_guides,
)

from Workshop.control.ui.shape_browser import (
    get_control_shape_library,
)
from Workshop.guide.hierarchy import (
    get_child_guides,
)
from Workshop.guide.core import is_guide

def maya_main_window() -> QtWidgets.QWidget:
    """Return Maya's main application window."""

    main_window_pointer = (
        omui.MQtUtil.mainWindow()
    )

    if main_window_pointer is None:
        raise RuntimeError(
            "Could not find Maya's main window."
        )

    return wrapInstance(
        int(main_window_pointer),
        QtWidgets.QWidget,
    )


class ControlSpaceWidget(QtWidgets.QWidget):
    """Editor for an ordered list of control spaces."""

    changed = Signal()

    def __init__(
        self,
        available_controls: list[str],
        parent: QtWidgets.QWidget | None = None,
    ) -> None:

        super().__init__(parent)

        self.available_controls = available_controls

        # --------------------------------------------------
        # LAYOUT
        # --------------------------------------------------

        layout = QtWidgets.QVBoxLayout(self)

        layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        layout.setSpacing(4)

        # --------------------------------------------------
        # AUTO
        # --------------------------------------------------

        self.auto_checkbox = QtWidgets.QCheckBox(
            "Auto"
        )

        self.auto_checkbox.setChecked(True)

        layout.addWidget(
            self.auto_checkbox
        )

        # --------------------------------------------------
        # SPACE LIST
        # --------------------------------------------------

        self.space_list = QtWidgets.QListWidget()

        self.space_list.setSelectionMode(
            QtWidgets.QAbstractItemView.SingleSelection
        )

        self.space_list.setMinimumHeight(70)

        layout.addWidget(
            self.space_list
        )

        # --------------------------------------------------
        # ADD ROW
        # --------------------------------------------------

        add_layout = QtWidgets.QHBoxLayout()

        add_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        self.space_combo = QtWidgets.QComboBox()

        self.space_combo.addItems(
            self.available_controls
        )

        self.add_button = QtWidgets.QPushButton(
            "+"
        )

        self.add_button.setFixedWidth(28)

        add_layout.addWidget(
            self.space_combo
        )

        add_layout.addWidget(
            self.add_button
        )

        layout.addLayout(
            add_layout
        )

        # --------------------------------------------------
        # EDIT ROW
        # --------------------------------------------------

        edit_layout = QtWidgets.QHBoxLayout()

        edit_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        self.remove_button = QtWidgets.QPushButton(
            "-"
        )

        self.up_button = QtWidgets.QPushButton(
            "↑"
        )

        self.down_button = QtWidgets.QPushButton(
            "↓"
        )

        edit_layout.addWidget(
            self.remove_button
        )

        edit_layout.addWidget(
            self.up_button
        )

        edit_layout.addWidget(
            self.down_button
        )

        layout.addLayout(
            edit_layout
        )

        # --------------------------------------------------
        # SIGNALS
        # --------------------------------------------------

        self.auto_checkbox.toggled.connect(
            self._auto_changed
        )

        self.add_button.clicked.connect(
            self._add_space
        )

        self.remove_button.clicked.connect(
            self._remove_space
        )

        self.up_button.clicked.connect(
            self._move_up
        )

        self.down_button.clicked.connect(
            self._move_down
        )

        self._update_enabled_state()

    # --------------------------------------------------
    # VALUE
    # --------------------------------------------------

    def value(self) -> str | list[str]:

        if self.auto_checkbox.isChecked():
            return "auto"

        return [
            self.space_list.item(index).text()
            for index in range(
                self.space_list.count()
            )
        ]

    def set_value(
        self,
        value: str | list[str] | None,
    ) -> None:

        self.space_list.clear()

        if (
            value is None
            or value == "auto"
        ):

            self.auto_checkbox.setChecked(
                True
            )

            self._update_enabled_state()

            return

        self.auto_checkbox.setChecked(
            False
        )

        if isinstance(value, str):
            value = [value]

        for control in value:

            self.space_list.addItem(
                control
            )

        self._update_enabled_state()

    # --------------------------------------------------
    # AUTO
    # --------------------------------------------------

    def _auto_changed(
        self,
        _state: bool,
    ) -> None:

        self._update_enabled_state()

        self.changed.emit()

    def _update_enabled_state(
        self,
    ) -> None:

        enabled = not self.auto_checkbox.isChecked()

        self.space_list.setEnabled(
            enabled
        )

        self.space_combo.setEnabled(
            enabled
        )

        self.add_button.setEnabled(
            enabled
        )

        self.remove_button.setEnabled(
            enabled
        )

        self.up_button.setEnabled(
            enabled
        )

        self.down_button.setEnabled(
            enabled
        )

    # --------------------------------------------------
    # ADD / REMOVE
    # --------------------------------------------------

    def _add_space(
        self,
    ) -> None:

        control = self.space_combo.currentText()

        if not control:
            return

        existing = [
            self.space_list.item(index).text()
            for index in range(
                self.space_list.count()
            )
        ]

        if control in existing:
            return

        self.space_list.addItem(
            control
        )

        self.changed.emit()

    def _remove_space(
        self,
    ) -> None:

        row = self.space_list.currentRow()

        if row < 0:
            return

        self.space_list.takeItem(
            row
        )

        self.changed.emit()

    # --------------------------------------------------
    # ORDER
    # --------------------------------------------------

    def _move_up(
        self,
    ) -> None:

        row = self.space_list.currentRow()

        if row <= 0:
            return

        item = self.space_list.takeItem(
            row
        )

        self.space_list.insertItem(
            row - 1,
            item
        )

        self.space_list.setCurrentRow(
            row - 1
        )

        self.changed.emit()

    def _move_down(
        self,
    ) -> None:

        row = self.space_list.currentRow()

        if (
            row < 0
            or row >= self.space_list.count() - 1
        ):
            return

        item = self.space_list.takeItem(
            row
        )

        self.space_list.insertItem(
            row + 1,
            item
        )

        self.space_list.setCurrentRow(
            row + 1
        )

        self.changed.emit()


class CollapsibleSection(QtWidgets.QWidget):
    """Simple collapsible UI section."""

    def __init__(
        self,
        title: str = "Section",
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.toggle_btn = QtWidgets.QToolButton()
        self.toggle_btn.setText(title)
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setChecked(True)

        self.toggle_btn.setToolButtonStyle(
            QtCore.Qt.ToolButtonTextBesideIcon
        )

        self.toggle_btn.setArrowType(
            QtCore.Qt.DownArrow
        )

        self.toggle_btn.clicked.connect(
            self.toggle
        )

        self.content = QtWidgets.QWidget()

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self.toggle_btn)
        layout.addWidget(self.content)

    def toggle(self) -> None:
        """Show or hide the section contents."""

        visible = self.toggle_btn.isChecked()

        self.content.setVisible(
            visible
        )

        self.toggle_btn.setArrowType(
            QtCore.Qt.DownArrow
            if visible
            else QtCore.Qt.RightArrow
        )


class ModuleLibrary(QtWidgets.QDialog):

    def __init__(
        self,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:

        if parent is None:
            parent = maya_main_window()

        super().__init__(parent)

        self.guide_count_spin = None

        self.setWindowTitle(
            "Module Library"
        )

        self.resize(
            500,
            600,
        )
        self.current_edit_module = None
        self.current_edit_part = None
        self.current_edit_guide = None

        self.dirty_settings: set[str] = set()
        self.dirty_relationships: set[str] = set()

        self._build_ui()
        self._connect_signals()

        self.refresh_module_ui()
        self.refresh_scene_guides()

    # --------------------------------------------------
    # UI
    # --------------------------------------------------

    def _build_ui(self):

        self.main_layout = QtWidgets.QVBoxLayout(
            self
        )

        self.main_layout.setContentsMargins(
            6,
            6,
            6,
            6,
        )

        self.main_layout.setSpacing(
            6
        )

        # ==================================================
        # ADD MODULE
        # ==================================================

        self.module_section = CollapsibleSection(
            title="Add Module"
        )

        self.main_layout.addWidget(
            self.module_section
        )

        self.module_layout = QtWidgets.QFormLayout(
            self.module_section.content
        )

        self.module_layout.setContentsMargins(
            6,
            4,
            6,
            6,
        )

        self.module_layout.setSpacing(4)


        # Module
        self.module_combo = QtWidgets.QComboBox()

        for module_name in sorted(
            MODULE_REGISTRY.keys()
        ):

            module_class = MODULE_REGISTRY[
                module_name
            ]

            display_name = getattr(
                module_class,
                "DISPLAY_NAME",
                module_name.title(),
            )

            self.module_combo.addItem(
                display_name,
                module_name,
            )


        # Part
        self.part_edit = QtWidgets.QLineEdit()

        self.part_edit.setPlaceholderText(
            "part"
        )


        # Side
        self.side_combo = QtWidgets.QComboBox()

        self.side_combo.addItems(
            [
                "M",
                "L",
                "R",
            ]
        )


        self.module_layout.addRow(
            "Module",
            self.module_combo,
        )

        self.module_layout.addRow(
            "Part",
            self.part_edit,
        )

        self.module_layout.addRow(
            "Side",
            self.side_combo,
        )


        # Dynamic guide-count UI gets inserted here.
        self.guide_count_spin = None


        # Add To Scene
        self.add_button = QtWidgets.QPushButton(
            "Add To Scene"
        )

        self.add_button.setMinimumHeight(28)

        self.module_layout.addRow(
            self.add_button
        )

        # ==================================================
        # SCENE GUIDES
        # ==================================================

        self.guide_section = CollapsibleSection(
            title="Guides"
        )

        self.main_layout.addWidget(
            self.guide_section
        )

        guide_container_layout = QtWidgets.QVBoxLayout(
            self.guide_section.content
        )

        guide_container_layout.setContentsMargins(
            6,
            4,
            6,
            6,
        )

        guide_container_layout.setSpacing(4)


        # Refresh row
        refresh_layout = QtWidgets.QHBoxLayout()

        refresh_layout.addStretch()

        self.refresh_guides_button = (
            QtWidgets.QPushButton("Refresh")
        )

        self.refresh_guides_button.setFixedWidth(70)

        refresh_layout.addWidget(
            self.refresh_guides_button
        )

        guide_container_layout.addLayout(
            refresh_layout
        )


        # Guide tree
        self.guide_tree = QtWidgets.QTreeWidget()

        self.guide_tree.setHeaderHidden(True)

        self.guide_tree.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection
        )

        guide_container_layout.addWidget(
            self.guide_tree
        )

        # ==================================================
        # SETTINGS
        # ==================================================

        self.settings_section = CollapsibleSection(
            title="Settings"
        )

        self.main_layout.addWidget(
            self.settings_section
        )

        # --------------------------------------------------
        # SETTINGS SECTION LAYOUT
        # --------------------------------------------------

        settings_container_layout = QtWidgets.QVBoxLayout(
            self.settings_section.content
        )

        settings_container_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        settings_container_layout.setSpacing(0)

        # --------------------------------------------------
        # SCROLL AREA
        # --------------------------------------------------

        self.settings_scroll_area = QtWidgets.QScrollArea()

        self.settings_scroll_area.setWidgetResizable(
            True
        )

        self.settings_scroll_area.setFrameShape(
            QtWidgets.QFrame.NoFrame
        )

        # Give Settings a useful amount of room,
        # but allow the dialog to remain compact.
        self.settings_scroll_area.setMinimumHeight(
            200
        )

        # --------------------------------------------------
        # SCROLL CONTENT
        # --------------------------------------------------

        self.settings_scroll_content = QtWidgets.QWidget()

        self.settings_layout = QtWidgets.QFormLayout(
            self.settings_scroll_content
        )

        self.settings_layout.setContentsMargins(
            6,
            4,
            6,
            6,
        )

        self.settings_layout.setSpacing(
            4
        )

        self.settings_scroll_area.setWidget(
            self.settings_scroll_content
        )

        settings_container_layout.addWidget(
            self.settings_scroll_area
        )

        # --------------------------------------------------
        # APPLY
        # --------------------------------------------------

        self.apply_settings_button = QtWidgets.QPushButton(
            "Apply Changes"
        )

        self.apply_settings_button.setMinimumHeight(
            28
        )

        settings_container_layout.addWidget(
            self.apply_settings_button
        )

        # --------------------------------------------------
        # WIDGET STORAGE
        # --------------------------------------------------

        # setting name -> Qt widget
        self.setting_widgets = {}

        # relationship name -> Qt widget
        self.relationship_widgets = {}

        # ==================================================
        # SPACER
        # ==================================================

        self.main_layout.addStretch()

    # --------------------------------------------------
    # SIGNALS
    # --------------------------------------------------


    def _connect_signals(self):

        self.module_combo.currentIndexChanged.connect(
            self.refresh_module_ui
        )

        self.add_button.clicked.connect(
            self.add_to_scene
        )
        self.refresh_guides_button.clicked.connect(
            self.refresh_scene_guides
        )
        self.guide_tree.itemSelectionChanged.connect(
            self.guide_selection_changed
        )

        self.apply_settings_button.clicked.connect(
            self.apply_selected_guide_settings
        )

    # --------------------------------------------------
    # CURRENT MODULE
    # --------------------------------------------------

    def get_selected_module_instances(
        self,
    ) -> list:

        selected_guides = set(
            self.get_selected_guides()
        )

        if not selected_guides:
            return []

        instances = resolve_module_instances()

        selected_instances = []

        for instance in instances:

            if any(
                guide in selected_guides
                for guide in instance.guides
            ):

                selected_instances.append(
                    instance
                )

        return selected_instances
    def mark_relationship_dirty(
        self,
        relationship_name: str,
    ) -> None:

        self.dirty_relationships.add(
            relationship_name
        )
    def get_previous_module_instances(
        self,
        guide: str,
        module: str,
        part: str,
    ) -> list:

        instances = resolve_module_instances()

        previous_instances = []

        for instance in instances:

            # Stop when we reach the module
            # currently being edited.
            if (
                instance.module == module
                and instance.part == part
                and guide in instance.guides
            ):
                break

            previous_instances.append(
                instance
            )

        return previous_instances

    def get_available_relationship_targets(
        self,
        guide: str,
        module: str,
        part: str,
    ) -> dict:

        instances = self.get_previous_module_instances(
            guide=guide,
            module=module,
            part=part,
        )

        joints = []
        controls = []

        for instance in instances:

            module_class = get_module_class(
                instance.module
            )

            settings = {}

            for setting in module_class.SETTINGS:

                settings[setting.name] = (
                    instance.settings.get(
                        setting.name,
                        setting.default,
                    )
                )

            preview = module_class.preview(
                part=instance.part,
                side=instance.side,
                guides=instance.guides,
                settings=settings,
            )

            joints.extend(
                preview.get(
                    "joints",
                    [],
                )
            )

            controls.extend(
                preview.get(
                    "controls",
                    [],
                )
            )

        return {
            "joints": joints,
            "controls": controls,
        }

    def clear_relationships_ui(
        self,
    ) -> None:

        self.relationship_widgets.clear()

    def create_relationship_widget(
        self,
        relationship,
        targets: dict,
    ) -> QtWidgets.QWidget | None:

        if relationship.relationship_type == "joint":

            widget = QtWidgets.QComboBox()

            widget.addItem("auto")

            widget.addItems(
                targets.get(
                    "joints",
                    [],
                )
            )

            widget.currentIndexChanged.connect(
                lambda _index, name=relationship.name:
                self.mark_relationship_dirty(name)
            )

            return widget

        # --------------------------------------------------
        # CONTROL SPACE
        # --------------------------------------------------

        if relationship.relationship_type == "control_space":

            widget = ControlSpaceWidget(
                available_controls=targets.get(
                    "controls",
                    [],
                )
            )

            widget.changed.connect(
                lambda name=relationship.name:
                self.mark_relationship_dirty(name)
            )

            return widget


    def mark_setting_dirty(
        self,
        setting_name: str,
    ) -> None:

        self.dirty_settings.add(
            setting_name
        )

    def get_selected_guides(
        self,
    ) -> list[str]:

        guides = []

        for item in self.guide_tree.selectedItems():

            guide = item.data(
                0,
                QtCore.Qt.UserRole,
            )

            if guide:
                guides.append(guide)

        return guides

    def guide_selection_changed(
        self,
    ) -> None:

        guides = self.get_selected_guides()

        if not guides:

            self.clear_settings_ui()
            self.clear_relationships_ui()

            self.current_edit_guide = None
            self.current_edit_module = None
            self.current_edit_part = None

            return

        guide = guides[0]

        modules = get_modules(
            guide
        )

        if not modules:

            self.clear_settings_ui()
            return

        module_info = modules[0]

        self.load_guide_settings(
            guide=guide,
            module=module_info.module,
            part=module_info.part,
        )

    def apply_selected_guide_settings(
        self,
    ) -> None:

        instances = self.get_compatible_selected_instances()

        if not instances:

            QtWidgets.QMessageBox.warning(
                self,
                "No Compatible Modules",
                "No compatible module instances are selected.",
            )

            return

        # --------------------------------------------------
        # NOTHING CHANGED
        # --------------------------------------------------

        if (
            not self.dirty_settings
            and not self.dirty_relationships
        ):

            print("No settings changed.")
            return

        # --------------------------------------------------
        # CURRENT UI VALUES
        # --------------------------------------------------

        settings = self.get_setting_values()

        relationships = self.get_relationship_values()

        updated = 0

        # --------------------------------------------------
        # APPLY TO SELECTED MODULE INSTANCES
        # --------------------------------------------------

        for instance in instances:

            if not instance.guides:
                continue

            # The first guide currently acts as the owner
            # of the module's stored data.
            owner_guide = instance.guides[0]

            # ----------------------------------------------
            # SETTINGS
            # ----------------------------------------------

            for setting_name in self.dirty_settings:

                if setting_name not in settings:
                    continue

                set_module_setting(
                    guide=owner_guide,
                    module=instance.module,
                    part=instance.part,
                    setting=setting_name,
                    value=settings[setting_name],
                )

            # ----------------------------------------------
            # RELATIONSHIPS
            # ----------------------------------------------

            for relationship_name in self.dirty_relationships:

                if relationship_name not in relationships:
                    continue

                set_module_relationship(
                    guide=owner_guide,
                    module=instance.module,
                    part=instance.part,
                    relationship=relationship_name,
                    value=relationships[
                        relationship_name
                    ],
                )

            updated += 1

        # --------------------------------------------------
        # REPORT
        # --------------------------------------------------

        print(
            f"Updated {updated} "
            f"{self.current_edit_module} "
            "module instance(s)"
        )

        if self.dirty_settings:

            print(
                "Changed settings:",
                sorted(self.dirty_settings),
            )

        if self.dirty_relationships:

            print(
                "Changed relationships:",
                sorted(
                    self.dirty_relationships
                ),
            )

        # --------------------------------------------------
        # RELOAD UI
        # --------------------------------------------------

        guide = self.current_edit_guide
        module = self.current_edit_module
        part = self.current_edit_part

        if (
            guide
            and module
            and part
        ):

            self.load_guide_settings(
                guide=guide,
                module=module,
                part=part,
            )

        else:

            self.dirty_settings.clear()
            self.dirty_relationships.clear()

    def get_relationship_values(
        self,
    ) -> dict:

        if self.current_edit_module is None:
            return {}

        module_class = get_module_class(
            self.current_edit_module
        )

        values = {}

        for relationship in module_class.RELATIONSHIPS:

            widget = self.relationship_widgets.get(
                relationship.name
            )

            if widget is None:
                continue

            if relationship.relationship_type == "joint":

                values[relationship.name] = (
                    widget.currentText()
                )

            elif relationship.relationship_type == "control_space":

                values[relationship.name] = (
                    widget.value()
                )

        return values

    def load_guide_settings(
        self,
        guide: str,
        module: str,
        part: str,
    ) -> None:

        self.current_edit_guide = guide
        self.current_edit_module = module
        self.current_edit_part = part

        self.clear_settings_ui()

        selected_instances = (
            self.get_compatible_selected_instances()
        )

        if len(selected_instances) > 1:

            guide_text = (
                f"{len(selected_instances)} "
                "module instances"
            )

        else:

            guide_text = guide

        module_class = get_module_class(
            module
        )

        # --------------------------------------------------
        # SELECTION
        # --------------------------------------------------

        self.settings_layout.addRow(
            "Selection",
            QtWidgets.QLabel(
                guide_text
            ),
        )

        # --------------------------------------------------
        # STORED DATA
        # --------------------------------------------------

        stored_settings = get_module_settings(
            guide,
            module=module,
            part=part,
        )

        stored_relationships = (
            get_module_relationships(
                guide,
                module=module,
                part=part,
            )
        )

        targets = (
            self.get_available_relationship_targets(
                guide=guide,
                module=module,
                part=part,
            )
        )

        # --------------------------------------------------
        # RELATIONSHIPS
        # --------------------------------------------------

        for relationship in module_class.RELATIONSHIPS:

            widget = self.create_relationship_widget(
                relationship=relationship,
                targets=targets,
            )

            if widget is None:
                continue

            value = stored_relationships.get(
                relationship.name,
                relationship.default,
            )

            # ----------------------------------------------
            # CONTROL SPACE
            # ----------------------------------------------

            if relationship.relationship_type == "control_space":

                widget.set_value(
                    value
                )

            # ----------------------------------------------
            # STANDARD COMBO RELATIONSHIPS
            # ----------------------------------------------

            elif value is not None:

                widget.setCurrentText(
                    str(value)
                )

            self.relationship_widgets[
                relationship.name
            ] = widget

            label = self.format_setting_name(
                relationship.name
            )

            self.settings_layout.addRow(
                label,
                widget,
            )

        # --------------------------------------------------
        # SETTINGS
        # --------------------------------------------------

        for setting in module_class.SETTINGS:

            widget = self.create_setting_widget(
                setting
            )

            if widget is None:
                continue

            value = stored_settings.get(
                setting.name,
                setting.default,
            )

            self.set_setting_widget_value(
                widget=widget,
                setting=setting,
                value=value,
            )

            self.setting_widgets[
                setting.name
            ] = widget

            label = self.format_setting_name(
                setting.name
            )

            self.settings_layout.addRow(
                label,
                widget,
            )

        # --------------------------------------------------
        # APPLY
        # --------------------------------------------------

        self.apply_settings_button = QtWidgets.QPushButton(
            "Apply Changes"
        )

        self.apply_settings_button.setMinimumHeight(
            28
        )

        self.apply_settings_button.clicked.connect(
            self.apply_selected_guide_settings
        )

        self.settings_layout.addRow(
            self.apply_settings_button
        )

        # --------------------------------------------------
        # RESET DIRTY STATE
        # --------------------------------------------------

        self.dirty_settings.clear()
        self.dirty_relationships.clear()


    def get_compatible_selected_instances(
        self,
    ) -> list:

        instances = (
            self.get_selected_module_instances()
        )

        if not instances:
            return []

        if self.current_edit_module is None:
            return []

        return [
            instance
            for instance in instances
            if instance.module
            == self.current_edit_module
        ]


    def set_setting_widget_value(
        self,
        widget,
        setting,
        value,
    ) -> None:

        if value is None:
            return

        if setting.setting_type == "float":

            widget.setValue(
                float(value)
            )

        elif setting.setting_type == "bool":

            widget.setChecked(
                bool(value)
            )

        elif setting.setting_type == "string":

            widget.setText(
                str(value)
            )

        elif setting.setting_type == "control_shape":

            index = widget.findText(
                str(value)
            )

            if index >= 0:
                widget.setCurrentIndex(
                    index
                )
    
    def get_current_module_name(
        self,
    ) -> str:

        return self.module_combo.currentData()

    def get_current_module_class(
        self,
    ):

        return get_module_class(
            self.get_current_module_name()
        )

    # --------------------------------------------------
    # GUIDE UI
    # --------------------------------------------------
    def get_setting_values(
        self,
    ) -> dict:

        if self.current_edit_module is None:
            return {}

        module_class = get_module_class(
            self.current_edit_module
        )

        values = {}

        for setting in module_class.SETTINGS:

            widget = self.setting_widgets.get(
                setting.name
            )

            if widget is None:
                continue

            if setting.setting_type == "float":

                values[setting.name] = (
                    widget.value()
                )

            elif setting.setting_type == "bool":

                values[setting.name] = (
                    widget.isChecked()
                )

            elif setting.setting_type == "control_shape":

                values[setting.name] = (
                    widget.currentText()
                )

            elif setting.setting_type == "string":

                values[setting.name] = (
                    widget.text().strip()
                )

        return values

    @staticmethod
    def format_setting_name(
        name: str,
    ) -> str:

        return name.replace(
            "_",
            " ",
        ).title()

    def create_setting_widget(
        self,
        setting,
    ) -> QtWidgets.QWidget | None:

        # --------------------------------------------------
        # FLOAT
        # --------------------------------------------------

        if setting.setting_type == "float":

            widget = QtWidgets.QDoubleSpinBox()

            widget.setRange(
                -10000.0,
                10000.0,
            )

            widget.setDecimals(3)
            widget.setSingleStep(0.1)

            if setting.default is not None:
                widget.setValue(
                    float(setting.default)
                )

            widget.valueChanged.connect(
                lambda _value, name=setting.name:
                self.mark_setting_dirty(name)
            )

            return widget

        # --------------------------------------------------
        # BOOL
        # --------------------------------------------------

        if setting.setting_type == "bool":

            widget = QtWidgets.QCheckBox()

            widget.setChecked(
                bool(setting.default)
            )

            widget.toggled.connect(
                lambda _value, name=setting.name:
                self.mark_setting_dirty(name)
            )

            return widget

        # --------------------------------------------------
        # STRING
        # --------------------------------------------------

        if setting.setting_type == "string":

            widget = QtWidgets.QLineEdit()

            if setting.default is not None:
                widget.setText(
                    str(setting.default)
                )

            # textEdited only fires when the user edits it.
            widget.textEdited.connect(
                lambda _value, name=setting.name:
                self.mark_setting_dirty(name)
            )

            return widget

        # --------------------------------------------------
        # CONTROL SHAPE
        # --------------------------------------------------

        if setting.setting_type == "control_shape":

            widget = QtWidgets.QComboBox()

            shape_library = (
                get_control_shape_library()
            )

            for shape_info in shape_library:

                widget.addItem(
                    shape_info.name
                )

            if setting.default is not None:

                index = widget.findText(
                    str(setting.default)
                )

                if index >= 0:
                    widget.setCurrentIndex(
                        index
                    )

            widget.currentIndexChanged.connect(
                lambda _index, name=setting.name:
                self.mark_setting_dirty(name)
            )

            return widget

        return None

    def refresh_settings_ui(
        self,
    ) -> None:

        self.clear_settings_ui()
        self.clear_relationships_ui()

        module_class = (
            self.get_current_module_class()
        )

        for setting in module_class.SETTINGS:

            widget = self.create_setting_widget(
                setting
            )

            if widget is None:
                continue

            self.setting_widgets[
                setting.name
            ] = widget

            label = self.format_setting_name(
                setting.name
            )
            self.selected_guide_label = QtWidgets.QLabel(
                "Guide: None"
            )

            self.selected_module_label = QtWidgets.QLabel(
                "Module: None"
            )

            self.settings_layout.addRow(
                label,
                widget,
            )

    def clear_settings_ui(
        self,
    ) -> None:

        while self.settings_layout.rowCount():

            self.settings_layout.removeRow(
                0
            )

        self.setting_widgets.clear()

    def clear_guide_count_ui(
        self,
    ) -> None:

        if self.guide_count_spin is not None:

            self.module_layout.removeRow(
                self.guide_count_spin
            )

            self.guide_count_spin = None

        if hasattr(
            self,
            "guide_count_label",
        ):

            self.module_layout.removeRow(
                self.guide_count_label
            )

            self.guide_count_label = None

    def refresh_module_ui(
        self,
        *args,
    ) -> None:

        self.clear_guide_count_ui()

        module_class = (
            self.get_current_module_class()
        )

        array_definition = None

        for definition in module_class.GUIDES:

            if isinstance(
                definition,
                ModuleGuideArray,
            ):
                array_definition = definition
                break

        # Variable guide count
        if array_definition is not None:

            self.guide_count_spin = (
                QtWidgets.QSpinBox()
            )

            self.guide_count_spin.setMinimum(
                array_definition.minimum_count
            )

            self.guide_count_spin.setMaximum(
                100
            )

            self.guide_count_spin.setValue(
                array_definition.default_count
            )

            # Insert before Add To Scene.
            row = self.module_layout.rowCount() - 1

            self.module_layout.insertRow(
                row,
                "Guide Count",
                self.guide_count_spin,
            )

        # Fixed guide count
        else:

            self.guide_count_label = (
                QtWidgets.QLabel(
                    str(
                        len(
                            module_class.GUIDES
                        )
                    )
                )
            )

            row = self.module_layout.rowCount() - 1

            self.module_layout.insertRow(
                row,
                "Guide Count",
                self.guide_count_label,
            )

    def refresh_scene_guides(
        self,
    ) -> None:

        self.guide_tree.clear()

        root = "root_M_guide"

        if not cmds.objExists(root):
            return

        root_item = QtWidgets.QTreeWidgetItem(
            [root]
        )

        root_item.setData(
            0,
            QtCore.Qt.UserRole,
            root,
        )

        self.guide_tree.addTopLevelItem(
            root_item
        )

        self._add_guide_children(
            parent_item=root_item,
            guide=root,
        )

        root_item.setExpanded(True)
    def _add_guide_children(
        self,
        parent_item,
        guide: str,
    ) -> None:

        children = get_child_guides(
            guide
        )

        for child in children:

            item = QtWidgets.QTreeWidgetItem(
                [child]
            )

            item.setData(
                0,
                QtCore.Qt.UserRole,
                child,
            )

            parent_item.addChild(
                item
            )

            self._add_guide_children(
                parent_item=item,
                guide=child,
            )

    # --------------------------------------------------
    # CREATE
    # --------------------------------------------------

    def add_to_scene(self):

        module = (
            self.get_current_module_name()
        )

        part = (
            self.part_edit
            .text()
            .strip()
        )

        side = (
            self.side_combo
            .currentText()
        )

        if not part:
            QtWidgets.QMessageBox.warning(
                self,
                "Missing Part Name",
                "Enter a part name before creating the module.",
            )
            return

        guide_count = None

        if self.guide_count_spin is not None:
            guide_count = (
                self.guide_count_spin.value()
            )

        try:

            guides = create_module_guides(
                module=module,
                part=part,
                side=side,
                guide_count=guide_count,
            )

        except Exception as error:

            QtWidgets.QMessageBox.critical(
                self,
                "Module Creation Failed",
                str(error),
            )

            raise

        self.refresh_scene_guides()

        print(
            f"Created {module} / "
            f"{part} / {side}"
        )

        for guide in guides:
            print(
                f"    {guide.name}"
            )

    

_module_library = None


def show_module_library():

    global _module_library

    if _module_library is not None:

        try:
            _module_library.close()
            _module_library.deleteLater()

        except RuntimeError:
            pass

    _module_library = ModuleLibrary()

    _module_library.show()

    return _module_library