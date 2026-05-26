# Does COLORED sparse AD + sparse solve fix it? Take MTK's residual f + sparse
# jac_prototype, compute a column coloring, rebuild the NonlinearFunction with
# jac_prototype + colorvec (the piece MTK's sparse=true omits), solve with KLU.
# Colored AD needs ~#colors passes (≈5 for a 5-pt stencil) regardless of N.

using ModelingToolkit, NonlinearSolve, LinearSolve, SparseArrays, SparseMatrixColorings
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
g = [u => 650.0 for u in unknowns(sys)]
prob = NonlinearProblem(sys, g; sparse = true)
jp = prob.f.jac_prototype
res = coloring(jp, ColoringProblem(), GreedyColoringAlgorithm())
colvec = column_colors(res)
println("unknowns=$(length(g))  nnz=$(nnz(jp))  colors=$(maximum(colvec))")

f2 = NonlinearFunction{true}(prob.f.f; jac_prototype = jp, colorvec = colvec)
prob2 = NonlinearProblem(f2, prob.u0, prob.p)

function timeit(prob, alg, label)
    solve(prob, alg; abstol = 1e-6, maxiters = 200)
    s, dt = @timed solve(prob, alg; abstol = 1e-6, maxiters = 200)
    println(rpad(label, 40), rpad(round(dt, digits = 5), 12), s.retcode)
    return s
end

println("\nconfig                                  warm[s]     retcode")
timeit(prob,  NewtonRaphson(),                              "sparse jac_prototype, NO colorvec (default)")
timeit(prob2, NewtonRaphson(linsolve = KLUFactorization()),     "colored AD + KLU")
timeit(prob2, NewtonRaphson(linsolve = UMFPACKFactorization()), "colored AD + UMFPACK")
