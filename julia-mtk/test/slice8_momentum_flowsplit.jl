# Slice 8 — momentum + parallel-channel flow split (activates the inert FluidPort.p).
#
# Adds a friction pressure-drop closure Δp = K·ṁ·|ṁ| (turbulent) and N parallel
# channels sharing a common inlet/outlet pressure, so flow distributes by hydraulic
# resistance. Tests MTK on: the across/through (p / ṁ) momentum coupling, a nonlinear
# friction whose Jacobian is SINGULAR at ṁ=0 (netflow flagged this as genuinely
# hard — Darcy-Weisbach), and the parallel network (Σṁ at plena, equal p).
#
# VERIFICATION (analytic): each channel ṁ_i = sign(Δp)·√(|Δp|/K_i); Σ = total.
#
# Standing limits (greppable):
# DEBT: isothermal flow split (enthalpy carried but passive); steady; K constant.

using ModelingToolkit, NonlinearSolve
using ModelingToolkit: t_nounits as t, instream, Flow, Stream

@connector function FluidPort(; name)
    vars = @variables begin
        p(t), [guess = 1.0e5]
        m_flow(t), [guess = 0.0, connect = Flow]
        h_outflow(t), [guess = 1.0e5, connect = Stream]
    end
    System(Equation[], t, vars, []; name)
end

# friction pipe: momentum (Δp ~ K·ṁ|ṁ|), adiabatic enthalpy passthrough
function FrictionPipe(; name, K = 1.0e8)
    @named port_a = FluidPort()
    @named port_b = FluidPort()
    ps = @parameters K = K
    eqs = [
        port_a.m_flow + port_b.m_flow ~ 0,
        port_a.p - port_b.p ~ K * port_a.m_flow * abs(port_a.m_flow),
        port_a.h_outflow ~ instream(port_b.h_outflow),
        port_b.h_outflow ~ instream(port_a.h_outflow),
    ]
    System(eqs, t, [], ps; name, systems = [port_a, port_b])
end

function PressureBoundary(; name, p = 1.0e5, h = 1.0e5)
    @named port = FluidPort()
    ps = @parameters p_set = p h_set = h
    eqs = [port.p ~ p_set, port.h_outflow ~ h_set]
    System(eqs, t, [], ps; name, systems = [port])
end

# 3 parallel channels, different resistances, common Δp
Ks    = [1.0e8, 2.0e8, 4.0e8]
p_in  = 2.0e5
p_out = 1.0e5
Δp    = p_in - p_out

@named inlet  = PressureBoundary(p = p_in,  h = 1.2e6)
@named outlet = PressureBoundary(p = p_out, h = 1.2e6)
ch = [FrictionPipe(; name = Symbol(:ch, i), K = Ks[i]) for i in 1:3]

conns = Equation[]
push!(conns, connect(inlet.port,  ch[1].port_a, ch[2].port_a, ch[3].port_a))
push!(conns, connect(outlet.port, ch[1].port_b, ch[2].port_b, ch[3].port_b))
@named net = System(conns, t; systems = [inlet, outlet, ch...])
sys = mtkcompile(net)
println("unknowns: ", length(unknowns(sys)))

# start guess AWAY from ṁ=0 (friction Jacobian is singular there)
guess = map(unknowns(sys)) do u
    s = string(u)
    u => (occursin("m_flow", s) ? 0.02 : occursin("h_outflow", s) ? 1.2e6 : 1.5e5)
end
prob = NonlinearProblem(sys, guess)
sol  = solve(prob, NewtonRaphson())
println("retcode: ", sol.retcode)

println("\n channel   K          MTK ṁ [kg/s]   analytic √(Δp/K)")
maxerr = 0.0
for i in 1:3
    mdot = sol[ch[i].port_a.m_flow]
    an   = sqrt(Δp / Ks[i])
    global maxerr = max(maxerr, abs(mdot - an))
    println("   $i      $(Ks[i])   $(round(mdot,digits=6))      $(round(an,digits=6))")
end
mtot = sum(sol[ch[i].port_a.m_flow] for i in 1:3)
println(" total ṁ = $(round(mtot,digits=6)) kg/s ; max |Δ| = $(maxerr)")
println(maxerr < 1e-8 ? "FLOW-SPLIT VERIFY PASS (ṁ_i = √(Δp/K_i))" : "FLOW-SPLIT VERIFY FAIL")

# the genuinely-hard case (netflow flagged): start at ṁ=0 where d(K·ṁ|ṁ|)/dṁ = 0
println("\n--- zero-flow start (singular friction Jacobian) ---")
gz = map(unknowns(sys)) do u
    s = string(u); u => (occursin("m_flow", s) ? 0.0 : occursin("h_outflow", s) ? 1.2e6 : 1.5e5)
end
for (alg, lab) in ((NewtonRaphson(), "NewtonRaphson"), (nothing, "default polyalgorithm"))
    s = alg === nothing ? solve(NonlinearProblem(sys, gz)) : solve(NonlinearProblem(sys, gz), alg)
    err = maximum(abs(s[ch[i].port_a.m_flow] - sqrt(Δp/Ks[i])) for i in 1:3)
    println("  $(rpad(lab,24)) retcode=$(s.retcode)  max|Δ|=$(round(err,sigdigits=3))")
end
