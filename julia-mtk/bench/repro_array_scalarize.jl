# Minimal repro: is MTK's array-equation handling vectorized (O(1) compile) or
# scalarized (compile grows with N)? Research says scalarization is the current
# state (vectorized array-equation codegen is roadmap: MTK blog "we aim to allow
# simplification without requiring scalarization" + Reactant.jl, future tense).
# This confirms it empirically: a SINGLE array equation on array variables, compile
# time vs N. Superlinear growth ⇒ scalarized (the equation is expanded to N scalars).

using ModelingToolkit, NonlinearSolve
using ModelingToolkit: t_nounits as t

function build(N)
    @variables u(t)[1:N]
    # one nonlinear array equation (nonlinear so it can't be symbolically eliminated)
    # discrete nonlinear Laplace: 0 = u[i-1] - 2u[i] + u[i+1] + 0.1·u[i]^2 (interior)
    interior = u[1:N-2] .- 2 .* u[2:N-1] .+ u[3:N] .+ 0.1 .* u[2:N-1] .^ 2
    eqs = [u[1] ~ 1.0, u[N] ~ 0.0, interior ~ zeros(N - 2)]   # 3 "equations", one is an array eq
    @named sys = System(eqs, t)
    return mtkcompile(sys)
end

function timeit(N)
    GC.gc()
    sys, t_compile = @timed build(N)
    return (; nu = length(unknowns(sys)), neq = length(equations(sys)), t_compile)
end

timeit(20)  # warm up
println(rpad("N", 8), rpad("unknowns", 10), rpad("equations", 11), "compile[s]")
for N in (100, 300, 1000, 3000)
    r = timeit(N)
    println(rpad(N, 8), rpad(r.nu, 10), rpad(r.neq, 11), round(r.t_compile, digits = 3))
end
println("\nIf unknowns≈N and compile grows superlinearly ⇒ the array equation was SCALARIZED.")
