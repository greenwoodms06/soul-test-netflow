# Is JULIA fast at scale, independent of MTK's codegen? Same nonlinear 2D mesh, but
# the residual is a hand-written LOOP (O(1) code → JITs instantly), solved with
# colored sparse AD + KLU. This isolates Julia's numeric performance from MTK's
# giant-unrolled-function compilation. Swept at netflow's exact sizes.
# netflow (re-measured): 10k 0.11s solve / 0.14s total; 40k 0.63/0.76; 90k 1.5/1.9.

using NonlinearSolve, LinearSolve, SparseArrays
using ADTypes, SparseConnectivityTracer, SparseMatrixColorings

function mesh_residual!(F, T, M)
    @inbounds for i in 1:M, j in 1:M
        c = (i - 1) * M + j
        if j == 1
            F[c] = T[c] - 1000.0
        elseif j == M
            F[c] = T[c] - 300.0
        else
            acc = 0.0
            for nidx in ((i - 1) * M + (j - 1), (i - 1) * M + (j + 1))
                acc += (10.0 + 0.005 * (T[c] + T[nidx])) * (T[nidx] - T[c])
            end
            if i > 1
                nidx = (i - 2) * M + j
                acc += (10.0 + 0.005 * (T[c] + T[nidx])) * (T[nidx] - T[c])
            end
            if i < M
                nidx = i * M + j
                acc += (10.0 + 0.005 * (T[c] + T[nidx])) * (T[nidx] - T[c])
            end
            F[c] = acc
        end
    end
    return nothing
end

function run_case(M)
    GC.gc()
    n = M * M
    u0 = fill(650.0, n)
    res!(F, u) = mesh_residual!(F, u, M)
    jp, t_detect = @timed jacobian_sparsity(res!, similar(u0), u0, TracerSparsityDetector())
    colvec, t_color = @timed column_colors(coloring(jp, ColoringProblem(), GreedyColoringAlgorithm()))
    nf = NonlinearFunction((F, u, p) -> mesh_residual!(F, u, M);
                           jac_prototype = Float64.(jp), colorvec = colvec)
    prob = NonlinearProblem(nf, u0)
    alg = NewtonRaphson(linsolve = KLUFactorization())
    s_cold, t_cold = @timed solve(prob, alg; abstol = 1e-6, maxiters = 200)
    s, t_warm = @timed solve(prob, alg; abstol = 1e-6, maxiters = 200)
    return (; n, ncol = maximum(colvec), t_detect, t_color, t_cold, t_warm, retcode = s.retcode)
end

run_case(6)  # warm up JIT (loop residual → fast)

println(rpad("nodes", 9), rpad("colors", 8), rpad("detect[s]", 11), rpad("color[s]", 10),
        rpad("cold[s]", 10), rpad("warm[s]", 11), "retcode")
for M in (32, 100, 200, 300)
    r = run_case(M)
    println(rpad(r.n, 9), rpad(r.ncol, 8), rpad(round(r.t_detect, digits = 4), 11),
            rpad(round(r.t_color, digits = 4), 10), rpad(round(r.t_cold, digits = 4), 10),
            rpad(round(r.t_warm, digits = 5), 11), r.retcode)
end
