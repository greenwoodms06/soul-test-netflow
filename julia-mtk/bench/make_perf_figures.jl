# Performance comparison figures. Data are measured on-machine 2026-05-21 (see the
# cited bench scripts); hardcoded here for a reproducible plot. All netflow numbers
# re-measured (not README).
using Plots
mkpath("results")

# --- Fig 1: numeric solve scaling, Julia vs netflow (apples-to-apples 2D mesh) ---
# Julia: native loop residual + colored sparse AD + KLU, NONLINEAR (bench/scaling_native.jl)
jl_nodes = [1024, 10000, 40000, 90000]
jl_solve = [0.00202, 0.0643, 0.38376, 1.46756]
# netflow: resistor mesh, LINEAR 1-iter (bench/remeasure_netflow_scaling.py)
nf_nodes = [1024, 10000, 40000, 90000]
nf_solve = [0.012, 0.110, 0.627, 1.493]

p1 = plot(jl_nodes, jl_solve; xscale = :log10, yscale = :log10, marker = :circle, lw = 2,
          label = "Julia: colored sparse AD + KLU (nonlinear)",
          xlabel = "unknowns (mesh nodes)", ylabel = "solve time [s]",
          title = "Numeric solve scaling — Julia vs netflow", legend = :topleft)
plot!(p1, nf_nodes, nf_solve; marker = :square, lw = 2, ls = :dash,
      label = "netflow: scipy sparse LU (linear, 1 iter)")
annotate!(p1, 10000, 0.0643, text("1.7× faster", 8, :left, :bottom))
savefig(p1, "results/perf_scaling.png")

# --- Fig 2: MTK per-component cost breakdown — codegen dominates, solve is cheap ---
# bench/scaling_mtk.jl (coupled chain, per-component + connect())
u   = [19, 59, 199, 599]
compile = [0.09, 0.35, 2.05, 8.36]
jit     = [0.605, 1.861, 9.658, 37.626]   # cold − warm ≈ cold
warm    = [0.0001, 0.0001, 0.0006, 0.0053]

p2 = plot(u, compile; xscale = :log10, yscale = :log10, marker = :circle, lw = 2,
          label = "mtkcompile (symbolic)", xlabel = "unknowns",
          ylabel = "time [s]", title = "MTK per-component cost: codegen ≫ solve",
          legend = :left)
plot!(p2, u, jit;  marker = :diamond, lw = 2, label = "JIT of generated (unrolled) function")
plot!(p2, u, warm; marker = :square,  lw = 2, label = "numeric solve (warm)")
savefig(p2, "results/perf_costmodel.png")

println("wrote results/perf_scaling.png and results/perf_costmodel.png")
