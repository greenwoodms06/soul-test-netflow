# Slice 2 — axial coolant channel with a Modelica-style stream connector.
#
# PURPOSE (verification): confirm the custom FluidPort (m_flow Flow + h_outflow
# Stream) and the instream()-based upwind energy balance conserve energy exactly:
#   ṁ·(h_out − h_in) == Σ Q_i   (steady), and the per-cell temperature staircase
# matches ΔT = Q_tot/(ṁ·cp). Single-phase, constant cp; forward flow only (ṁ>0) —
# full bidirectional actualStream is deferred (this chain never reverses). Heat is
# prescribed per cell here; coupling the real fuel-pin radial stack is slice 3.
# Connector carries specific enthalpy h per Body decision (Modelica/TRANSFORM style).
# See docs/adr/0001.
#
# Standing limits (greppable, per Soul completion gate):
# DEBT: forward-flow only — energy eq uses instream(inlet)+raw(outlet); full
#       bidirectional actualStream(both ports) deferred (this chain never reverses).
# DEBT: constant cp, single-phase — real water properties (Clapeyron/CoolProp/
#       SteamTables) deferred; cp=5500 is representative, NOT a validated value.
# DEBT: no momentum / pressure-drop — FluidPort.p is carried but only passed through.
# TODO: heat is prescribed per cell — couple the slice-1 fuel-pin radial stack to
#       each cell's HeatPort to form the full fuel-channel→coolant chain (slice 3).

using ModelingToolkit
using ModelingToolkitStandardLibrary.Thermal
using NonlinearSolve
using ModelingToolkit: t_nounits as t
using ModelingToolkit: instream, Flow, Stream

# ---- Custom Modelica-style fluid connector ----------------------------------
@connector function FluidPort(; name)
    vars = @variables begin
        p(t), [guess = 15.5e6]                       # Pa, potential (across)
        m_flow(t), [guess = 0.0, connect = Flow]     # kg/s, + into component
        h_outflow(t), [guess = 1.2e6, connect = Stream]  # J/kg, enthalpy if flow leaves here
    end
    System(Equation[], t, vars, []; name)
end

# ---- One axial coolant cell (steady, well-mixed, constant cp) ----------------
function CoolantCell(; name, cp = 5500.0, T_ref = 273.15)
    @named port_a = FluidPort()   # inlet
    @named port_b = FluidPort()   # outlet
    @named heat   = HeatPort()    # heat in (from convection / prescribed)
    ps   = @parameters cp=cp T_ref=T_ref
    vars = @variables h(t) T(t) Q(t)
    eqs = [
        port_a.m_flow + port_b.m_flow ~ 0,         # mass (steady)
        port_a.h_outflow ~ h,                      # well-mixed outflow
        port_b.h_outflow ~ h,
        h ~ cp * (T - T_ref),                      # single-phase property relation
        Q ~ heat.Q_flow,
        heat.T ~ T,
        port_a.p ~ port_b.p,                       # no momentum modeled yet
        # steady energy, forward flow: in via instream, out carries bulk h
        port_a.m_flow * instream(port_a.h_outflow) + port_b.m_flow * port_b.h_outflow + Q ~ 0,
    ]
    System(eqs, t, vars, ps; name, systems = [port_a, port_b, heat])
end

# ---- Boundaries -------------------------------------------------------------
function MassFlowInlet(; name, mdot = 0.3, h_in = 1.2e6)
    @named port = FluidPort()
    ps = @parameters mdot=mdot h_in=h_in
    eqs = [
        port.m_flow ~ -mdot,          # flow leaves source into the system
        port.h_outflow ~ h_in,        # supplied inlet enthalpy
    ]
    System(eqs, t, [], ps; name, systems = [port])
end

function PressureOutlet(; name, p_set = 15.5e6, h_amb = 1.2e6)
    @named port = FluidPort()
    ps = @parameters p_set=p_set h_amb=h_amb
    eqs = [
        port.p ~ p_set,
        port.h_outflow ~ h_amb,       # only used on backflow; forward flow ignores
    ]
    System(eqs, t, [], ps; name, systems = [port])
end

# ---- Assemble an N-cell channel ---------------------------------------------
N      = 10
mdot   = 0.3
cp     = 5500.0
T_ref  = 273.15
T_in   = 565.0
h_in   = cp * (T_in - T_ref)
q_lin  = 18_000.0
L      = 3.66
Q_tot  = q_lin * L
Q_cell = Q_tot / N

@named inlet  = MassFlowInlet(mdot = mdot, h_in = h_in)
@named outlet = PressureOutlet(p_set = 15.5e6, h_amb = h_in)
cells   = [CoolantCell(; name = Symbol(:cell, i), cp = cp, T_ref = T_ref) for i in 1:N]
heaters = [FixedHeatFlow(; name = Symbol(:q, i), Q_flow = Q_cell) for i in 1:N]

conns = Equation[]
push!(conns, connect(inlet.port, cells[1].port_a))
for i in 1:(N - 1)
    push!(conns, connect(cells[i].port_b, cells[i + 1].port_a))
end
push!(conns, connect(cells[N].port_b, outlet.port))
for i in 1:N
    push!(conns, connect(heaters[i].port, cells[i].heat))
end

@named channel = System(conns, t; systems = [inlet, outlet, cells..., heaters...])
sys = mtkcompile(channel)
println("n unknowns after mtkcompile: ", length(unknowns(sys)))

guesses = vcat([cells[i].T => T_in for i in 1:N], [cells[i].h => h_in for i in 1:N])
prob = NonlinearProblem(sys, guesses)
sol  = solve(prob, NewtonRaphson())
println("retcode: ", sol.retcode)

T_out = sol[cells[N].T]
h_out = sol[cells[N].h]
dH    = mdot * (h_out - h_in)
println("\nT_in = $T_in K ; T_out = $T_out K ; ΔT = $(T_out - T_in) K")
println("analytic ΔT = $(Q_tot / (mdot * cp)) K")
println("ṁ·Δh = $dH W ; ΣQ = $Q_tot W ; energy residual = $(abs(dH - Q_tot)) W")
maxstair = 0.0
for i in 1:N
    Ti   = sol[cells[i].T]
    Texp = T_in + i * Q_cell / (mdot * cp)
    global maxstair = max(maxstair, abs(Ti - Texp))
end
println("max per-cell staircase error = $maxstair K")
pass = abs(dH - Q_tot) < 1e-6 && maxstair < 1e-6
println(pass ? "VERIFY PASS (energy conserved + staircase exact)" : "VERIFY FAIL")
