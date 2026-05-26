"""Startup transient: PWR-like fuel assembly going from cold to full power.

Scenario:
* 7×7 fuel-pin assembly, 20 axial slices
* Non-identical radial power (cosine tilt, peak/avg = 1.4)
* Cosine axial power shape (peak/avg = 1.5)
* Coolant solved as unknown, with cross-pin mixing (5%)
* Initial state: cold isothermal at coolant inlet T (565 K)
* Power ramp: q_lin(t) = q_nominal · smoothstep(t, 0, 30) over 30 s
* Total simulation: 120 s

Outputs to ``results/``:
* ``startup_assembly.gif``  — animated centerline-T heatmap
* ``startup_profiles.png``  — multi-panel: axial profile @ key times,
                              key node trajectories, q_lin(t)
* ``startup_3d.html``       — interactive plotly with time slider
"""

from __future__ import annotations

import argparse
import pathlib
import re
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.animation as animation
import matplotlib.pyplot as plt
import numpy as np

from netflow.bench.fuel_array import (
    T_COOLANT_INLET, build_pin_assembly,
    cosine_axial_shape, cosine_radial_power,
)
from netflow.plugins.thermal import CoolPropFluid


_CENTERLINE_RE = re.compile(r"^p(\d+)_(\d+)_z(\d+)_centerline$")


def smoothstep_ramp(t: float, t_start: float, t_end: float) -> float:
    """Smooth 0→1 ramp over [t_start, t_end] (cubic Hermite)."""
    if t <= t_start:
        return 0.0
    if t >= t_end:
        return 1.0
    s = (t - t_start) / (t_end - t_start)
    return s * s * (3 - 2 * s)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pins", type=int, default=7)
    parser.add_argument("--axial", type=int, default=20)
    parser.add_argument("--t-end", type=float, default=120.0)
    parser.add_argument("--ramp-end", type=float, default=30.0)
    parser.add_argument("--n-frames", type=int, default=48)
    parser.add_argument("--rtol", type=float, default=1e-4)
    parser.add_argument("--atol", type=float, default=1e-1,
                        help="absolute tolerance in Kelvin")
    parser.add_argument("--max-step", type=float, default=2.0,
                        help="cap on integrator step (s)")
    parser.add_argument("--mixing", type=float, default=0.05)
    parser.add_argument("--axial-peak-factor", type=float, default=1.5)
    parser.add_argument("--radial-peak-factor", type=float, default=1.4)
    parser.add_argument("--name-tag", type=str, default="",
                        help="optional suffix appended to all output filenames")
    parser.add_argument("--out", type=pathlib.Path,
                        default=pathlib.Path("results"))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    N = args.pins
    K = args.axial
    print(f"Building {N}×{N} × {K} axial assembly…")
    fluid = CoolPropFluid("Water", default_P=15.5e6)
    q_radial = cosine_radial_power(N, N, peak_factor=args.radial_peak_factor)
    ax_shape = cosine_axial_shape(args.axial_peak_factor)
    net, meta = build_pin_assembly(
        n_x=N, n_y=N, n_axial=K,
        q_lin=q_radial, axial_shape=ax_shape,
        coolant_fluid=fluid, coolant_as_unknown=True,
        cross_pin_mixing_fraction=args.mixing,
    )
    print(f"  {len(net.nodes)} nodes, {len(net.edges)} edges")

    # Capture nominal centerline sources so we can scale them in source_fn
    nominal_sources: dict[str, float] = {}
    for nid, node in net.nodes.items():
        if _CENTERLINE_RE.match(nid):
            nominal_sources[nid] = node.source
    print(f"  {len(nominal_sources)} centerline source nodes catalogued")

    # Time-varying power: ramp 0 → nominal over [0, ramp_end]
    def source_fn(t: float, network) -> None:
        scale = smoothstep_ramp(t, 0.0, args.ramp_end)
        for nid, q0 in nominal_sources.items():
            network._nodes[nid].source = scale * q0    # noqa: SLF001

    # Initial state: cold isothermal at coolant inlet T (everything at 565 K)
    y0 = {nid: T_COOLANT_INLET for nid in net.nodes}
    # Set initial source to zero (ramp begins at 0)
    for nid in nominal_sources:
        net._nodes[nid].source = 0.0      # noqa: SLF001

    # Evaluate at evenly spaced frames
    t_eval = np.linspace(0.0, args.t_end, args.n_frames)
    print(f"Integrating 0 → {args.t_end} s with ramp ending at {args.ramp_end} s, "
          f"{args.n_frames} frames…")
    t0 = time.perf_counter()
    tr = net.solve_transient(
        (0.0, args.t_end), y0=y0, source_fn=source_fn,
        t_eval=t_eval, method="BDF",
        rtol=args.rtol, atol=args.atol, max_step=args.max_step,
    )
    print(f"  done in {time.perf_counter() - t0:.1f} s. "
          f"converged={tr.converged}, RHS evals={tr.n_rhs_evals}")
    print(f"  message: {tr.message}")

    # Extract per-pin peak centerline T over axial — frame by frame
    n_frames = len(tr.t)
    peak_T = np.full((N, N, n_frames), np.nan)
    cl_by_pin_z = np.full((N, N, K, n_frames), np.nan)
    cool_by_pin_z = np.full((N, N, K, n_frames), np.nan)
    for nid, traj in tr.states.items():
        m = _CENTERLINE_RE.match(nid)
        if m:
            ix, iy, k = int(m[1]), int(m[2]), int(m[3])
            cl_by_pin_z[ix, iy, k, :] = traj
            continue
        m2 = re.match(r"^p(\d+)_(\d+)_cool_z(\d+)$", nid)
        if m2:
            ix, iy, k = int(m2[1]), int(m2[2]), int(m2[3])
            cool_by_pin_z[ix, iy, k, :] = traj
    peak_T = np.nanmax(cl_by_pin_z, axis=2)   # (N, N, n_frames)

    print(f"  T_peak final = {peak_T[..., -1].max() - 273.15:.1f} °C")
    print(f"  T_peak ramped up by {peak_T[..., -1].max() - peak_T[..., 0].max():.1f} K")

    # ---- (A) Animated heatmap GIF ----
    print("\nGenerating animated heatmap…")
    fig, (ax_hm, ax_ts) = plt.subplots(
        1, 2, figsize=(12, 5.5),
        gridspec_kw=dict(width_ratios=[1.0, 1.0]),
    )

    vmin = T_COOLANT_INLET - 273.15
    vmax = (np.nanmax(cl_by_pin_z) - 273.15) * 1.02
    im = ax_hm.imshow(
        peak_T[..., 0].T - 273.15, origin="lower", cmap="hot",
        vmin=vmin, vmax=vmax,
        extent=[-0.5, N - 0.5, -0.5, N - 0.5],
    )
    ax_hm.set_title(f"Peak centerline T  ·  t = 0.0 s")
    ax_hm.set_xlabel("pin ix"); ax_hm.set_ylabel("pin iy")
    cb = fig.colorbar(im, ax=ax_hm, fraction=0.046, label="T (°C)")

    # Right panel: trajectories of (hot center pin axial profile + q_lin time series)
    ix_hot, iy_hot = N // 2, N // 2
    z_axis = np.linspace(0, 1.5, K)
    line_cl, = ax_ts.plot([], [], color="#cc3333", linewidth=2, label="hot pin centerline")
    line_cool, = ax_ts.plot([], [], color="#3399ff", linewidth=2, label="hot pin coolant")
    ax_ts.set_xlim(0, 1.5)
    ax_ts.set_ylim(vmin, vmax)
    ax_ts.set_xlabel("axial position z (m)")
    ax_ts.set_ylabel("T (°C)")
    ax_ts.set_title(f"Hot pin ({ix_hot},{iy_hot}) axial profile")
    ax_ts.grid(True, alpha=0.3)
    ax_ts.legend(loc="upper right", fontsize=9)

    # q_lin(t) inset
    ax_qlin = fig.add_axes([0.13, 0.84, 0.18, 0.08])
    t_array = tr.t
    qlin_array = np.array([smoothstep_ramp(t, 0.0, args.ramp_end) for t in t_array])
    ax_qlin.plot(t_array, qlin_array, color="#444444", linewidth=1.5)
    qmark, = ax_qlin.plot([0], [0], "ro", markersize=6)
    ax_qlin.set_xlim(0, args.t_end)
    ax_qlin.set_ylim(-0.05, 1.10)
    ax_qlin.set_yticks([0, 1])
    ax_qlin.set_yticklabels(["off", "full"])
    ax_qlin.set_xlabel("t (s)", fontsize=8)
    ax_qlin.tick_params(labelsize=7)
    ax_qlin.set_title("q_lin(t)", fontsize=8)

    def update(frame_idx: int):
        T = peak_T[..., frame_idx].T - 273.15
        im.set_data(T)
        ax_hm.set_title(f"Peak centerline T  ·  t = {tr.t[frame_idx]:5.1f} s")
        line_cl.set_data(z_axis, cl_by_pin_z[ix_hot, iy_hot, :, frame_idx] - 273.15)
        line_cool.set_data(z_axis, cool_by_pin_z[ix_hot, iy_hot, :, frame_idx] - 273.15)
        qmark.set_data([tr.t[frame_idx]], [qlin_array[frame_idx]])
        return [im, line_cl, line_cool, qmark]

    anim = animation.FuncAnimation(
        fig, update, frames=n_frames, blit=False, interval=80,
    )
    tag = f"_{args.name_tag}" if args.name_tag else ""
    gif_path = args.out / f"startup_assembly{tag}.gif"
    anim.save(gif_path, writer="pillow", fps=12, dpi=90)
    plt.close(fig)
    print(f"  wrote {gif_path}")

    # ---- (B) Multi-panel summary PNG ----
    print("\nGenerating summary panel…")
    fig, ((ax_a, ax_b), (ax_c, ax_d)) = plt.subplots(2, 2, figsize=(13, 9))

    # Centerline trajectory of a few selected pins
    selected = [
        ("hot center", N // 2, N // 2, "#cc3333"),
        ("mid edge", N // 2, 0, "#cc9933"),
        ("cool corner", 0, 0, "#3366aa"),
    ]
    for label, ix, iy, color in selected:
        peak_traj = np.nanmax(cl_by_pin_z[ix, iy, :, :], axis=0) - 273.15
        ax_a.plot(tr.t, peak_traj, color=color, linewidth=2, label=label)
    ax_a.axvline(args.ramp_end, color="black", linestyle="--", alpha=0.5)
    ax_a.text(args.ramp_end, ax_a.get_ylim()[1] * 0.95, " ramp ends",
              fontsize=8, va="top")
    ax_a.set_xlabel("t (s)")
    ax_a.set_ylabel("peak centerline T (°C)")
    ax_a.set_title("Centerline T trajectories of selected pins")
    ax_a.grid(True, alpha=0.3)
    ax_a.legend()

    # Axial profile of hot pin at several times
    times_to_show = [0, args.ramp_end / 2, args.ramp_end, args.t_end / 2, args.t_end]
    times_to_show = [t for t in times_to_show if t <= args.t_end]
    for t_show in times_to_show:
        f_idx = np.argmin(np.abs(tr.t - t_show))
        T_axial = cl_by_pin_z[ix_hot, iy_hot, :, f_idx] - 273.15
        ax_b.plot(z_axis, T_axial, marker="o", markersize=4,
                  label=f"t = {tr.t[f_idx]:.1f} s")
    ax_b.set_xlabel("axial z (m)")
    ax_b.set_ylabel("centerline T (°C)")
    ax_b.set_title(f"Hot pin ({ix_hot},{iy_hot}) centerline axial profile vs time")
    ax_b.grid(True, alpha=0.3)
    ax_b.legend(fontsize=9)

    # Coolant outlet T over time, per-pin (show fan-out)
    for ix in range(N):
        for iy in range(N):
            outlet = cool_by_pin_z[ix, iy, -1, :] - 273.15
            ax_c.plot(tr.t, outlet, alpha=0.25, color="#3399ff", linewidth=0.8)
    # Highlight hot and cool pins
    ax_c.plot(tr.t, cool_by_pin_z[N//2, N//2, -1, :] - 273.15,
              color="#cc3333", linewidth=2, label="hot center")
    ax_c.plot(tr.t, cool_by_pin_z[0, 0, -1, :] - 273.15,
              color="#3366aa", linewidth=2, label="cool corner")
    ax_c.set_xlabel("t (s)")
    ax_c.set_ylabel("coolant outlet T (°C)")
    ax_c.set_title("Coolant outlet trajectories (every pin, blue fan)")
    ax_c.grid(True, alpha=0.3)
    ax_c.legend()

    # Power ramp
    ax_d.plot(tr.t, qlin_array, color="#cc3333", linewidth=2)
    ax_d.axvline(args.ramp_end, color="black", linestyle="--", alpha=0.5)
    ax_d.set_xlabel("t (s)"); ax_d.set_ylabel("q_lin(t) / q_nominal")
    ax_d.set_title("Power ramp (smoothstep)")
    ax_d.grid(True, alpha=0.3)

    fig.suptitle(
        f"PWR fuel-pin assembly startup — {N}×{N} × {K} axial · "
        f"cosine radial peak/avg=1.4 · axial peak/avg=1.5 · mix=0.05",
        fontsize=12,
    )
    fig.tight_layout()
    png_path = args.out / f"startup_profiles{tag}.png"
    fig.savefig(png_path, dpi=120)
    plt.close(fig)
    print(f"  wrote {png_path}")

    # ---- (C) Plotly interactive HTML with time slider ----
    print("\nGenerating interactive plotly HTML…")
    import plotly.graph_objects as go
    frames = []
    for f_idx in range(n_frames):
        frames.append(go.Frame(
            data=[go.Heatmap(
                z=peak_T[..., f_idx].T - 273.15,
                colorscale="Hot", zmin=vmin, zmax=vmax,
                colorbar=dict(title="T (°C)"),
            )],
            name=f"{tr.t[f_idx]:.1f}",
        ))
    fig_pl = go.Figure(
        data=[go.Heatmap(
            z=peak_T[..., 0].T - 273.15,
            colorscale="Hot", zmin=vmin, zmax=vmax,
            colorbar=dict(title="T (°C)"),
        )],
        frames=frames,
    )
    fig_pl.update_layout(
        title=f"Startup transient — peak centerline T  ·  {N}×{N} × {K} axial",
        xaxis_title="pin ix",
        yaxis_title="pin iy",
        height=600, width=700,
        sliders=[dict(
            active=0,
            steps=[dict(
                method="animate",
                args=[[f"{tr.t[i]:.1f}"],
                      dict(mode="immediate", frame=dict(duration=80, redraw=True))],
                label=f"{tr.t[i]:.0f}s",
            ) for i in range(n_frames)],
        )],
        updatemenus=[dict(
            type="buttons", showactive=False,
            buttons=[
                dict(label="▶ play", method="animate",
                     args=[None, dict(frame=dict(duration=80, redraw=True),
                                      fromcurrent=True)]),
                dict(label="⏸ pause", method="animate",
                     args=[[None], dict(frame=dict(duration=0, redraw=False),
                                        mode="immediate")]),
            ],
        )],
    )
    html_path = args.out / f"startup_3d{tag}.html"
    fig_pl.write_html(str(html_path), include_plotlyjs="cdn")
    print(f"  wrote {html_path}")

    print("\nAll outputs written to", args.out.resolve())


if __name__ == "__main__":
    main()
