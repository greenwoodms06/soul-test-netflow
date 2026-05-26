# Does MethodOfLines (the "recommended tool for discretized PDEs") escape the
# compile wall? Research said NO — Rackauckas (SciML lead): "MethodOfLines uses a
# scalarization which leads to long compile times"; community benchmark ~6000 s at
# 100×100. This EMPIRICALLY confirms it on this machine, at small grids (the trend),
# so the "you should've used MOL" advice can be answered with data.
#
# 2D transient heat (the canonical MOL tutorial). We measure DISCRETIZE (codegen)
# and first-solve time vs grid size — both should grow steeply (scalarized per point).

using OrdinaryDiffEqRosenbrock, ModelingToolkit, MethodOfLines, DomainSets

@parameters t x y
@variables u(..)
Dt = Differential(t); Dxx = Differential(x)^2; Dyy = Differential(y)^2

eq  = Dt(u(t, x, y)) ~ Dxx(u(t, x, y)) + Dyy(u(t, x, y))
bcs = [u(0, x, y) ~ 0.0,
       u(t, 0, y) ~ 1.0, u(t, 1, y) ~ 0.0,
       u(t, x, 0) ~ 1.0 - x, u(t, x, 1) ~ 1.0 - x]
domains = [t ∈ Interval(0.0, 0.05), x ∈ Interval(0.0, 1.0), y ∈ Interval(0.0, 1.0)]
@named pde = PDESystem(eq, bcs, domains, [t, x, y], [u(t, x, y)])

function run_case(n)
    GC.gc()
    dx = 1.0 / n
    disc = MOLFiniteDifference([x => dx, y => dx], t)
    prob, t_disc = @timed discretize(pde, disc)          # MOL codegen happens here
    npts = length(prob.u0)
    sol, t_cold = @timed solve(prob, Rosenbrock23(); saveat = 0.05)
    return (; npts, t_disc, t_cold, retcode = sol.retcode)
end

run_case(5)  # warm up the MOL machinery
println(rpad("grid", 8), rpad("interior pts", 14), rpad("discretize[s]", 15), rpad("1st solve[s]", 14), "retcode")
for n in (10, 20, 30, 40)
    r = run_case(n)
    println(rpad("$(n)×$(n)", 8), rpad(r.npts, 14), rpad(round(r.t_disc, digits = 2), 15),
            rpad(round(r.t_cold, digits = 2), 14), r.retcode)
end
