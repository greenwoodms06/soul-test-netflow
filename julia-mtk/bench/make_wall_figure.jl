# The dev money-figure: symbolic compile/codegen cost vs system size for all three
# MTK modeling approaches — they all scalarize, so they all wall. Data measured
# on-machine 2026-05-21 (bench/scaling_assembly.jl, repro_array_scalarize.jl,
# scaling_mol.jl); hardcoded for a reproducible plot.
using Plots
mkpath("results")

# per-component (@named + connect()) — mtkcompile
pc_n = [19, 79, 179, 319, 499, 979, 1999]
pc_t = [0.104, 0.498, 1.509, 3.415, 7.264, 18.772, 71.146]
# array-equation (@variables u[1:N], one array eq) — mtkcompile
ar_n = [98, 298, 998, 2998]
ar_t = [0.038, 0.069, 0.335, 1.969]
# MethodOfLines — discretize (symbolic codegen; note: + a large 1st-solve JIT on top)
mol_n = [81, 361, 841, 1521]
mol_t = [0.69, 2.92, 7.59, 16.52]

p = plot(pc_n, pc_t; xscale = :log10, yscale = :log10, marker = :circle, lw = 2,
         label = "per-component (@named + connect)", legend = :topleft,
         xlabel = "system size (unknowns or grid points)",
         ylabel = "symbolic compile [s]",
         title = "MTK compile cost scales with system size (all 3 approaches)")
plot!(p, ar_n, ar_t; marker = :square, lw = 2, label = "array equation (u[1:N])")
plot!(p, mol_n, mol_t; marker = :diamond, lw = 2, label = "MethodOfLines (discretize)")
# guide line ~ linear, for reference
plot!(p, [50, 3000], [0.05, 3.0]; ls = :dot, color = :gray, label = "∝ N (reference)")
savefig(p, "results/mtk_compile_wall.png")
println("wrote results/mtk_compile_wall.png")
