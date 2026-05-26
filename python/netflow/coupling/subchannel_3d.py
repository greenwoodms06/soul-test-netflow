"""3D + animated visuals of the subchannel coupled-T-H coolant field.

Produces:
  * results/subchannel_axial.gif  — coolant field rising up the assembly
    (each frame = one axial level, inlet -> outlet), showing the spread
    develop and guide-tube cool channels persist.
  * results/subchannel_3d.html    — interactive plotly 3D of the full
    pin x axial coolant field.

Run:  python -m netflow.coupling.subchannel_3d
"""

from __future__ import annotations

import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.animation as animation
import matplotlib.pyplot as plt
import numpy as np

from netflow.coupling.subchannel import solve_coupled_subchannel, GUIDE_17


def main():
    N = 17
    guide = GUIDE_17
    n_ax = 14
    n_fuel = N * N - len(guide)
    cx = cy = (N - 1) / 2
    rmax = np.hypot(cx, cy)
    q_map = np.zeros((N, N))
    for i in range(N):
        for j in range(N):
            r = np.hypot(i - cx, j - cy) / rmax
            q_map[i, j] = 18000.0 * (1.0 + 0.05 * np.cos(r * np.pi / 2) - 0.025)
    total_mdot = 0.358 * n_fuel

    print("Solving 17x17 subchannel (for 3D + animation)...")
    res = solve_coupled_subchannel(
        N, n_ax=n_ax, q_map=q_map, guide=guide, total_mdot=total_mdot,
        guide_K=0.85, lateral_mix_frac=0.22, max_picard=10,
    )
    field = res.coolant_axial - 273.15   # (N,N,n_ax) in C
    print(f"  converged={res.converged}, exit spread {res.spread_K:.1f} K")

    vmin, vmax = field.min(), field.max()
    L = 3.658
    z = np.linspace(0, L, n_ax)

    # --- (A) axial-development animation ---
    fig, ax = plt.subplots(figsize=(6.5, 5.5))
    im = ax.imshow(field[:, :, 0].T, origin="lower", cmap="coolwarm",
                   vmin=vmin, vmax=vmax, extent=[-0.5, N-0.5, -0.5, N-0.5])
    cb = fig.colorbar(im, ax=ax, fraction=0.046, label="coolant T (°C)")
    title = ax.set_title("")
    ax.set_xlabel("pin ix"); ax.set_ylabel("pin iy")
    for (i, j) in guide:
        ax.plot(i, j, "o", mfc="none", mec="black", ms=5, mew=0.7)

    def update(k):
        im.set_data(field[:, :, k].T)
        title.set_text(f"Coolant T rising up the assembly  ·  z = {z[k]:.2f} m "
                       f"({k+1}/{n_ax})")
        return [im, title]

    anim = animation.FuncAnimation(fig, update, frames=n_ax, interval=300)
    out_gif = pathlib.Path("results/subchannel_axial.gif")
    out_gif.parent.mkdir(exist_ok=True)
    anim.save(out_gif, writer="pillow", fps=4, dpi=90)
    plt.close(fig)
    print(f"  wrote {out_gif}")

    # --- (B) interactive 3D plotly ---
    try:
        import plotly.graph_objects as go
        xs, ys, zs, cs, txt = [], [], [], [], []
        for i in range(N):
            for j in range(N):
                for k in range(n_ax):
                    xs.append(i); ys.append(j); zs.append(z[k])
                    cs.append(field[i, j, k])
                    tag = " (guide)" if (i, j) in guide else ""
                    txt.append(f"pin ({i},{j}){tag}<br>z={z[k]:.2f} m<br>"
                               f"T={field[i,j,k]:.1f} °C")
        fig3d = go.Figure(go.Scatter3d(
            x=xs, y=ys, z=zs, mode="markers",
            marker=dict(size=2.5, color=cs, colorscale="RdBu_r",
                        cmin=vmin, cmax=vmax, opacity=0.55,
                        colorbar=dict(title="T (°C)")),
            text=txt, hovertemplate="%{text}<extra></extra>",
        ))
        fig3d.update_layout(
            title="Subchannel coolant field — 17×17 × axial (coupled T-H)",
            scene=dict(xaxis_title="pin ix", yaxis_title="pin iy",
                       zaxis_title="axial z (m)", aspectmode="manual",
                       aspectratio=dict(x=1, y=1, z=1.6)),
            height=700, width=800,
        )
        out_html = pathlib.Path("results/subchannel_3d.html")
        fig3d.write_html(str(out_html), include_plotlyjs="cdn")
        print(f"  wrote {out_html}")
    except ImportError:
        pass


if __name__ == "__main__":
    main()
