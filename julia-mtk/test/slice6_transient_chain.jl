# Slice 6 — TRANSIENT of the full coupled fuel-channel→coolant chain, with figures.
#
# slice 3 (coupled chain) + storage: HeatCapacitor at each fuel centerline + fluid
# energy storage in each coolant cell (CoolantCellDyn). Cold→full-power startup
# (step at t=0 from a uniform 565 K). Constant props.
#
# VERIFICATION: the t→∞ state must equal the slice-3 steady solution (analytic
# T_cool[i]=T_in+i·Q/(ṁcp), T_cl[i]=T_cool[i]+Q·R_tot). Plus rendered figures.
#
# Standing limits (greppable):
# DEBT: constant props; lumped centerline capacity; coolant mass approximate.

using ModelingToolkit, ModelingToolkitStandardLibrary.Thermal
using OrdinaryDiffEqRosenbrock, OrdinaryDiffEqNonlinearSolve
using ModelingToolkit: t_nounits as t
using Plots
include("../src/ThermalChain.jl"); using .ThermalChain

N      = 10
mdot, cp, T_ref, T_in = 0.3, 5500.0, 273.15, 565.0
h_in   = cp * (T_in - T_ref)
r_p, r_ci, r_co = 4.10e-3, 4.185e-3, 4.75e-3
L_tot  = 3.66
dz     = L_tot / N
q_lin  = 18_000.0
Q_cell = q_lin * dz
R = radial_resistances(; r_pellet = r_p, r_ci, r_co, L = dz,
    k_fuel = 3.0, k_clad = 16.0, h_gap = 5_000.0, h_conv = 30_000.0)

C_fuel = π * r_p^2 * dz * 10_900.0 * 300.0          # pellet capacity per cell [J/K]
M_cool = 700.0 * (π * 12.0e-3^2 / 4) * dz           # coolant mass per cell [kg]

@named inlet  = MassFlowInlet(mdot = mdot, h_in = h_in)
@named outlet = PressureOutlet(p_set = 15.5e6, h_amb = h_in)
cells = [CoolantCellDyn(; name = Symbol(:cell, i), cp, T_ref, M = M_cool) for i in 1:N]
src = [FixedHeatFlow(; name = Symbol(:src, i), Q_flow = Q_cell) for i in 1:N]
cap = [HeatCapacitor(; name = Symbol(:cap, i), C = C_fuel, T = T_in) for i in 1:N]
Rf = [ThermalResistor(; name = Symbol(:Rf, i), R = R.R_fuel) for i in 1:N]
Rg = [ThermalResistor(; name = Symbol(:Rg, i), R = R.R_gap)  for i in 1:N]
Rc = [ThermalResistor(; name = Symbol(:Rc, i), R = R.R_clad) for i in 1:N]
Rh = [ThermalResistor(; name = Symbol(:Rh, i), R = R.R_conv) for i in 1:N]

conns = Equation[]
push!(conns, connect(inlet.port, cells[1].port_a))
for i in 1:(N - 1); push!(conns, connect(cells[i].port_b, cells[i + 1].port_a)); end
push!(conns, connect(cells[N].port_b, outlet.port))
for i in 1:N
    push!(conns, connect(src[i].port, cap[i].port, Rf[i].port_a))
    push!(conns, connect(Rf[i].port_b, Rg[i].port_a))
    push!(conns, connect(Rg[i].port_b, Rc[i].port_a))
    push!(conns, connect(Rc[i].port_b, Rh[i].port_a))
    push!(conns, connect(Rh[i].port_b, cells[i].heat))
end
@named chain = System(conns, t; systems = vcat(inlet, outlet, cells, src, cap, Rf, Rg, Rc, Rh))
sys = mtkcompile(chain)
println("dynamic states: ", length(unknowns(sys)))

u0 = vcat([cap[i].T => T_in for i in 1:N], [cells[i].T => T_in for i in 1:N])
t_end = 60.0
prob = ODEProblem(sys, u0, (0.0, t_end))
sol  = solve(prob, Rosenbrock23(); abstol = 1e-8, reltol = 1e-8)
println("retcode: ", sol.retcode)

# ---- verify final state vs slice-3 steady (analytic) ------------------------
T_cool_ss(i) = T_in + i * Q_cell / (mdot * cp)
T_cl_ss(i)   = T_cool_ss(i) + Q_cell * R.R_tot
T_cl_final   = [sol(t_end; idxs = cap[i].T)   for i in 1:N]
T_cool_final = [sol(t_end; idxs = cells[i].T) for i in 1:N]
maxerr = maximum(max(abs(T_cl_final[i] - T_cl_ss(i)), abs(T_cool_final[i] - T_cool_ss(i))) for i in 1:N)
println("max |final − slice-3 steady| = $(round(maxerr,digits=4)) K  (t_end=$(t_end)s ≈ $(round(t_end/(R.R_tot*C_fuel),digits=1))τ)")
println(maxerr < 0.1 ? "TRANSIENT-CHAIN VERIFY PASS" : "TRANSIENT-CHAIN VERIFY FAIL (likely t_end < ∞ tail)")

# ---- figures ----------------------------------------------------------------
mkpath("results")
p1 = plot(1:N, T_cl_final; marker = :circle, label = "fuel centerline",
          xlabel = "axial cell", ylabel = "T [K]", title = "Axial profile at steady (t=$(t_end)s)")
plot!(p1, 1:N, T_cool_final; marker = :square, label = "coolant bulk")
savefig(p1, "results/transient_chain_profile.png")

ts = range(0, t_end, length = 200)
p2 = plot(; xlabel = "t [s]", ylabel = "T [K]", title = "Startup transient (step power at t=0)")
for (i, lab) in ((1, "centerline cell 1"), (N ÷ 2, "centerline cell $(N÷2)"), (N, "centerline cell $N"))
    plot!(p2, ts, [sol(tt; idxs = cap[i].T) for tt in ts]; label = lab)
end
plot!(p2, ts, [sol(tt; idxs = cells[N].T) for tt in ts]; label = "outlet coolant", ls = :dash)
savefig(p2, "results/transient_chain_timeseries.png")
println("wrote results/transient_chain_profile.png and results/transient_chain_timeseries.png")
