# Scaling, the SciML way — sparse Jacobian via AD + automatic sparsity detection +
# matrix coloring, with a sparse KLU linear solve. This is how Julia is meant to
# scale nonlinear systems; MTK's symbolic sparse jac (bench/diag_sparse_solve.jl)
# was the slow path. Goal: reach netflow's regime (10k nodes 0.11s, 90k 1.5s).
# NONLINEAR 2D mesh (T-dependent k), keeps all unknowns.

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

sparse_ad = AutoSparse(AutoForwardDiff();
    sparsity_detector = TracerSparsityDetector(),
    coloring_algorithm = GreedyColoringAlgorithm())
alg = NewtonRaphson(autodiff = sparse_ad, linsolve = KLUFactorization())

function run_case(M)
    GC.gc()
    sys, t_compile = @timed mtkcompile(build_nl_mesh(M))
    nu = length(unknowns(sys))
    g = [u => 650.0 for u in unknowns(sys)]
    prob = NonlinearProblem(sys, g)
    solve(prob, alg; abstol = 1e-6, maxiters = 200)              # warm up JIT + detection
    s, t_solve = @timed solve(prob, alg; abstol = 1e-6, maxiters = 200)
    return (; nu, t_compile, t_solve, retcode = s.retcode)
end

run_case(5)  # warm up

println(rpad("M", 6), rpad("nodes", 9), rpad("unknowns", 10),
        rpad("compile[s]", 12), rpad("solve[s]", 12), "retcode")
for M in (10, 32, 70, 100, 140)
    r = run_case(M)
    println(rpad(M, 6), rpad(M * M, 9), rpad(r.nu, 10),
            rpad(round(r.t_compile, digits = 3), 12), rpad(round(r.t_solve, digits = 5), 12), r.retcode)
end
