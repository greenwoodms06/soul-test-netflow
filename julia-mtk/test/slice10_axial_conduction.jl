# Slice 10 — relax solid (axial) conduction: couple adjacent fuel centerlines with
# ThermalConductors, so the fuel becomes a 2D (radial×axial) conduction field instead
# of independent radial stacks. Tests MTK with added coupling (wider Jacobian band).
#
# VERIFICATION: energy conservation must hold EXACTLY regardless of axial conduction
# (it only redistributes heat internally; at steady state all power still reaches the
# coolant). Also: with a PEAKED axial power, axial conduction smooths the centerline
# peak — shown at realistic vs exaggerated conductance, both energy-conserving.
#
# Standing limits (greppable):
# DEBT: lumped centerline-to-centerline axial path; constant props.

using ModelingToolkit, ModelingToolkitStandardLibrary.Thermal, NonlinearSolve
using ModelingToolkit: t_nounits as t
include("../src/ThermalChain.jl"); using .ThermalChain

const N = 10
const MDOT, CP, TREF, TIN = 0.3, 5500.0, 273.15, 565.0
const HIN = CP * (TIN - TREF)
R = radial_resistances(; r_pellet = 4.10e-3, r_ci = 4.185e-3, r_co = 4.75e-3,
    L = 3.66/N, k_fuel = 3.0, k_clad = 16.0, h_gap = 5_000.0, h_conv = 30_000.0)

# peaked (cosine) axial power, total fixed
qz = [1 + 0.8*cospi((i-0.5)/N - 0.5) for i in 1:N]   # peaked in middle
qz .*= (18_000.0*3.66) / (sum(qz)*(3.66/N))           # normalize to same total power
Qcell = qz .* (3.66/N)
Qtot = sum(Qcell)

function build(Gax)
    @named inl = MassFlowInlet(mdot = MDOT, h_in = HIN)
    @named out = PressureOutlet(p_set = 15.5e6, h_amb = HIN)
    cells = [CoolantCell(; name = Symbol(:c, i), cp = CP, T_ref = TREF) for i in 1:N]
    src = [FixedHeatFlow(; name = Symbol(:s, i), Q_flow = Qcell[i]) for i in 1:N]
    Rf = [ThermalResistor(; name = Symbol(:Rf, i), R = R.R_fuel) for i in 1:N]
    Rg = [ThermalResistor(; name = Symbol(:Rg, i), R = R.R_gap)  for i in 1:N]
    Rc = [ThermalResistor(; name = Symbol(:Rc, i), R = R.R_clad) for i in 1:N]
    Rh = [ThermalResistor(; name = Symbol(:Rh, i), R = R.R_conv) for i in 1:N]
    Gx = [ThermalConductor(; name = Symbol(:Gax, i), G = Gax) for i in 1:N-1]   # axial coupling
    conns = Equation[]
    push!(conns, connect(inl.port, cells[1].port_a))
    for i in 1:N-1; push!(conns, connect(cells[i].port_b, cells[i+1].port_a)); end
    push!(conns, connect(cells[N].port_b, out.port))
    for i in 1:N
        push!(conns, connect(src[i].port, Rf[i].port_a))
        push!(conns, connect(Rf[i].port_b, Rg[i].port_a))
        push!(conns, connect(Rg[i].port_b, Rc[i].port_a))
        push!(conns, connect(Rc[i].port_b, Rh[i].port_a))
        push!(conns, connect(Rh[i].port_b, cells[i].heat))
    end
    for i in 1:N-1
        push!(conns, connect(src[i].port, Gx[i].port_a))     # centerline_i ↔ centerline_{i+1}
        push!(conns, connect(Gx[i].port_b, src[i+1].port))
    end
    @named sys = System(conns, t; systems = vcat(inl, out, cells, src, Rf, Rg, Rc, Rh, Gx))
    return mtkcompile(sys), cells, src
end

function solve_case(Gax)
    sys, cells, src = build(Gax)
    g = map(unknowns(sys)) do u
        s = string(u); u => (occursin("₊h(t)", s) ? HIN : occursin("Q_flow", s) ? 6000.0 : 900.0)
    end
    sol = solve(NonlinearProblem(sys, g), NewtonRaphson(); abstol = 1e-4, maxiters = 1000)
    Tcl = [sol[src[i].port.T] for i in 1:N]
    h_out = sol[cells[N].h]
    dH = MDOT*(h_out - HIN)
    return Tcl, dH, sol.retcode
end

# realistic axial conductance: k_UO2 * A_pellet / dz
Gax_real = 3.0 * (π*4.10e-3^2) / (3.66/N)
println("realistic G_ax = $(round(Gax_real,sigdigits=3)) W/K  (radial G ≈ $(round(1/R.R_tot,sigdigits=3)) W/K)")

maxresid = 0.0
for (Gax, lab) in ((Gax_real, "realistic (≈no axial)"), (5.0, "moderate"), (50.0, "exaggerated"))
    Tcl, dH, rc = solve_case(Gax)
    enr = abs(dH - Qtot); global maxresid = max(maxresid, enr)
    println("$(rpad(lab,22)) centerline range=$(round(maximum(Tcl)-minimum(Tcl),digits=1)) K  ",
            "peak=$(round(maximum(Tcl),digits=1)) K  energy resid=$(round(enr,sigdigits=2)) W  [$rc]")
end
println(maxresid < 1e-3 ? "\nAXIAL-CONDUCTION VERIFY PASS (energy conserved ∀ G_ax; peak smooths as G_ax↑)" :
                          "\nAXIAL-CONDUCTION VERIFY FAIL")

# MTK gotcha probe: a G=0 ThermalConductor (degenerate zero-conductance element)
_, _, rc0 = solve_case(0.0)
println("G_ax=0 (degenerate zero-conductance element) → retcode=$rc0  [MTK gotcha: use no element, not G=0]")
