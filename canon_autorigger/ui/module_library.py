from __future__ import annotations

import maya.OpenMayaUI as omui
import maya.cmds as cmds

from Workshop.guide.module import get_module_settings, get_modules, set_module_setting
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

        self.settings_layout = QtWidgets.QFormLayout(
            self.settings_section.content
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

        # Stores:
        # setting name -> Qt widget
        self.setting_widgets = {}

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

    # --------------------------------------------------
    # CURRENT MODULE
    # --------------------------------------------------

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
        self.settings_layout.addRow(
            "Selection",
            QtWidgets.QLabel(
                guide_text
            ),
        )

        stored_settings = get_module_settings(
            guide,
            module=module,
            part=part,
        )

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
        self.apply_settings_button = (
            QtWidgets.QPushButton(
                "Apply Changes"
            )
        )

        self.apply_settings_button.setMinimumHeight(
            26
        )

        self.apply_settings_button.clicked.connect(
            self.apply_selected_guide_settings
        )

        self.settings_layout.addRow(
            self.apply_settings_button
        )

    def apply_selected_guide_settings(
        self,
    ) -> None:

        instances = (
            self.get_compatible_selected_instances()
        )

        if not instances:

            QtWidgets.QMessageBox.warning(
                self,
                "No Compatible Modules",
                (
                    "None of the selected guides belong "
                    "to the module type currently being edited."
                ),
            )

            return

        settings = self.get_setting_values()

        updated = 0

        for instance in instances:

            if not instance.guides:
                continue

            # First guide owns the settings for
            # this module instance.
            owner_guide = instance.guides[0]

            for setting_name, value in settings.items():

                set_module_setting(
                    guide=owner_guide,
                    module=instance.module,
                    part=instance.part,
                    setting=setting_name,
                    value=value,
                )

            updated += 1

        print(
            f"Updated {updated} "
            f"{self.current_edit_module} "
            f"module instance(s)"
        )

        # Reload the primary edited module.
        if self.current_edit_guide:

            self.load_guide_settings(
                guide=self.current_edit_guide,
                module=self.current_edit_module,
                part=self.current_edit_part,
            )

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

        module_class = (
            self.get_current_module_class()
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

            return widget

        # --------------------------------------------------
        # BOOL
        # --------------------------------------------------

        if setting.setting_type == "bool":

            widget = QtWidgets.QCheckBox()

            widget.setChecked(
                bool(setting.default)
            )

            return widget

        # --------------------------------------------------
        # String
        # --------------------------------------------------


        if setting.setting_type == "string":

            widget = QtWidgets.QLineEdit()

            if setting.default is not None:
                widget.setText(
                    str(setting.default)
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

            # Set schema default
            if setting.default is not None:

                index = widget.findText(
                    str(setting.default)
                )

                if index >= 0:
                    widget.setCurrentIndex(
                        index
                    )

            return widget

        return None

    def refresh_settings_ui(
        self,
    ) -> None:

        self.clear_settings_ui()

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