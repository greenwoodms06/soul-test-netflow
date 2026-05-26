# Slice 1 — single steady fuel pin, MTK acausal network vs textbook closed form.
#
# PURPOSE (verification, not validation): confirm ModelingToolkit's connect()
# assembles and solves the across/through thermal network correctly, by checking
# the centerline temperature against the independently-computed analytic
# series-resistance result to machine precision. Constant properties on purpose —
# this isolates the SOLVER MACHINERY from the closures. Matching netflow's
# T-dependent number is a later slice. See docs/adr/0001.
#
# Standing limits (greppable, per Soul completion gate):
# DEBT: constant properties (k_fuel, k_clad, h_gap, h_conv) — machinery verification
#       only; T-dependent UO2 conductivity + netflow's gap/convection closures are
#       needed to match netflow's 1201.9 K (slice 3+). The 1252.99 K here is NOT that.
# TODO: NonlinearSolve retcode reads `Stalled` (linear system already at machine-zero
#       residual on step 1); a LinearProblem/SteadyStateProblem would report `Success`.
#       Correctness is established by the analytic comparison, which is retcode-independent.

using ModelingToolkit
using ModelingToolkitStandardLibrary.Thermal
using NonlinearSolve
using ModelingToolkit: t_nounits as t

# ---- Geometry (netflow's documented pin) ------------------------------------
r_pellet   = 4.10e-3            # m
gap_thick  = 0.085e-3           # m
r_ci       = r_pellet + gap_thick   # clad inner radius, m
r_co       = 4.75e-3            # clad outer radius, m
L          = 1.0               # m
q_lin      = 18_000.0          # W/m
Qtot       = q_lin * L         # W (total power into the pin)

# ---- Representative CONSTANT properties (verification anchor) ----------------
k_fuel = 3.0      # W/m-K  (constant; real UO2 is T-dependent — later)
k_clad = 16.0     # W/m-K
h_gap  = 5_000.0  # W/m^2-K, referenced at r_pellet
h_conv = 30_000.0 # W/m^2-K
T_cool = 593.0    # K

# ---- Analytic series resistances [K/W] --------------------------------------
R_fuel = 1 / (4π * k_fuel * L)
R_gap  = 1 / (2π * r_pellet * h_gap * L)
R_clad = log(r_co / r_ci) / (2π * k_clad * L)
R_conv = 1 / (2π * r_co * h_conv * L)
R_tot  = R_fuel + R_gap + R_clad + R_conv

T_center_analytic = T_cool + Qtot * R_tot
println("R_tot = $R_tot K/W ; analytic centerline = $T_center_analytic K")

# ---- MTK acausal network ----------------------------------------------------
@named src  = FixedHeatFlow(Q_flow = Qtot)   # positive Q_flow injects heat into network
@named Rf   = ThermalResistor(R = R_fuel)
@named Rg   = ThermalResistor(R = R_gap)
@named Rc   = ThermalResistor(R = R_clad)
@named Rh   = ThermalResistor(R = R_conv)
@named cool = FixedTemperature(T = T_cool)

eqs = [
    connect(src.port, Rf.port_a),
    connect(Rf.port_b, Rg.port_a),
    connect(Rg.port_b, Rc.port_a),
    connect(Rc.port_b, Rh.port_a),
    connect(Rh.port_b, cool.port),
]

@named pin = System(eqs, t; systems = [src, Rf, Rg, Rc, Rh, cool])
sys = mtkcompile(pin)

println("unknowns: ", unknowns(sys))

prob = NonlinearProblem(sys, [src.port.T => T_cool])
sol  = solve(prob, NewtonRaphson())
println("retcode: ", sol.retcode)

T_center_mtk = sol[src.port.T]
err = abs(T_center_mtk - T_center_analytic)
println("centerline MTK     = $T_center_mtk K")
println("centerline analytic= $T_center_analytic K")
println("abs error          = $err K")
println(err < 1e-6 ? "VERIFY PASS (machine-precision agreement)" : "VERIFY FAIL")
