# Slice 7 — neutronics + Doppler feedback coupled to thermal (MULTIPHYSICS).
#
# Tests MTK's headline strength: composing domains. A custom point-kinetics
# component (signal domain: RealInput fuel-T → RealOutput power) wired to the thermal
# acausal domain (PrescribedHeatFlow ← power; HeatCapacitor fuel; R; coolant;
# TemperatureSensor → feedback) via MTKStandardLibrary Blocks.
#
# Scenario: at t=0 insert +100 pcm external reactivity; power rises, fuel heats,
# negative Doppler (α<0) returns reactivity to 0 at a new equilibrium.
#
# VERIFICATION (analytic Doppler balance): equilibrium ρ→0 ⇒ T_fuel = T_ref −
# ρ_ext/α, and power = (T_fuel − T_cool)/R. Numbers ILLUSTRATIVE, not reactor-
# specific (see validation-vs-code-comparison guardrail).
#
# Standing limits (greppable):
# DEBT: one delayed group; lumped single-node fuel; α/β/Λ illustrative.

using ModelingToolkit, ModelingToolkitStandardLibrary.Thermal, ModelingToolkitStandardLibrary.Blocks
using OrdinaryDiffEqRosenbrock, OrdinaryDiffEqNonlinearSolve
using ModelingToolkit: t_nounits as t, D_nounits as D

# point kinetics (1 delayed group) + Doppler feedback — a signal-domain component
function PointKinetics(; name, β = 0.0065, Λ = 2e-5, λ = 0.08, α = -2.5e-5,
                       ρ_ext = 1e-3, T_ref = 1253.0, P0 = 18_000.0, n0 = 1.0)
    @named T_fuel = RealInput()      # fuel temperature in
    @named power  = RealOutput()     # thermal power out
    ps = @parameters β=β Λ=Λ λ=λ α=α ρ_ext=ρ_ext T_ref=T_ref P0=P0
    vars = @variables n(t)=n0 C(t)=(β/(Λ*λ))*n0 ρ(t)
    eqs = [
        ρ ~ ρ_ext + α * (T_fuel.u - T_ref),
        D(n) ~ ((ρ - β) / Λ) * n + λ * C,
        D(C) ~ (β / Λ) * n - λ * C,
        power.u ~ P0 * n,
    ]
    System(eqs, t, vars, ps; name, systems = [T_fuel, power])
end

# thermal: nominal single-pin lumped node (constant props from slice 1)
Tcool = 593.0
Rth   = 0.0366660            # K/W (radial total, slice 1 constant props)
Cf    = 172.7               # J/K (pellet capacity)
T_nom = Tcool + 18_000.0 * Rth   # 1253 K nominal fuel temp ⇒ T_ref

@named kin    = PointKinetics(ρ_ext = 1e-3, T_ref = T_nom)
@named src    = PrescribedHeatFlow()
@named fuel   = HeatCapacitor(C = Cf, T = T_nom)
@named R      = ThermalResistor(R = Rth)
@named cool   = FixedTemperature(T = Tcool)
@named sensor = TemperatureSensor()

eqs = [
    connect(kin.power, src.Q_flow),                 # power → heat source (signal)
    connect(src.port, fuel.port, R.port_a, sensor.port),
    connect(R.port_b, cool.port),
    connect(sensor.T, kin.T_fuel),                  # fuel T → Doppler feedback (signal)
]
@named plant = System(eqs, t; systems = [kin, src, fuel, R, cool, sensor])
sys = mtkcompile(plant)
println("states: ", length(unknowns(sys)), "  ", unknowns(sys))

t_end = 300.0   # ≫ slowest mode (delayed-neutron τ≈1/λ=12.5 s, > thermal 6.3 s)
prob = ODEProblem(sys, [kin.n => 1.0, fuel.T => T_nom], (0.0, t_end))
sol  = solve(prob, Rosenbrock23(); abstol = 1e-9, reltol = 1e-9)
println("retcode: ", sol.retcode)

# analytic Doppler equilibrium
α = -2.5e-5; ρ_ext = 1e-3
T_eq  = T_nom - ρ_ext / α                 # ρ→0 ⇒ T = T_ref − ρ_ext/α
P_eq  = (T_eq - Tcool) / Rth
n_eq  = P_eq / 18_000.0

T_f  = sol(t_end; idxs = fuel.T)
n_f  = sol(t_end; idxs = kin.n)
ρ_f  = sol(t_end; idxs = kin.ρ)
P_f  = 18_000.0 * n_f
println("\n               MTK final     analytic")
println("T_fuel [K]   $(round(T_f,digits=3))     $(round(T_eq,digits=3))")
println("power  [W]   $(round(P_f,digits=1))    $(round(P_eq,digits=1))")
println("n (rel)      $(round(n_f,digits=5))      $(round(n_eq,digits=5))")
println("ρ (pcm)      $(round(ρ_f*1e5,digits=3))        0.0   (critical at equilibrium)")

ok = abs(T_f - T_eq) < 0.05 && abs(ρ_f) < 5e-6
println("\n", ok ? "MULTIPHYSICS VERIFY PASS (Doppler equilibrium ρ→0, T matches analytic)" :
                   "MULTIPHYSICS VERIFY FAIL")

# figure: the Doppler feedback transient (first 60 s)
using Plots
mkpath("results")
ts = range(0, 60, length = 600)
nrm  = [sol(tt; idxs = kin.n) for tt in ts]
Tf   = [sol(tt; idxs = fuel.T) for tt in ts]
rho  = [sol(tt; idxs = kin.ρ) * 1e5 for tt in ts]   # pcm
p1 = plot(ts, nrm; label = "power n (rel)", ylabel = "n", legend = :right,
          title = "Neutronics↔thermal: +100 pcm step, Doppler settling")
p2 = plot(ts, Tf;  label = "fuel T [K]", ylabel = "T [K]", legend = :right, color = 2)
p3 = plot(ts, rho; label = "reactivity ρ [pcm]", xlabel = "t [s]", ylabel = "ρ [pcm]",
          legend = :right, color = 3)
savefig(plot(p1, p2, p3; layout = (3, 1), size = (640, 620)), "results/neutronics_feedback.png")
println("wrote results/neutronics_feedback.png")
