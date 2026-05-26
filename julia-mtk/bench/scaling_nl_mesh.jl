# ⚠ PARTIALLY SUPERSEDED (2026-05-21). Correct that nonlinear keeps unknowns, but it
# used the SLOW path (sparse=true symbolic jac + uncolored AD) → misleading N^2.6
# "wall". The fast path (colored AD + KLU) is in scaling_native.jl/diag_colored.jl;
# corrected conclusion in docs/BENCHMARK.md §2 (Julia matches/beats netflow).
#
# Scaling, done right — a NONLINEAR 2D mesh that mtkcompile CANNOT symbolically
# eliminate (so it keeps unknowns and generates a numeric sparse system, the regime
# where Julia should be fast). The earlier linear mesh reduced to 0 unknowns
# (symbolic Gaussian elimination, ~N²) — an artifact, not a real limit.
#
# k(T) = a + b·T makes the flux quadratic ⇒ genuinely nonlinear coupled system.
# Reports unknowns kept (should be ~interior nodes, NOT 0), mtkcompile time, and
# warm solve, with a SPARSE Jacobian. Compare to netflow: 90k nodes / 1.5 s.

using ModelingToolkit, NonlinearSolve
using ModelingToolkit: t_nounits as t

function build_nl_mesh(M)
    n = M * M
    @variables T(t)[1:n]
    idx(i, j) = (i - 1) * M + j
    kcond(Tm) = 10.0 + 0.01 * Tm        # T-dependent conductivity → nonlinear
    eqs = Equation[]
    for i in 1:M, j in 1:M
        c = idx(i, j)
        if j == 1
            push!(eqs, T[c] ~ 1000.0)
        elseif j == M
            push!(eqs, T[c] ~ 300.0)
        else
            nb = Tuple{Int,Int}[(i, j - 1), (i, j + 1)]
            i > 1 && push!(nb, (i - 1, j))
            i < M && push!(nb, (i + 1, j))
            flux = sum(kcond((T[c] + T[idx(p, q)]) / 2) * (T[idx(p, q)] - T[c]) for (p, q) in nb)
            push!(eqs, flux ~ 0)
        end
    end
    @named sys = System(eqs, t)
    return sys
end

function run_case(M; sparse)
    GC.gc()
    sys = build_nl_mesh(M)
    sys2, t_compile = @timed mtkcompile(sys)
    nu = length(unknowns(sys2))
    guesses = [u => 650.0 for u in unknowns(sys2)]
    prob, t_prob = @timed NonlinearProblem(sys2, guesses; sparse = sparse)
    sol, t_cold = @timed solve(prob, NewtonRaphson(); abstol = 1e-6, maxiters = 200)
    _, t_warm = @timed solve(prob, NewtonRaphson(); abstol = 1e-6, maxiters = 200)
    return (; nu, t_compile, t_prob, t_cold, t_warm, retcode = sol.retcode)
end

run_case(5; sparse = true)  # warm up

println(rpad("M", 6), rpad("nodes", 9), rpad("unknowns", 10), rpad("compile[s]", 12),
        rpad("buildprob[s]", 13), rpad("solve_warm[s]", 14), "retcode")
for M in (10, 20, 32, 50, 70, 100)
    r = run_case(M; sparse = true)
    println(rpad(M, 6), rpad(M * M, 9), rpad(r.nu, 10), rpad(round(r.t_compile, digits = 3), 12),
            rpad(round(r.t_prob, digits = 3), 13), rpad(round(r.t_warm, digits = 5), 14), r.retcode)
end
