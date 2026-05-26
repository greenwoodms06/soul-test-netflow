# One bounded attempt: can MTK array variables keep mtkcompile fast (loop codegen)
# instead of the unrolled per-component blowup? 1D nonlinear conduction chain via
# array-variable broadcast equations. If mtkcompile stays cheap at large N, MTK gets
# convenience AND scale; if it explodes/scalarizes, the array-symbolic fix is not
# turnkey (a finding either way).

using ModelingToolkit, NonlinearSolve
using ModelingToolkit: t_nounits as t

function build_arraysym(N)
    @variables T(t)[1:N]
    # keep T as a symbolic ARRAY (no collect) so slices stay vectorized
    Tm   = (T[1:N-1] .+ T[2:N]) ./ 2
    flux = (10.0 .+ 0.005 .* Tm) .* (T[2:N] .- T[1:N-1])       # symbolic array, len N-1
    interior = flux[2:N-1] .- flux[1:N-2]                      # symbolic array, len N-2
    eqs = [T[1] ~ 1000.0, T[N] ~ 300.0, interior ~ zeros(N - 2)]  # single array equation
    @named sys = System(eqs, t)
    return sys
end

function run_case(N)
    GC.gc()
    sys, t_compile = @timed mtkcompile(build_arraysym(N))
    nu = length(unknowns(sys))
    return (; nu, t_compile)
end

run_case(50)  # warm up
println(rpad("N", 8), rpad("unknowns", 10), "compile[s]")
for N in (1000, 5000, 20000)
    r = run_case(N)
    println(rpad(N, 8), rpad(r.nu, 10), round(r.t_compile, digits = 3))
end
