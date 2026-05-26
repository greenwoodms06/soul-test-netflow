# Slice 4 — reproduce netflow's nonlinear single-pin physics in MTK (accuracy axis).
#
# CODE-TO-CODE COMPARISON (not validation): build the SAME closures netflow uses
# (UO2 phonon+electronic k(T), He gap conduction + gray radiation, Zr clad k(T),
# Dittus-Boelter convection) and check the four node temperatures against the
# RE-MEASURED netflow baseline (bench/remeasure_netflow.py, 1204.75 K — NOT the
# stale README 1201.9 K). See validation-vs-code-comparison guardrail, docs/adr/0001.
#
# Water μ/k_f/Pr are quadratic fits of netflow's CoolProp data over 585-610 K
# (bench/fit_water_props.py; ≤0.35% error, reproduces netflow's h to 0.12%) —
# avoids a CoolProp.jl C-build. Conduction k evaluated at layer mean temperature,
# exactly as netflow does.
#
# Standing limits (greppable):
# DEBT: water-prop fit valid only ~585-610 K (subcooled liquid; sat≈618 K at 15.5 MPa).
# DEBT: fixed coolant 593 K (single pin) — coupling to the solved channel is slice 3.

using ModelingToolkit, NonlinearSolve
using ModelingToolkit: t_nounits as t

# ---- geometry / operating point (netflow quick-start) -----------------------
r_p   = 4.10e-3
r_ci_ = r_p + 0.085e-3
r_co  = 4.75e-3
L     = 1.0
q     = 18_000.0
Tcool = 593.0
σ     = 5.670374419e-8
ε     = 0.85
Agap  = 2π * r_p * L
Aht   = 3.14e-2
Dh    = 12.0e-3
mdot  = 0.30
Axs   = π * Dh^2 / 4

# ---- netflow's exact closures (symbolic-friendly) ---------------------------
kUO2(T) = 1 / (0.0375 + 2.165e-4 * T) + 4.715e9 / T^2 * exp(-16361 / T)
kHe(T)  = 2.682e-3 * T^0.71
kZr(T)  = 12.6 + 0.0048 * (T - 300)
# water @ 15.5 MPa, quadratic fits of netflow's CoolProp (585-610 K)
muf(T)  = -2.0223992769e-9 * T^2 + 1.9761159982e-6 * T - 3.8012592650e-4
kff(T)  = -1.3080990232e-5 * T^2 + 1.3581205087e-2 * T - 2.9242712999
Prf(T)  =  2.1996090686e-4 * T^2 - 2.5487516332e-1 * T + 7.4721737357e1

@variables T_cl(t) T_ps(t) T_ci(t) T_co(t)

# fluxes (a→b positive), k at layer mean T — matching netflow
f_pellet = 4π * kUO2((T_cl + T_ps) / 2) * L * (T_cl - T_ps)
f_gapc   = 2π * L * kHe((T_ps + T_ci) / 2) / log(r_ci_ / r_p) * (T_ps - T_ci)
f_gapr   = σ * ε * Agap * (T_ps^4 - T_ci^4)
f_clad   = 2π * L * kZr((T_ci + T_co) / 2) / log(r_co / r_ci_) * (T_ci - T_co)
Tfilm    = (T_co + Tcool) / 2
Re_      = mdot * Dh / (muf(Tfilm) * Axs)
Nu_      = 0.023 * Re_^0.8 * Prf(Tfilm)^0.4        # heating (clad hotter): n=0.4
h_       = Nu_ * kff(Tfilm) / Dh
f_conv   = h_ * Aht * (T_co - Tcool)

# node energy balances (KCL: net flux out = source)
eqs = [
    0 ~ q - f_pellet,                       # centerline (source q)
    0 ~ f_pellet - (f_gapc + f_gapr),       # pellet surface
    0 ~ (f_gapc + f_gapr) - f_clad,         # clad inner
    0 ~ f_clad - f_conv,                    # clad outer
]

@named sys = System(eqs, t)
sys = mtkcompile(sys)

guess = [T_cl => 1200.0, T_ps => 830.0, T_ci => 635.0, T_co => 610.0]
prob = NonlinearProblem(sys, guess)
sol  = solve(prob, NewtonRaphson(); abstol = 1e-4, maxiters = 1000)
println("retcode: ", sol.retcode, " ; ||resid|| = ", sqrt(sum(abs2, sol.resid)))

# ---- compare to RE-MEASURED netflow (bench/remeasure_netflow.py) ------------
nf = (centerline = 1204.7488, pellet_surface = 834.8303,
      clad_inner = 637.3277, clad_outer = 611.7027)
mtk = (centerline = sol[T_cl], pellet_surface = sol[T_ps],
       clad_inner = sol[T_ci], clad_outer = sol[T_co])

println("\n node              MTK [K]     netflow [K]   Δ [K]")
maxd = 0.0
for k in keys(nf)
    d = abs(getfield(mtk, k) - getfield(nf, k))
    global maxd = max(maxd, d)
    println("  $(rpad(string(k),16)) $(rpad(round(getfield(mtk,k),digits=3),11)) $(rpad(getfield(nf,k),13)) $(round(d,digits=4))")
end
println("\n max node Δ vs netflow = $(round(maxd,digits=4)) K")
println(maxd < 0.5 ? "CODE-COMPARISON PASS (MTK reproduces netflow within 0.5 K)" :
                     "CODE-COMPARISON: Δ exceeds 0.5 K — investigate")
