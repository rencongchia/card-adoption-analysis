"""Wise brand-aligned matplotlib theme.

Matches the visuals with reference to Wise's HY/FY corporate decks: forest green + bright
lime green palette on white, with all-greens semantics (no red / blue / orange).
Positive values render in bright green; negative values render in dark forest green.
"""
from __future__ import annotations

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

BRIGHT_GREEN = "#9FE870"
DARK_GREEN   = "#163300"
MID_GREEN    = "#4FAD3A"
SOFT_GREEN   = "#C7EEA8"
LIGHT_BG     = "#F2F0EC"
CARD_GREY    = "#ECEEEC"
WARM_GREY    = "#7A8F76"
FAINT_GREY   = "#B5BEC9"

PALETTE = [BRIGHT_GREEN, DARK_GREEN, MID_GREEN, SOFT_GREEN, WARM_GREY]


def diverging_cmap():
    """Diverging colormap: dark forest (negative) → cream (zero) → bright green (positive)."""
    return LinearSegmentedColormap.from_list(
        "wise_div", [DARK_GREEN, "#3A5A2E", "#7C9A6E", LIGHT_BG, SOFT_GREEN, BRIGHT_GREEN]
    )


def sequential_cmap():
    """Sequential green ramp: cream → bright → dark forest. For ordered values."""
    return LinearSegmentedColormap.from_list(
        "wise_seq", [LIGHT_BG, SOFT_GREEN, BRIGHT_GREEN, MID_GREEN, DARK_GREEN]
    )


def apply():
    """Apply Wise rcParams globally. Call once at notebook/script top."""
    mpl.rcParams.update({
        "figure.facecolor":  "white",
        "axes.facecolor":    "white",
        "savefig.facecolor": "white",
        "savefig.dpi":       300,
        "savefig.bbox":      "tight",

        "axes.edgecolor":    DARK_GREEN,
        "axes.linewidth":    1.0,
        "axes.labelcolor":   DARK_GREEN,
        "axes.labelweight":  "bold",
        "axes.titlecolor":   DARK_GREEN,
        "axes.titleweight":  "bold",
        "axes.titlesize":    14,
        "axes.titlelocation": "left",
        "axes.titlepad":     14,
        "axes.labelsize":    11,
        "axes.spines.top":   False,
        "axes.spines.right": False,
        "axes.spines.left":  False,
        "axes.grid":         False,

        "xtick.color":       DARK_GREEN,
        "ytick.color":       DARK_GREEN,
        "xtick.labelsize":   10,
        "ytick.labelsize":   10,
        "xtick.major.size":  0,
        "ytick.major.size":  0,
        "xtick.major.pad":   6,
        "ytick.major.pad":   6,

        "legend.frameon":    False,
        "legend.fontsize":   10,
        "legend.labelcolor": DARK_GREEN,

        "font.family":       ["Helvetica Neue", "Arial", "DejaVu Sans"],
        "font.weight":       "normal",
        "text.color":        DARK_GREEN,

        "lines.linewidth":   2.4,
        "lines.markersize":  7,

        "axes.prop_cycle":   mpl.cycler(color=PALETTE),
    })


def style_axes(ax, *, baseline=True, ygrid=False):
    """Per-axes touch-ups after plotting: baseline at y=0, optional faint y-grid."""
    if baseline:
        ax.axhline(0, color=DARK_GREEN, linewidth=0.8, zorder=1)
    if ygrid:
        ax.yaxis.grid(True, color=DARK_GREEN, alpha=0.08, linewidth=0.6, zorder=0)
        ax.set_axisbelow(True)
    ax.tick_params(axis="x", which="both", length=0)
    ax.tick_params(axis="y", which="both", length=0)


def value_color(v: float) -> str:
    """Bright green for positive, dark green for negative — Wise two-tone semantic."""
    return BRIGHT_GREEN if v > 0 else DARK_GREEN


def label_color_on(value: float, vmax: float) -> str:
    """Pick white-on-dark or dark-on-light for in-cell labels (e.g. heatmaps)."""
    return "white" if abs(value) > 0.55 * vmax and value < 0 else DARK_GREEN
