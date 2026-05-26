# Slice 5 — dynamic/transient fuel pin (the storage extension, ADR-0001).
#
# Adds a HeatCapacitor at the centerline to the slice-1 radial stack — storage
# added WITHOUT changing connectors, exactly as the ADR promised. Constant props,
# so the centerline is an EXACT first-order system:
#     C·dT_cl/dt = Q − (T_cl − T_cool)/R_tot   ⇒   τ = R_tot·C,
#     T(t) = T∞ + (T_cool − T∞)·exp(−t/τ),   T∞ = T_cool + Q·R_tot
#
# VERIFICATION (two analytic anchors):
#   (a) T(∞) equals slice-1's steady centerline (1252.99 K)
#   (b) the time constant: T(τ) equals the first-order value T∞+(T_cool−T∞)/e
#
# This is also the regime the benchmark predicted MTK wins: compile once, step many.
# See docs/adr/0001, docs/BENCHMARK.md §2.
#
# Standing limits (greppable):
# DEBT: constant props, single pin, lumped capacity at centerline only (first-order).
# TODO: transient of the full COUPLED chain (slice 3 + storage); code-comparison vs
#       netflow's solve_transient; a rendered T(t) / axial-profile plot (none yet).

using ModelingToolkit, ModelingToolkitStandardLibrary.Thermal
using OrdinaryDiffEqRosenbrock
using OrdinaryDiffEqNonlinearSolve        # DAE initialization nonlinear solve
using ModelingToolkit: t_nounits as t

# geometry / constant props (slice 1)
r_p, r_ci, r_co, L = 4.10e-3, 4.185e-3, 4.75e-3, 1.0
q, Tcool = 18_000.0, 593.0
k_fuel, k_clad, h_gap, h_conv = 3.0, 16.0, 5_000.0, 30_000.0
R_fuel = 1 / (4π * k_fuel * L)
R_gap  = 1 / (2π * r_p * h_gap * L)
R_clad = log(r_co / r_ci) / (2π * k_clad * L)
R_conv = 1 / (2π * r_co * h_conv * L)
R_tot  = R_fuel + R_gap + R_clad + R_conv

# lumped pellet thermal capacity (netflow's model: m·cp)
ρ_UO2, cp_pellet = 10_900.0, 300.0
C_fuel = π * r_p^2 * L * ρ_UO2 * cp_pellet
τ      = R_tot * C_fuel
T_inf  = Tcool + q * R_tot

@named src  = FixedHeatFlow(Q_flow = q)
@named cap  = HeatCapacitor(C = C_fuel, T = Tcool)
@named Rf   = ThermalResistor(R = R_fuel)
@named Rg   = ThermalResistor(R = R_gap)
@named Rc   = ThermalResistor(R = R_clad)
@named Rh   = ThermalResistor(R = R_conv)
@named cool = FixedTemperature(T = Tcool)

eqs = [
    connect(src.port, cap.port, Rf.port_a),
    connect(Rf.port_b, Rg.port_a),
    connect(Rg.port_b, Rc.port_a),
    connect(Rc.port_b, Rh.port_a),
    connect(Rh.port_b, cool.port),
]
@named pin = System(eqs, t; systems = [src, cap, Rf, Rg, Rc, Rh, cool])
sys = mtkcompile(pin)

t_end = 80.0    # ≈ 12.6 τ
prob = ODEProblem(sys, [cap.T => Tcool], (0.0, t_end))
sol  = solve(prob, Rosenbrock23(); abstol = 1e-9, reltol = 1e-9)
println("retcode: ", sol.retcode)

T_analytic(τt) = T_inf + (Tcool - T_inf) * exp(-τt / τ)   # exact first-order solution

# verify the WHOLE trajectory against the analytic first-order solution
ts = 0.0:1.0:t_end
traj_err = maximum(abs(sol(tt; idxs = cap.T) - T_analytic(tt)) for tt in ts)
T_final  = sol[cap.T][end]
gap_steady = abs(T_final - T_inf)         # residual exp tail at t_end (physical, not error)

println("\nτ = R·C = $(round(τ,digits=3)) s  (C=$(round(C_fuel,digits=1)) J/K, R_tot=$(round(R_tot,digits=5)) K/W)")
println("steady T∞ = $(round(T_inf,digits=3)) K  (slice-1 steady = 1252.989 K)")
println("T($(t_end)) MTK = $(round(T_final,digits=4)) K ; analytic($(t_end)) = $(round(T_analytic(t_end),digits=4)) K")
println("  (residual exp tail to T∞ at $(t_end)s = $(round(gap_steady,digits=4)) K — physical, = (T∞−T_cool)·e^(−t/τ))")
println("max |T_MTK(t) − T_analytic(t)| over trajectory = $(traj_err) K")
println(traj_err < 1e-2 ?
    "TRANSIENT VERIFY PASS (matches exact first-order solution over full trajectory)" :
    "TRANSIENT VERIFY FAIL")
