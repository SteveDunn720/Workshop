import maya.cmds as mc
import maya.api.OpenMaya as om
import maya.OpenMayaUI as omui
try:
    from PySide6 import QtWidgets, QtCore
    from shiboken6 import wrapInstance
except:
    from PySide2 import QtWidgets, QtCore
    from shiboken2 import wrapInstance


from Workshop.UE_asset_export.auto_lod_export import export_verified_asset


# -----------------------------
# Maya Main Window
# -----------------------------
def maya_main_window():
    ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(int(ptr), QtWidgets.QWidget)


# -----------------------------
# KITBASH SCAN
# -----------------------------
def scan_kitbash_assets():

    if not mc.objExists("Kitbash"):
        return []

    children = mc.listRelatives(
        "Kitbash",
        children=True,
        type="transform"
    ) or []

    assets = []

    for c in children:
        if c.endswith("_grp"):
            assets.append(c)

    return sorted(set(assets))


# -----------------------------
# MAIN UI
# -----------------------------
class KitbashAssetTool(QtWidgets.QDialog):

    WINDOW_TITLE = "Kitbash Asset Tool"

    def __init__(self, parent=maya_main_window()):
        super().__init__(parent)

        self.setWindowTitle(self.WINDOW_TITLE)
        self.setMinimumWidth(360)
        self.setWindowFlags(
            self.windowFlags() ^ QtCore.Qt.WindowContextHelpButtonHint
        )

        # -------------------------
        # SESSION CACHE (runtime only)
        # -------------------------
        self.asset_cache = scan_kitbash_assets()

        # mapping: DoorA -> DoorA_grp
        self.asset_map = {
            a.replace("_grp", ""): a
            for a in self.asset_cache
        }

        self.build_ui()
        self.create_connections()

    # -----------------------------
    # UI BUILD
    # -----------------------------
    def build_ui(self):

        self.setStyleSheet("""
            QPushButton {
                background-color: rgb(80,80,80);
                color: white;
                border-radius: 4px;
                padding: 6px;
            }

            QPushButton:hover {
                background-color: rgb(100,100,100);
            }

            QComboBox {
                padding: 4px;
            }

            QLabel {
                color: white;
            }

            QWidget {
                background-color: rgb(40,40,40);
            }
        """)

        main_layout = QtWidgets.QVBoxLayout(self)

        # -------------------------
        # SECTION: KITBASH
        # -------------------------
        kit_group = QtWidgets.QGroupBox("Kitbash Asset")
        kit_layout = QtWidgets.QVBoxLayout()

        self.asset_combo = QtWidgets.QComboBox()
        self.asset_combo.setEditable(True)
        self.asset_combo.addItems(self.asset_map.keys())

        kit_layout.addWidget(self.asset_combo)

        kit_group.setLayout(kit_layout)
        main_layout.addWidget(kit_group)

        # -------------------------
        # SECTION: ACTIONS
        # -------------------------
        action_group = QtWidgets.QGroupBox("Actions")
        action_layout = QtWidgets.QVBoxLayout()

        self.export_btn = QtWidgets.QPushButton("Export Asset")

        action_layout.addWidget(self.export_btn)

        action_group.setLayout(action_layout)
        main_layout.addWidget(action_group)

        # -------------------------
        # STATUS
        # -------------------------
        self.status_label = QtWidgets.QLabel("Ready")
        main_layout.addWidget(self.status_label)

    # -----------------------------
    # CONNECTIONS
    # -----------------------------
    def create_connections(self):

        self.export_btn.clicked.connect(self.export_asset)

        self.asset_combo.lineEdit().editingFinished.connect(
            self.on_asset_entered
        )

    # -----------------------------
    # SESSION CACHE LOGIC
    # -----------------------------
    def on_asset_entered(self):

        display_name = self.asset_combo.currentText().strip()

        if not display_name:
            return

        # convert back to scene name
        scene_name = display_name + "_grp"

        # only add if it exists in scene OR is new session entry
        if display_name not in self.asset_map:

            self.asset_map[display_name] = scene_name

            self.asset_combo.clear()
            self.asset_combo.addItems(sorted(self.asset_map.keys()))

            self.status_label.setText(f"Added: {display_name}")

        else:
            self.status_label.setText(f"Selected: {display_name}")

    # -----------------------------
    # EXPORT (DUMMY)
    # -----------------------------
    def export_asset(self):

        asset = self.asset_combo.currentText().strip()

        if not asset:
            self.status_label.setText("No asset selected")
            return

        #print(f"[EXPORT] {asset}")
        export_verified_asset(asset)
        self.status_label.setText(f"Exporting: {asset}")


# -----------------------------
# LAUNCH
# -----------------------------
def show_ui():

    global kitbash_ui

    try:
        kitbash_ui.close()
    except:
        pass

    kitbash_ui = KitbashAssetTool()
    kitbash_ui.show()


show_ui()