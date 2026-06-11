from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QTreeWidget,
    QTreeWidgetItem,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QFormLayout,
    QLabel,
    QLineEdit,
    QDoubleSpinBox,
    QPushButton,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
)

from .base_tab import BaseTab
from simulation.station import Anchor
from data import importer as importer_module


class StationDialog(QDialog):
    """Dialog to add or edit a station's name and X/Y/Z position."""

    POSITION_RANGE = 1000.0

    def __init__(self, parent=None, title="Station", name="", position=None, position_editable=True):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)

        layout = QVBoxLayout()
        form = QFormLayout()

        self.name_input = QLineEdit(name)
        form.addRow("Name:", self.name_input)

        self.position_inputs = []
        for axis, value in zip(("X:", "Y:", "Z:"), position or [0.0, 0.0, 0.0]):
            spin = QDoubleSpinBox()
            spin.setRange(-self.POSITION_RANGE, self.POSITION_RANGE)
            spin.setDecimals(3)
            spin.setSingleStep(0.1)
            spin.setValue(float(value))
            spin.setEnabled(position_editable)
            form.addRow(axis, spin)
            self.position_inputs.append(spin)

        layout.addLayout(form)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)

    def get_name(self):
        return self.name_input.text().strip()

    def get_position(self):
        return [spin.value() for spin in self.position_inputs]


class TreeTab(BaseTab):

    def __init__(self, main_window):
        super().__init__(main_window)
        self.tree = None

    @property
    def tab_name(self):
        return "Tree"

    def create_widget(self):
        container = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        container.setLayout(layout)

        toolbar = QWidget()
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        add_anchor_button = QPushButton("Add Anchor")
        add_anchor_button.setToolTip("Add a new anchor to the active scenario")
        add_anchor_button.clicked.connect(self._add_anchor_dialog)
        toolbar_layout.addWidget(add_anchor_button)
        toolbar_layout.addStretch()
        toolbar.setLayout(toolbar_layout)
        layout.addWidget(toolbar)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        layout.addWidget(self.tree)

        self.update_tree()
        return container

    def update_tree(self):
        if not self.tree:
            return

        self.tree.clear()

        app = self.main_window.app
        scenarios = app.scenarios

        active = self.main_window.trilat_plot.scenario

        scenario_names, _error_message = importer_module.get_available_scenarios()
        for scen_name in scenario_names:
            scen_node = QTreeWidgetItem(self.tree)

            row_widget = QWidget()
            row_layout = QHBoxLayout()
            row_layout.setContentsMargins(0, 0, 0, 0)

            checkbox = QCheckBox()
            is_imported = scen_name in [s.name for s in scenarios]
            checkbox.setChecked(is_imported)
            checkbox.stateChanged.connect(lambda state, name=scen_name: self._toggle_scenario(name, state))

            name_label = QLabel(scen_name)

            row_layout.addWidget(checkbox)
            row_layout.addWidget(name_label)
            row_layout.addStretch()

            if is_imported:
                scen = next(s for s in scenarios if s.name == scen_name)

                if active is not scen:
                    activate_button = QPushButton("⏿")
                    activate_button.setToolTip("Activate this scenario in the main plot")
                    activate_button.clicked.connect(lambda checked, s=scen: self._activate_scenario(s))
                    row_layout.addWidget(activate_button)

                if active is scen:
                    self.tree.setCurrentItem(scen_node)
                    checkbox.setEnabled(False)  # Prevent unchecking the active scenario

                stations_node = QTreeWidgetItem(scen_node, ["Stations"])
                for st in scen.stations:
                    self._add_station_row(stations_node, st)

                if scen.tag_truth is not None:
                    self._add_station_row(stations_node, scen.tag_truth)

                measurements_node = QTreeWidgetItem(scen_node, ["Measurements"])
                for pair, distance in scen.measurements.relation.items():
                    station1, station2 = pair
                    label = f"{station1.name} ↔ {station2.name}: {distance:.2f}"
                    QTreeWidgetItem(measurements_node, [label])

            row_widget.setLayout(row_layout)
            self.tree.setItemWidget(scen_node, 0, row_widget)

    def _add_station_row(self, parent_node, st):
        station_node = QTreeWidgetItem(parent_node)

        station_widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        pos = st.position()
        name_label = QLabel(f"{st.name} ({pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f})")

        edit_button = QPushButton("✎")
        edit_button.setToolTip("Edit station (name and coordinates)")
        edit_button.clicked.connect(lambda checked, s=st: self._edit_station_dialog(s))

        layout.addWidget(name_label)
        layout.addStretch()
        layout.addWidget(edit_button)

        if st is not getattr(self.scenario, 'tag_truth', None):
            delete_button = QPushButton("␡")
            delete_button.setToolTip("Delete station")
            delete_button.clicked.connect(lambda checked, s=st: self._delete_station(s))
            layout.addWidget(delete_button)

        station_widget.setLayout(layout)
        self.tree.setItemWidget(station_node, 0, station_widget)

    def update(self):
        self.update_tree()

    def _add_anchor_dialog(self):
        if self.scenario is None:
            return

        default_name = f"Anchor {len(self.scenario.get_anchor_list()) + 1}"
        dialog = StationDialog(
            self.main_window, title="Add Anchor",
            name=default_name, position=[0.0, 0.0, 0.0], position_editable=True,
        )
        if dialog.exec_() != QDialog.Accepted:
            return

        name = dialog.get_name() or default_name
        x, y, z = dialog.get_position()

        plot = self.main_window.trilat_plot
        plot.add_anchor(x, y, z)
        plot.scenario.get_anchor_list()[-1].name = name

        self.main_window.update_all()

    def _edit_station_dialog(self, st):
        is_anchor = isinstance(st, Anchor)
        dialog = StationDialog(
            self.main_window, title="Edit Station",
            name=st.name, position=st.position(), position_editable=is_anchor,
        )
        if dialog.exec_() != QDialog.Accepted:
            return

        new_name = dialog.get_name()
        if new_name and new_name != st.name:
            st.name = new_name

        if is_anchor:
            st.update_position(dialog.get_position())

        self.main_window.update_all()

    def _delete_station(self, station):
        self.scenario.remove_station(station)
        self.main_window.update_all()

    def _activate_scenario(self, scen):
        plot = self.main_window.trilat_plot
        plot.scenario = scen
        plot.sandbox_tag = next((tag for tag in scen.get_tag_list() if tag.name == "SANDBOX_TAG"), None)
        plot.init_artists()
        self.main_window.update_all()

    def _remove_scenario(self, scen):
        app = self.main_window.app
        if scen in app.scenarios:
            app.scenarios.remove(scen)

        plot = self.main_window.trilat_plot
        if plot.scenario is scen:
            plot.scenario = app.scenarios[0] if app.scenarios else None
            if plot.scenario is not None:
                plot.sandbox_tag = next((tag for tag in plot.scenario.get_tag_list() if tag.name == "SANDBOX_TAG"), None)
                plot.init_artists()

        self.main_window.update_all()

    def _toggle_scenario(self, scen_name, state):
        app = self.main_window.app
        if state == Qt.Checked:
            if scen_name not in [s.name for s in app.scenarios]:
                self._import_scenario_from_workspace(scen_name)
        else:
            scen = next((s for s in app.scenarios if s.name == scen_name), None)
            if scen:
                self._remove_scenario(scen)

    def _import_scenario_from_workspace(self, scen_name: str):
        success, message, imported_scenario = importer_module.import_scenario(scen_name, workspace_dir="workspace")

        if success and imported_scenario is not None:
            app = self.main_window.app
            app.scenarios.append(imported_scenario)

            plot = self.main_window.trilat_plot
            plot.scenario = imported_scenario
            plot.sandbox_tag = next((tag for tag in imported_scenario.get_tag_list() if tag.name == "SANDBOX_TAG"), None)
            plot.init_artists()

            self.main_window.update_all()
            try:
                self.main_window.statusBar().showMessage(f"Imported scenario '{scen_name}'", 5000)
            except Exception:
                pass
        else:
            try:
                self.main_window.statusBar().showMessage(f"Import Error: {message}", 0)
            except Exception:
                pass
