import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401  (registers the 3D projection)

from PyQt5.QtCore import pyqtSignal, QObject

from simulation import station


class TrilatPlot3D(QObject):
    anchors_changed = pyqtSignal()
    tags_changed = pyqtSignal()
    measurements_changed = pyqtSignal()

    STATION_DOT_SIZE = 100
    STATION_COLOR = 'blue'
    SPHERE_RESOLUTION = (8j, 6j)

    def __init__(self, window, scenario):
        super().__init__()
        self.window = window
        self.scenario = scenario
        self.display_config = self.window.display_config

        self.fig = plt.figure(figsize=(6, 4))
        self.ax = self.fig.add_subplot(111, projection='3d')

        self.anchor_scatter = None
        self.tag_estimate_scatter = None
        self.tag_truth_plot = None

        self.sphere_artists = []
        self.anchor_pair_lines = []
        self.anchor_pair_texts = []
        self.tag_anchor_lines = []
        self.tag_anchor_texts = []
        self.tag_name_texts = []
        self.anchor_name_texts = []
        self.dop_text = None

        self.sandbox_tag = next((tag for tag in self.scenario.get_tag_list() if tag.name == "SANDBOX_TAG"), None)

        self.init_artists()

    def update_anchors(self):
        anchor_positions = self.scenario.anchor_positions()
        if len(anchor_positions) > 0:
            self.anchor_scatter._offsets3d = (anchor_positions[:, 0], anchor_positions[:, 1], anchor_positions[:, 2])
        else:
            self.anchor_scatter._offsets3d = ([], [], [])

    def _sphere_wireframe(self, center, radius, color):
        u, v = np.mgrid[0:2 * np.pi:self.SPHERE_RESOLUTION[0], 0:np.pi:self.SPHERE_RESOLUTION[1]]
        xs = center[0] + radius * np.cos(u) * np.sin(v)
        ys = center[1] + radius * np.sin(u) * np.sin(v)
        zs = center[2] + radius * np.cos(v)
        return self.ax.plot_wireframe(xs, ys, zs, color=color, alpha=0.15, linewidth=0.5)

    def _clear_spheres(self):
        for artist in self.sphere_artists:
            try:
                artist.remove()
            except Exception:
                pass
        self.sphere_artists = []

    def _reference_tag(self):
        if self.sandbox_tag is not None:
            return self.sandbox_tag
        tags = self.scenario.get_tag_list()
        return tags[0] if tags else None

    def update_data(self, anchors=False, tags=False, measurements=False):
        anchor_positions = self.scenario.anchor_positions()
        tag_positions = self.scenario.tag_positions()

        reference_tag = self._reference_tag()

        distances_truth = np.array([])
        if reference_tag is not None:
            distances_truth = reference_tag.distances()
        elif self.scenario.tag_truth is not None:
            distances_truth = self.scenario.tag_truth.distances(self.scenario)

        # Tag estimate scatter
        if len(tag_positions) > 0:
            self.tag_estimate_scatter._offsets3d = (tag_positions[:, 0], tag_positions[:, 1], tag_positions[:, 2])
        else:
            self.tag_estimate_scatter._offsets3d = ([], [], [])

        # Anchor scatter
        if len(anchor_positions) > 0:
            self.anchor_scatter._offsets3d = (anchor_positions[:, 0], anchor_positions[:, 1], anchor_positions[:, 2])
        else:
            self.anchor_scatter._offsets3d = ([], [], [])

        # Tag truth scatter
        if self.scenario.tag_truth is not None:
            tt = self.scenario.tag_truth.position()
            self.tag_truth_plot._offsets3d = ([tt[0]], [tt[1]], [tt[2]])
            self.tag_truth_plot.set_visible(True)
        else:
            self.tag_truth_plot.set_visible(False)

        # Anchor uncertainty spheres
        self._clear_spheres()
        if self.display_config.showAnchorSpheres and len(anchor_positions) > 0 and len(distances_truth) == len(anchor_positions):
            for i, pos in enumerate(anchor_positions):
                outer_r = distances_truth[i] + self.scenario.sigma
                inner_r = max(0.0, distances_truth[i] - self.scenario.sigma)
                if outer_r > 0:
                    self.sphere_artists.append(self._sphere_wireframe(pos, outer_r, self.STATION_COLOR))
                if inner_r > 0:
                    self.sphere_artists.append(self._sphere_wireframe(pos, inner_r, self.STATION_COLOR))

        # Anchor-anchor pair lines and labels
        num_pairs = max(0, len(anchor_positions) * (len(anchor_positions) - 1) // 2)
        while len(self.anchor_pair_lines) < num_pairs:
            line = self.ax.plot([], [], [], 'b--', alpha=0.5)[0]
            self.anchor_pair_lines.append(line)
            text = self.ax.text(0, 0, 0, '', ha='center', va='center')
            text.set_visible(False)
            self.anchor_pair_texts.append(text)

        pair_idx = 0
        for i in range(len(anchor_positions)):
            for j in range(i + 1, len(anchor_positions)):
                p1, p2 = anchor_positions[i], anchor_positions[j]
                line = self.anchor_pair_lines[pair_idx]
                if self.display_config.showBetweenAnchorsLines:
                    line.set_data_3d([p1[0], p2[0]], [p1[1], p2[1]], [p1[2], p2[2]])
                    line.set_visible(True)
                else:
                    line.set_visible(False)

                text = self.anchor_pair_texts[pair_idx]
                if self.display_config.showBetweenAnchorsLabels:
                    mid = (p1 + p2) / 2
                    distance = np.linalg.norm(p1 - p2)
                    text.set_text(f"{distance:.2f}")
                    text.set_position_3d((mid[0], mid[1], mid[2]))
                    text.set_visible(True)
                else:
                    text.set_visible(False)

                pair_idx += 1

        for idx in range(pair_idx, len(self.anchor_pair_lines)):
            self.anchor_pair_lines[idx].set_visible(False)
            self.anchor_pair_texts[idx].set_visible(False)

        # Tag-anchor lines and labels
        needed_tag_anchor = len(tag_positions) * len(anchor_positions)
        while len(self.tag_anchor_lines) < needed_tag_anchor:
            line = self.ax.plot([], [], [], 'r--', alpha=0.5)[0]
            self.tag_anchor_lines.append(line)
            text = self.ax.text(0, 0, 0, '', ha='center', va='center')
            text.set_visible(False)
            self.tag_anchor_texts.append(text)

        ta_idx = 0
        for tag_position in tag_positions:
            for anchor_position in anchor_positions:
                line = self.tag_anchor_lines[ta_idx]
                if self.display_config.showTagAnchorLines:
                    line.set_data_3d(
                        [anchor_position[0], tag_position[0]],
                        [anchor_position[1], tag_position[1]],
                        [anchor_position[2], tag_position[2]],
                    )
                    line.set_visible(True)
                else:
                    line.set_visible(False)

                text = self.tag_anchor_texts[ta_idx]
                if self.display_config.showTagAnchorLabels:
                    mid = (anchor_position + tag_position) / 2
                    distance = np.linalg.norm(anchor_position - tag_position)
                    text.set_text(f"{distance:.2f}")
                    text.set_position_3d((mid[0], mid[1], mid[2]))
                    text.set_visible(True)
                else:
                    text.set_visible(False)

                ta_idx += 1

        for idx in range(ta_idx, len(self.tag_anchor_lines)):
            self.tag_anchor_lines[idx].set_visible(False)
            self.tag_anchor_texts[idx].set_visible(False)

        # Tag name labels
        while len(self.tag_name_texts) < len(tag_positions):
            text = self.ax.text(0, 0, 0, '', color='red', ha='center', va='bottom')
            text.set_visible(False)
            self.tag_name_texts.append(text)

        for i, tag_position in enumerate(tag_positions):
            text = self.tag_name_texts[i]
            if self.display_config.showTagLabels:
                text.set_text(self.scenario.get_tag_list()[i].name)
                text.set_position_3d((tag_position[0], tag_position[1], tag_position[2]))
                text.set_visible(True)
            else:
                text.set_visible(False)

        for idx in range(len(tag_positions), len(self.tag_name_texts)):
            self.tag_name_texts[idx].set_visible(False)

        # Anchor name labels
        while len(self.anchor_name_texts) < len(anchor_positions):
            text = self.ax.text(0, 0, 0, '', ha='center', va='center')
            text.set_visible(False)
            self.anchor_name_texts.append(text)

        for i, anchor_position in enumerate(anchor_positions):
            text = self.anchor_name_texts[i]
            if self.display_config.showAnchorLabels:
                text.set_text(self.scenario.get_anchor_list()[i].name)
                text.set_position_3d((anchor_position[0], anchor_position[1], anchor_position[2]))
                text.set_visible(True)
            else:
                text.set_visible(False)

        for idx in range(len(anchor_positions), len(self.anchor_name_texts)):
            self.anchor_name_texts[idx].set_visible(False)

        # PDOP/HDOP/VDOP info text
        if self.display_config.showGDOP and reference_tag is not None:
            pdop, hdop, vdop = reference_tag.dop_components()
            lines = [f"PDOP: {pdop:.2f}", f"HDOP: {hdop:.2f}"]
            if vdop is not None:
                lines.append(f"VDOP: {vdop:.2f}")
            self.dop_text.set_text("\n".join(lines))
            self.dop_text.set_visible(True)
        else:
            self.dop_text.set_visible(False)

        self._adjust_axes_bounds()

    def _adjust_axes_bounds(self):
        """Keep the 3D axes cubic and centered on the current scenario data."""
        position_arrays = []

        anchor_positions = self.scenario.anchor_positions()
        if len(anchor_positions) > 0:
            position_arrays.append(anchor_positions)

        tag_positions = self.scenario.tag_positions()
        if len(tag_positions) > 0:
            position_arrays.append(np.array(tag_positions))

        if self.scenario.tag_truth is not None:
            position_arrays.append(np.array([self.scenario.tag_truth.position()]))

        if not position_arrays:
            return

        all_positions = np.vstack(position_arrays)
        mins = all_positions.min(axis=0)
        maxs = all_positions.max(axis=0)
        center = (mins + maxs) / 2
        span = max((maxs - mins).max(), 1.0)
        half = span / 2 * 1.2

        self.ax.set_xlim(center[0] - half, center[0] + half)
        self.ax.set_ylim(center[1] - half, center[1] + half)
        self.ax.set_zlim(center[2] - half, center[2] + half)
        try:
            self.ax.set_box_aspect((1, 1, 1))
        except Exception:
            pass

    def redraw(self):
        """Trigger a canvas redraw."""
        try:
            self.fig.canvas.draw_idle()
        except Exception:
            pass

    def init_artists(self):
        self.ax.clear()

        self.anchor_scatter = self.ax.scatter([], [], [], c=self.STATION_COLOR, s=self.STATION_DOT_SIZE, picker=True)
        self.tag_estimate_scatter = self.ax.scatter([], [], [], c='red', marker='x')

        if self.scenario.tag_truth is not None:
            pos = self.scenario.tag_truth.position()
            self.tag_truth_plot = self.ax.scatter([pos[0]], [pos[1]], [pos[2]], c='green', s=self.STATION_DOT_SIZE, picker=True)
        else:
            self.tag_truth_plot = self.ax.scatter([], [], [], c='green', s=self.STATION_DOT_SIZE, picker=True)

        self.sphere_artists = []
        self.anchor_pair_lines = []
        self.anchor_pair_texts = []
        self.tag_anchor_lines = []
        self.tag_anchor_texts = []
        self.tag_name_texts = []
        self.anchor_name_texts = []

        self.dop_text = self.ax.text2D(
            0.02, 0.98, '', transform=self.ax.transAxes,
            ha='left', va='top', fontsize=9, family='monospace',
        )

        self.ax.set_xlabel('X')
        self.ax.set_ylabel('Y')
        self.ax.set_zlabel('Z')
        self.ax.set_title(self.scenario.name)

        self._adjust_axes_bounds()

        try:
            self.fig.canvas.draw_idle()
        except Exception:
            pass

    def add_anchor(self, x, y, z):
        anchor_name = f"Anchor {len(self.scenario.get_anchor_list()) + 1}"
        self.scenario.stations.append(station.Anchor([x, y, z], anchor_name))
        self.anchors_changed.emit()

    def remove_anchor(self, index):
        anchor_to_remove = self.scenario.get_anchor_list()[index]
        self.scenario.remove_station(anchor_to_remove)
        self.anchors_changed.emit()
