"""
Display tab for the PDOP application.
"""

from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QCheckBox
from .base_tab import BaseTab


class DisplayTab(BaseTab):
    """Tab for display configuration options."""

    def __init__(self, main_window):
        super().__init__(main_window)
        self.display_tree = None
        # Store references to checkboxes for later access
        self.anchor_spheres_checkbox = None
        self.anchor_labels_checkbox = None
        self.between_anchors_lines_checkbox = None
        self.between_anchors_labels_checkbox = None
        self.tag_anchor_lines_checkbox = None
        self.tag_anchor_labels_checkbox = None
        self.tag_labels_checkbox = None
        self.gdop_checkbox = None

    @property
    def tab_name(self):
        return "Display"

    def create_widget(self):
        """Create and return the display tab widget."""
        self.display_tree = QTreeWidget()
        self.display_tree.setHeaderHidden(True)

        # Anchor section
        anchor_node = QTreeWidgetItem(self.display_tree, ["Anchor"])
        self.anchor_spheres_checkbox = QCheckBox("Show Anchor Spheres")
        self.anchor_spheres_checkbox.setChecked(self.display_config.showAnchorSpheres)
        self.anchor_spheres_checkbox.stateChanged.connect(self.update_display_config)
        anchor_spheres_item = QTreeWidgetItem(anchor_node)
        self.display_tree.setItemWidget(anchor_spheres_item, 0, self.anchor_spheres_checkbox)
        anchor_node.setExpanded(True)

        self.anchor_labels_checkbox = QCheckBox("Show Anchor Labels")
        self.anchor_labels_checkbox.setChecked(self.display_config.showAnchorLabels)
        self.anchor_labels_checkbox.stateChanged.connect(self.update_display_config)
        anchor_labels_item = QTreeWidgetItem(anchor_node)
        self.display_tree.setItemWidget(anchor_labels_item, 0, self.anchor_labels_checkbox)

        # Between Anchors section
        between_anchors_node = QTreeWidgetItem(self.display_tree, ["Between Anchors"])
        self.between_anchors_lines_checkbox = QCheckBox("Show Lines Between Anchors")
        self.between_anchors_lines_checkbox.setChecked(self.display_config.showBetweenAnchorsLines)
        self.between_anchors_lines_checkbox.stateChanged.connect(self.update_display_config)
        between_anchors_lines_item = QTreeWidgetItem(between_anchors_node)
        self.display_tree.setItemWidget(between_anchors_lines_item, 0, self.between_anchors_lines_checkbox)
        between_anchors_node.setExpanded(True)

        self.between_anchors_labels_checkbox = QCheckBox("Show Labels Between Anchors")
        self.between_anchors_labels_checkbox.setChecked(self.display_config.showBetweenAnchorsLabels)
        self.between_anchors_labels_checkbox.stateChanged.connect(self.update_display_config)
        between_anchors_labels_item = QTreeWidgetItem(between_anchors_node)
        self.display_tree.setItemWidget(between_anchors_labels_item, 0, self.between_anchors_labels_checkbox)

        # Tag and Anchors section
        tag_anchor_node = QTreeWidgetItem(self.display_tree, ["Tag and Anchors"])
        self.tag_anchor_lines_checkbox = QCheckBox("Show Lines Between Tag and Anchors")
        self.tag_anchor_lines_checkbox.setChecked(self.display_config.showTagAnchorLines)
        self.tag_anchor_lines_checkbox.stateChanged.connect(self.update_display_config)
        tag_anchor_lines_item = QTreeWidgetItem(tag_anchor_node)
        self.display_tree.setItemWidget(tag_anchor_lines_item, 0, self.tag_anchor_lines_checkbox)
        tag_anchor_node.setExpanded(True)

        self.tag_anchor_labels_checkbox = QCheckBox("Show Labels Between Tag and Anchors")
        self.tag_anchor_labels_checkbox.setChecked(self.display_config.showTagAnchorLabels)
        self.tag_anchor_labels_checkbox.stateChanged.connect(self.update_display_config)
        tag_anchor_labels_item = QTreeWidgetItem(tag_anchor_node)
        self.display_tree.setItemWidget(tag_anchor_labels_item, 0, self.tag_anchor_labels_checkbox)

        self.tag_labels_checkbox = QCheckBox("Show Tag Labels")
        self.tag_labels_checkbox.setChecked(self.display_config.showTagLabels)
        self.tag_labels_checkbox.stateChanged.connect(self.update_display_config)
        tag_labels_item = QTreeWidgetItem(tag_anchor_node)
        self.display_tree.setItemWidget(tag_labels_item, 0, self.tag_labels_checkbox)

        # Info section
        info_node = QTreeWidgetItem(self.display_tree, ["Info"])
        self.gdop_checkbox = QCheckBox("Show PDOP / HDOP / VDOP")
        self.gdop_checkbox.setChecked(self.display_config.showGDOP)
        self.gdop_checkbox.stateChanged.connect(self.update_display_config)
        gdop_item = QTreeWidgetItem(info_node)
        self.display_tree.setItemWidget(gdop_item, 0, self.gdop_checkbox)
        info_node.setExpanded(True)

        return self.display_tree

    def update_display_config(self):
        """Update display configuration based on checkbox states."""
        self.display_config.showAnchorSpheres = self.anchor_spheres_checkbox.isChecked()
        self.display_config.showAnchorLabels = self.anchor_labels_checkbox.isChecked()
        self.display_config.showBetweenAnchorsLines = self.between_anchors_lines_checkbox.isChecked()
        self.display_config.showBetweenAnchorsLabels = self.between_anchors_labels_checkbox.isChecked()
        self.display_config.showTagAnchorLines = self.tag_anchor_lines_checkbox.isChecked()
        self.display_config.showTagAnchorLabels = self.tag_anchor_labels_checkbox.isChecked()
        self.display_config.showTagLabels = self.tag_labels_checkbox.isChecked()
        self.display_config.showGDOP = self.gdop_checkbox.isChecked()

        self.main_window.update_all()
