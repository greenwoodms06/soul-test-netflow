# Scaling, fast path v2 — sparsity by DETECTION (TracerSparsityDetector), not MTK's
# slow symbolic sparse jac. NonlinearSolve auto-colors + does sparse colored AD;
# KLU sparse solve. Separates one-time costs (mtkcompile + first solve: detection/
# coloring/JIT) from the amortized WARM solve (the netflow-comparable numeric cost).
# netflow ref (re-measured): 10k nodes 0.11s solve, 40k 0.63s, 90k 1.5s.

using ModelingToolkit, NonlinearSolve, LinearSolve, SparseArrays
using ADTypes, SparseConnectivityTracer, SparseMatrixColorings
using ModelingToolkit: t_nounits as t

function build_nl_mesh(M)
    n = M * M
    @variables T(t)[1:n]
    idx(i, j) = (i - 1) * M + j
    kcond(Tm) = 10.0 + 0.01 * Tm
    eqs = Equation[]
    for i in 1:M, j in 1:M
        c = idx(i, j)
        if j == 1
            push!(eqs, T[c] ~ 1000.0)
        elseif j == M
            push!(eqs, T[c] ~ 300.0)
        else
            nb = Tuple{Int,Int}[(i, j - 1), (i, j + 1)]
            i > 1 && push!(nb, (i - 1, j)); i < M && push!(nb, (i + 1, j))
            push!(eqs, sum(kcond((T[c] + T[idx(p,q)]) / 2) * (T[idx(p,q)] - T[c]) for (p,q) in nb) ~ 0)
        end
    end
    @named sys = System(eqs, t); return sys
end

function fast_prob(sys, g)
    prob0 = NonlinearProblem(sys, g)                                   # fast, no symbolic jac
    f = prob0.f.f; u0 = prob0.u0; p = prob0.p
    fbang!(du, u) = f(du, u, p)
    jp = jacobian_sparsity(fbang!, similar(u0), u0, TracerSparsityDetector())  # FAST pattern
    colvec = column_colors(coloring(jp, ColoringProblem(), GreedyColoringAlgorithm()))
    f2 = NonlinearFunction{true}(f; jac_prototype = Float64.(jp), colorvec = colvec)
    return NonlinearProblem(f2, u0, p)
end

alg = NewtonRaphson(linsolve = KLUFactorization())

function run_case(M)
    GC.gc()
    sys, t_compile = @timed mtkcompile(build_nl_mesh(M))
    nu = length(unknowns(sys))
    g = [u => 650.0 for u in unknowns(sys)]
    prob, t_setup = @timed fast_prob(sys, g)
    s_cold, t_cold = @timed solve(prob, alg; abstol = 1e-6, maxiters = 200)  # +detect/color/JIT
    s, t_warm = @timed solve(prob, alg; abstol = 1e-6, maxiters = 200)       # numeric only
    return (; nu, t_compile, t_setup, t_cold, t_warm, retcode = s.retcode)
end

run_case(6)  # warm up

println(rpad("M", 6), rpad("unknowns", 10), rpad("compile[s]", 12), rpad("setup[s]", 11),
        rpad("cold[s]", 11), rpad("warm[s]", 11), "retcode")
for M in (32, 50, 70, 100)
    r = run_case(M)
    println(rpad(M, 6), rpad(r.nu, 10), rpad(round(r.t_compile, digits = 3), 12),
            rpad(round(r.t_setup, digits = 3), 11), rpad(round(r.t_cold, digits = 4), 11),
            rpad(round(r.t_warm, digits = 5), 11), r.retcode)
end
