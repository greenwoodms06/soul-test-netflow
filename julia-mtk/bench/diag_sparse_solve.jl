# Diagnostic at fixed N — WHY is the nonlinear-mesh solve slow, and does a sparse
# linear solver fix it? Builds the M=32 (960-unknown) nonlinear mesh and compares
# Newton with: default linsolve vs dense LU vs sparse KLU/UMFPACK, all on the sparse
# analytic Jacobian. Reports jac_prototype type (is it actually sparse?) + warm times.

using ModelingToolkit, NonlinearSolve, LinearSolve, SparseArrays
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

M = 32
sys = mtkcompile(build_nl_mesh(M))
nu = length(unknowns(sys))
g  = [u => 650.0 for u in unknowns(sys)]

prob_dense  = NonlinearProblem(sys, g; sparse = false)
prob_sparse = NonlinearProblem(sys, g; sparse = true)
println("unknowns = $nu")
println("dense  jac_prototype: ", typeof(prob_dense.f.jac_prototype))
println("sparse jac_prototype: ", typeof(prob_sparse.f.jac_prototype),
        prob_sparse.f.jac_prototype isa AbstractSparseMatrix ?
        "  nnz=$(nnz(prob_sparse.f.jac_prototype))" : "")

function timed_solve(prob, alg, label)
    solve(prob, alg; abstol = 1e-6, maxiters = 200)               # warm up JIT
    s, dt = @timed solve(prob, alg; abstol = 1e-6, maxiters = 200)
    println(rpad(label, 34), rpad(round(dt, digits = 5), 12), s.retcode)
end

println("\nconfig                            warm[s]     retcode")
timed_solve(prob_dense,  NewtonRaphson(),                         "dense jac, default linsolve")
timed_solve(prob_sparse, NewtonRaphson(),                         "sparse jac, default linsolve")
timed_solve(prob_sparse, NewtonRaphson(linsolve=KLUFactorization()),     "sparse jac, KLU")
timed_solve(prob_sparse, NewtonRaphson(linsolve=UMFPACKFactorization()), "sparse jac, UMFPACK")
