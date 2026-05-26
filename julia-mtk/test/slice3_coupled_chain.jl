# Slice 3 — full fuel-channel→coolant→loop chain (the bounded model).
#
# Couples slice-1 (fuel-pin radial conduction) to slice-2 (coolant advection):
# each axial cell has its own fuel-pin radial stack whose convection resistor dumps
# heat into that cell's coolant; the coolant advects it downstream.
#
# PURPOSE (verification): two global/local invariants to machine precision —
#   (a) ENERGY CLOSURE: Σ Q_i == ṁ·(h_out − h_in)  (all fuel power ends in coolant)
#   (b) PER-PIN radial drop: T_center_i == T_cool_i + Q_i·R_tot_radial
#
# Constant properties still (machinery + coupling verification). Matching netflow's
# T-dependent 1201.9 K is slice 4. See docs/adr/0001.
#
# Standing limits (greppable):
# DEBT: constant props; forward-flow; no momentum. Convection uses cell BULK T.
# TODO: T-dependent k_UO2 + real water props + netflow's closures (slice 4).

using ModelingToolkit
using ModelingToolkitStandardLibrary.Thermal
using NonlinearSolve
using ModelingToolkit: t_nounits as t
include("../src/ThermalChain.jl")
using .ThermalChain

# ---- Scenario (netflow's pin geometry; uniform axial power) ------------------
N       = 10
mdot    = 0.3
cp      = 5500.0
T_ref   = 273.15
T_in    = 565.0
h_in    = cp * (T_in - T_ref)

r_pellet = 4.10e-3
r_ci     = r_pellet + 0.085e-3
r_co     = 4.75e-3
L_total  = 3.66
dz       = L_total / N
q_lin    = 18_000.0
Q_cell   = q_lin * dz          # power per axial segment
Q_tot    = q_lin * L_total

# radial resistances per segment (length dz)
R = radial_resistances(; r_pellet, r_ci, r_co, L = dz,
    k_fuel = 3.0, k_clad = 16.0, h_gap = 5_000.0, h_conv = 30_000.0)

# ---- Build coupled chain ----------------------------------------------------
@named inlet  = MassFlowInlet(mdot = mdot, h_in = h_in)
@named outlet = PressureOutlet(p_set = 15.5e6, h_amb = h_in)
cells = [CoolantCell(; name = Symbol(:cell, i), cp = cp, T_ref = T_ref) for i in 1:N]

# per-cell fuel-pin radial stack
src = [FixedHeatFlow(; name = Symbol(:src, i), Q_flow = Q_cell) for i in 1:N]
Rf  = [ThermalResistor(; name = Symbol(:Rf, i), R = R.R_fuel) for i in 1:N]
Rg  = [ThermalResistor(; name = Symbol(:Rg, i), R = R.R_gap)  for i in 1:N]
Rc  = [ThermalResistor(; name = Symbol(:Rc, i), R = R.R_clad) for i in 1:N]
Rh  = [ThermalResistor(; name = Symbol(:Rh, i), R = R.R_conv) for i in 1:N]

conns = Equation[]
# coolant chain
push!(conns, connect(inlet.port, cells[1].port_a))
for i in 1:(N - 1)
    push!(conns, connect(cells[i].port_b, cells[i + 1].port_a))
end
push!(conns, connect(cells[N].port_b, outlet.port))
# fuel pin per cell: centerline → fuel → gap → clad → conv → coolant cell
for i in 1:N
    push!(conns, connect(src[i].port, Rf[i].port_a))
    push!(conns, connect(Rf[i].port_b, Rg[i].port_a))
    push!(conns, connect(Rg[i].port_b, Rc[i].port_a))
    push!(conns, connect(Rc[i].port_b, Rh[i].port_a))
    push!(conns, connect(Rh[i].port_b, cells[i].heat))
end

allsys = vcat(inlet, outlet, cells, src, Rf, Rg, Rc, Rh)
@named chain = System(conns, t; systems = allsys)
sys = mtkcompile(chain)
println("n unknowns after mtkcompile: ", length(unknowns(sys)))

# guess every actual unknown: enthalpies→h_in, heat flows→Q_cell, temperatures→T_in
guesses = map(unknowns(sys)) do u
    s = string(u)
    val = occursin("₊h(t)", s)   ? h_in :
          occursin("Q_flow", s)  ? Q_cell : T_in
    u => val
end
prob = NonlinearProblem(sys, guesses)
# abstol matched to residual scale: energy-eq residuals carry W units (terms ~ ṁ·h),
# so the float64 floor is ~1e-11; 1e-6 W = energy balance to microwatts.
sol  = solve(prob, NewtonRaphson(); abstol = 1e-6, maxiters = 1000)
println("retcode: ", sol.retcode, " ; ||resid|| = ", sqrt(sum(abs2, sol.resid)))

# ---- Verify -----------------------------------------------------------------
T_out = sol[cells[N].T]
h_out = sol[cells[N].h]
dH    = mdot * (h_out - h_in)
res_energy = abs(dH - Q_tot)
println("\n(a) ENERGY CLOSURE: ṁ·Δh = $dH W ; ΣQ = $Q_tot W ; residual = $res_energy W")
println("    coolant ΔT = $(T_out - T_in) K (analytic $(Q_tot/(mdot*cp)) K)")

max_radial_err = 0.0
println("\n(b) PER-PIN radial drop (T_center = T_cool + Q·R_tot):")
for i in (1, N ÷ 2, N)
    Tcl   = sol[src[i].port.T]
    Tcool = sol[cells[i].T]
    Tcl_an = Tcool + Q_cell * R.R_tot
    println("    cell $i: T_center = $(round(Tcl,digits=3)) K ; T_cool = $(round(Tcool,digits=3)) K ; analytic centerline = $(round(Tcl_an,digits=3)) K")
end
for i in 1:N
    Tcl = sol[src[i].port.T]
    Tcl_an = sol[cells[i].T] + Q_cell * R.R_tot
    global max_radial_err = max(max_radial_err, abs(Tcl - Tcl_an))
end
println("    max per-pin radial error = $max_radial_err K")

pass = res_energy < 1e-6 && max_radial_err < 1e-6
println("\n", pass ? "VERIFY PASS (energy closed + every pin's radial drop exact)" : "VERIFY FAIL")
