# Scaling wall — does dropping the per-component/connector style let MTK's symbolic
# build reach netflow's regime? Same coolant-advection coupling as slice 2/3, but
# written as FLAT array equations (no components, no connect()/stream expansion).
# Compare mtkcompile scaling to the per-component result (bench/scaling_mtk.jl:
# 599 unknowns → 8.4 s compile). Hypothesis: the connector machinery was the cost.

using ModelingToolkit, NonlinearSolve
using ModelingToolkit: t_nounits as t

function build_flat(N)
    mdot, cp, T_in = 0.3, 5500.0, 565.0
    Q_cell = 18_000.0 * 3.66 / N
    @variables Tc(t)[1:N]                 # coolant temperature per cell
    eqs = Vector{Equation}(undef, N)
    eqs[1] = mdot * cp * (Tc[1] - T_in) ~ Q_cell
    for i in 2:N
        eqs[i] = mdot * cp * (Tc[i] - Tc[i - 1]) ~ Q_cell
    end
    @named sys = System(collect(eqs), t)
    return sys
end

function run_case(N)
    GC.gc()
    _, t_build = @timed build_flat(N)
    sys = build_flat(N)
    sys2, t_compile = @timed mtkcompile(sys)
    nu = length(unknowns(sys2))
    guesses = [u => 580.0 for u in unknowns(sys2)]
    prob = NonlinearProblem(sys2, guesses)
    _, t_cold = @timed solve(prob, NewtonRaphson(); abstol = 1e-4)
    _, t_warm = @timed solve(prob, NewtonRaphson(); abstol = 1e-4)
    return (; nu, t_build, t_compile, t_cold, t_warm)
end

run_case(10)  # warm up JIT

println(rpad("N", 8), rpad("unknowns", 10), rpad("build[s]", 10),
        rpad("compile[s]", 12), rpad("solve_cold[s]", 14), rpad("solve_warm[s]", 14))
for N in (100, 1000, 5000, 20000)
    r = run_case(N)
    println(rpad(N, 8), rpad(r.nu, 10), rpad(round(r.t_build, digits = 3), 10),
            rpad(round(r.t_compile, digits = 3), 12),
            rpad(round(r.t_cold, digits = 3), 14), rpad(round(r.t_warm, digits = 6), 14))
end
