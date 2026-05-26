"""Interactive 3-D viewer + thermal-map plots for fuel-pin assembly results.

Requires ``plotly`` and ``matplotlib``. Generates standalone HTML
(no server) plus static PNGs for publication-style figures.
"""

from __future__ import annotations

import math
import pathlib
import re
from dataclasses import dataclass

try:
    import plotly.graph_objects as go
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "netflow.viz_interactive requires plotly, matplotlib, numpy. "
        "Install with: pip install 'netflow[viz]' plotly"
    ) from exc


# Fuel-pin geometry (matches netflow.bench.fuel_array)
R_PELLET = 4.10e-3
R_CLAD_INNER = 4.10e-3 + 0.085e-3
R_CLAD_OUTER = 4.75e-3
COOLANT_R_DISPLAY = R_CLAD_OUTER * 1.4   # where to render coolant in 3-D space


# Match: p{ix}_{iy}_z{k}_{station} or p{ix}_{iy}_cool_z{k}
_PIN_NODE_RE = re.compile(r"^p(\d+)_(\d+)_z(\d+)_(\w+)$")
_COOL_NODE_RE = re.compile(r"^p(\d+)_(\d+)_cool_z(\d+)$")


@dataclass
class AssemblyData:
    """Tidy representation of one solved fuel-array problem."""
    n_x: int
    n_y: int
    n_axial: int
    slice_L: float
    # Indexed by [ix, iy, k] → T (K). Shape (n_x, n_y, n_axial) per station.
    T_centerline: np.ndarray
    T_pellet_surface: np.ndarray
    T_clad_inner: np.ndarray
    T_clad_outer: np.ndarray
    T_coolant: np.ndarray
    # Per-pin scalar fields for top-down maps
    q_lin_per_pin: np.ndarray   # shape (n_x, n_y); 0 if unknown
    peak_T_per_pin: np.ndarray  # shape (n_x, n_y) — max centerline over axial

    @property
    def stations(self) -> dict[str, np.ndarray]:
        return {
            "centerline": self.T_centerline,
            "pellet_surface": self.T_pellet_surface,
            "clad_inner": self.T_clad_inner,
            "clad_outer": self.T_clad_outer,
            "coolant": self.T_coolant,
        }


def extract_assembly_data(
    network,
    result,
    *,
    n_x: int,
    n_y: int,
    n_axial: int,
    slice_L: float,
    q_lin_fn=None,
) -> AssemblyData:
    """Parse a solved fuel-array Result into a tidy 3-D tensor per station."""
    stations = ("centerline", "pellet_surface", "clad_inner", "clad_outer")
    grids: dict[str, np.ndarray] = {
        s: np.full((n_x, n_y, n_axial), np.nan) for s in stations
    }
    coolant = np.full((n_x, n_y, n_axial), np.nan)

    for nid, T in result.states.items():
        m = _PIN_NODE_RE.match(nid)
        if m:
            ix, iy, k, station = int(m[1]), int(m[2]), int(m[3]), m[4]
            if station in grids:
                grids[station][ix, iy, k] = T
            continue
        m = _COOL_NODE_RE.match(nid)
        if m:
            ix, iy, k = int(m[1]), int(m[2]), int(m[3])
            coolant[ix, iy, k] = T

    q_lin_grid = np.zeros((n_x, n_y))
    if q_lin_fn is not None:
        for ix in range(n_x):
            for iy in range(n_y):
                q_lin_grid[ix, iy] = float(q_lin_fn(ix, iy))

    peak_T = np.nanmax(grids["centerline"], axis=2)

    return AssemblyData(
        n_x=n_x, n_y=n_y, n_axial=n_axial, slice_L=slice_L,
        T_centerline=grids["centerline"],
        T_pellet_surface=grids["pellet_surface"],
        T_clad_inner=grids["clad_inner"],
        T_clad_outer=grids["clad_outer"],
        T_coolant=coolant,
        q_lin_per_pin=q_lin_grid,
        peak_T_per_pin=peak_T,
    )


# ---------------------------------------------------------------------------
# Static plots
# ---------------------------------------------------------------------------

def plot_assembly_heatmap(
    data: AssemblyData,
    out_path: pathlib.Path,
    *,
    title: str | None = None,
) -> None:
    """Top-down heatmap of peak centerline T across the assembly.

    Side panel shows the linear-power distribution that produced it.
    """
    has_q = data.q_lin_per_pin.max() > 0
    n_panels = 2 if has_q else 1
    fig, axes = plt.subplots(
        1, n_panels, figsize=(11 if has_q else 6, 5.5),
        squeeze=False,
    )

    ax = axes[0, 0]
    T_C = data.peak_T_per_pin - 273.15
    im = ax.imshow(
        T_C.T, origin="lower", cmap="hot",
        extent=[-0.5, data.n_x - 0.5, -0.5, data.n_y - 0.5],
    )
    ax.set_title(f"Peak centerline T  (max = {np.nanmax(T_C):.0f} °C)")
    ax.set_xlabel("pin index ix")
    ax.set_ylabel("pin index iy")
    cb = fig.colorbar(im, ax=ax, fraction=0.046)
    cb.set_label("T (°C)")

    if has_q:
        ax2 = axes[0, 1]
        im2 = ax2.imshow(
            data.q_lin_per_pin.T / 1000.0, origin="lower", cmap="plasma",
            extent=[-0.5, data.n_x - 0.5, -0.5, data.n_y - 0.5],
        )
        ax2.set_title(
            f"Linear power q_lin "
            f"(peak/avg = {data.q_lin_per_pin.max()/data.q_lin_per_pin.mean():.2f})"
        )
        ax2.set_xlabel("pin index ix")
        ax2.set_ylabel("pin index iy")
        cb2 = fig.colorbar(im2, ax=ax2, fraction=0.046)
        cb2.set_label("q_lin (kW/m)")

    if title:
        fig.suptitle(title, fontsize=11, y=1.02)
    fig.tight_layout()
    fig.savefig(out_path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {out_path}")


def plot_hottest_pin_axial(
    data: AssemblyData,
    out_path: pathlib.Path,
) -> None:
    """Axial T profile of the hottest pin — centerline, pellet surface,
    clad inner/outer, coolant."""
    flat_idx = np.nanargmax(data.peak_T_per_pin)
    ix, iy = np.unravel_index(flat_idx, data.peak_T_per_pin.shape)
    z = (np.arange(data.n_axial) + 0.5) * data.slice_L

    fig, ax = plt.subplots(figsize=(8, 5.5))
    profiles = [
        ("centerline", data.T_centerline, "#cc3333", "o"),
        ("pellet surface", data.T_pellet_surface, "#cc9933", "s"),
        ("clad inner", data.T_clad_inner, "#3366aa", "^"),
        ("clad outer", data.T_clad_outer, "#33aaaa", "v"),
        ("coolant", data.T_coolant, "#3399ff", "d"),
    ]
    for label, arr, color, marker in profiles:
        T_C = arr[ix, iy, :] - 273.15
        ax.plot(z, T_C, marker=marker, linewidth=1.8,
                color=color, label=label, markersize=4)

    q_lin_kW = data.q_lin_per_pin[ix, iy] / 1000.0
    ax.set_xlabel("axial position z (m)")
    ax.set_ylabel("temperature (°C)")
    ax.set_title(
        f"Hottest pin axial profile  ·  pin ({ix},{iy})  "
        f"·  q_lin = {q_lin_kW:.1f} kW/m"
    )
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best", fontsize=9)
    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)
    print(f"  wrote {out_path}")


# ---------------------------------------------------------------------------
# Interactive 3-D viewer (plotly)
# ---------------------------------------------------------------------------

def make_interactive_assembly_view(
    data: AssemblyData,
    out_path: pathlib.Path,
    *,
    pitch: float = 12.6e-3,
    title: str | None = None,
) -> None:
    """Standalone HTML with a 3-D scatter of all (pin × axial × station) nodes.

    Dropdown selects which radial station(s) to display. Hover reveals
    pin (ix, iy), axial slice, station name, temperature in K and °C,
    and linear power for that pin.
    """
    n_x, n_y, n_axial = data.n_x, data.n_y, data.n_axial

    stations_with_radius = [
        ("centerline",     0.0,              "Centerline (fuel)"),
        ("pellet_surface", R_PELLET,         "Pellet surface"),
        ("clad_inner",     R_CLAD_INNER,     "Clad inner"),
        ("clad_outer",     R_CLAD_OUTER,     "Clad outer"),
        ("coolant",        COOLANT_R_DISPLAY,"Coolant (subchannel)"),
    ]

    # Build one trace per station — each is a 3-D scatter over all
    # (pin × axial-slice) positions. One point per node (no rings) to
    # keep file size and renderer cost manageable at PWR-assembly scale.
    fig = go.Figure()

    T_global_min = float("inf"); T_global_max = -float("inf")
    for station, _, _ in stations_with_radius:
        arr = data.stations[station]
        if np.isfinite(arr).any():
            T_global_min = min(T_global_min, float(np.nanmin(arr)))
            T_global_max = max(T_global_max, float(np.nanmax(arr)))

    for station, r_disp, pretty in stations_with_radius:
        T_arr = data.stations[station]
        xs: list[float] = []
        ys: list[float] = []
        zs: list[float] = []
        Ts: list[float] = []
        texts: list[str] = []

        # Offset the radial stations slightly to the right of pin center so
        # they don't all stack on top of each other in 3-D. Centerline at
        # pin centre, others fan out along +x within the pin's pitch box.
        for ix in range(n_x):
            for iy in range(n_y):
                cx = ix * pitch + r_disp
                cy = iy * pitch
                q_lin = data.q_lin_per_pin[ix, iy]
                q_lin_txt = (f"<br>q_lin = {q_lin/1000:.2f} kW/m"
                             if q_lin > 0 else "")
                for k in range(n_axial):
                    T = T_arr[ix, iy, k]
                    if not np.isfinite(T):
                        continue
                    zs.append((k + 0.5) * data.slice_L)
                    xs.append(cx); ys.append(cy); Ts.append(T)
                    texts.append(
                        f"<b>{pretty}</b><br>"
                        f"pin ({ix},{iy})  slice k={k}<br>"
                        f"T = {T:.1f} K  ({T-273.15:.1f} °C)"
                        + q_lin_txt
                    )

        visible = station in ("centerline", "clad_outer")
        fig.add_trace(go.Scatter3d(
            x=xs, y=ys, z=zs,
            mode="markers",
            marker=dict(
                size=3.0 if station == "centerline" else 2.2,
                color=Ts,
                colorscale="Hot",
                cmin=T_global_min, cmax=T_global_max,
                showscale=(station == "centerline"),
                colorbar=(dict(title="T (K)") if station == "centerline" else None),
                opacity=0.9,
                symbol="circle",
            ),
            text=texts,
            hovertemplate="%{text}<extra></extra>",
            name=pretty,
            visible=visible,
        ))

    # Dropdown to toggle traces individually OR sensible presets.
    n_traces = len(fig.data)

    def vis_for(names: list[str]) -> list[bool]:
        return [fig.data[i].name in [n for s, _, n in stations_with_radius if s in names]
                for i in range(n_traces)]

    fig.update_layout(
        title=title or (
            f"Fuel-pin assembly ({n_x}×{n_y} pins, {n_axial} axial slices) — "
            f"peak T = {np.nanmax(data.peak_T_per_pin)-273.15:.0f} °C"
        ),
        scene=dict(
            xaxis_title="x (m)",
            yaxis_title="y (m)",
            zaxis_title="axial z (m)",
            aspectmode="data",
        ),
        margin=dict(l=0, r=0, t=60, b=0),
        updatemenus=[
            dict(
                buttons=[
                    dict(label="Centerline + clad outer",
                         method="update",
                         args=[{"visible": vis_for(["centerline", "clad_outer"])}]),
                    dict(label="All stations",
                         method="update",
                         args=[{"visible": [True] * n_traces}]),
                    dict(label="Centerline only (peak T)",
                         method="update",
                         args=[{"visible": vis_for(["centerline"])}]),
                    dict(label="Coolant only",
                         method="update",
                         args=[{"visible": vis_for(["coolant"])}]),
                    dict(label="Clad outer (wall T)",
                         method="update",
                         args=[{"visible": vis_for(["clad_outer"])}]),
                ],
                direction="down",
                x=0.0, xanchor="left",
                y=1.08, yanchor="top",
                bgcolor="#eeeeee",
            ),
        ],
        annotations=[
            dict(
                text=("<b>Drag</b> to rotate · <b>scroll</b> to zoom · "
                      "<b>shift+drag</b> to pan · hover any point for details"),
                x=0.5, y=1.04, xref="paper", yref="paper",
                showarrow=False, font=dict(size=11),
            ),
        ],
    )

    fig.write_html(str(out_path), include_plotlyjs="cdn", auto_open=False)
    n_points = sum(len(t.x) for t in fig.data if hasattr(t, "x") and t.x is not None)
    print(f"  wrote {out_path}  ({n_points:,} 3-D markers, "
          f"open in a browser to interact)")


__all__ = [
    "AssemblyData",
    "extract_assembly_data",
    "plot_assembly_heatmap",
    "plot_hottest_pin_axial",
    "make_interactive_assembly_view",
]
