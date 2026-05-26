# ⚠ SUPERSEDED / RETRACTED RESULT (2026-05-21). This LINEAR mesh triggers MTK
# symbolic Gaussian elimination (→0 unknowns, ~N², "87s at 4900") — an ARTIFACT of
# linearity, NOT a real limit. Real nonlinear physics keeps unknowns and is fast.
# See bench/scaling_native.jl + docs/BENCHMARK.md §2 for the corrected result.
#
# Scaling wall, part 2 — a genuinely COUPLED 2D problem (won't reduce to 0 like the
# 1D chain). Mirrors netflow's resistor_mesh: M×M Laplace grid, Dirichlet left=1,
# right=0. This forces a real sparse linear solve, so it tests whether MTK's
# mtkcompile AND solve reach netflow's 10⁴–10⁵ regime. netflow reference (re-measured):
# 10k nodes 0.14s, 40k 0.76s, 90k 1.88s (setup+solve).

using ModelingToolkit, NonlinearSolve
using ModelingToolkit: t_nounits as t

function build_mesh(M)
    n = M * M
    @variables T(t)[1:n]
    idx(i, j) = (i - 1) * M + j
    eqs = Equation[]
    for i in 1:M, j in 1:M
        k = idx(i, j)
        if j == 1
            push!(eqs, T[k] ~ 1.0)
        elseif j == M
            push!(eqs, T[k] ~ 0.0)
        else
            nb = Int[idx(i, j - 1), idx(i, j + 1)]
            i > 1 && push!(nb, idx(i - 1, j))
            i < M && push!(nb, idx(i + 1, j))
            push!(eqs, sum(T[m] for m in nb) - length(nb) * T[k] ~ 0)
        end
    end
    @named sys = System(eqs, t)
    return sys
end

function run_case(M; sparse)
    GC.gc()
    sys = build_mesh(M)
    sys2, t_compile = @timed mtkcompile(sys)
    nu = length(unknowns(sys2))
    guesses = [u => 0.5 for u in unknowns(sys2)]
    prob = NonlinearProblem(sys2, guesses)
    alg = sparse ? NewtonRaphson(linsolve = nothing) : NewtonRaphson()
    _, t_cold = @timed solve(prob, NewtonRaphson(); abstol = 1e-6, maxiters = 100)
    _, t_warm = @timed solve(prob, NewtonRaphson(); abstol = 1e-6, maxiters = 100)
    return (; nu, t_compile, t_cold, t_warm)
end

run_case(5; sparse = false)  # warm up

println(rpad("M", 6), rpad("nodes", 9), rpad("unknowns", 10), rpad("compile[s]", 12),
        rpad("solve_cold[s]", 14), rpad("solve_warm[s]", 14))
for M in (10, 20, 32, 50, 70)
    r = run_case(M; sparse = false)
    println(rpad(M, 6), rpad(M * M, 9), rpad(r.nu, 10), rpad(round(r.t_compile, digits = 3), 12),
            rpad(round(r.t_cold, digits = 3), 14), rpad(round(r.t_warm, digits = 5), 14))
end
