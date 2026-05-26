# Performance axis — MTK scaling for the coupled fuel-channel→coolant chain.
#
# Measures the TWO distinct costs separately, because MTK's cost model differs
# fundamentally from netflow's: mtkcompile is SYMBOLIC (build the equations once),
# solve is NUMERIC. netflow has no symbolic stage — it hand-assembles sparse
# matrices, so its cost is all in assembly+factorization. The honest comparison is
# the trend, not a single number. Constant properties (linear) for a clean scaling
# signal; structure matches slice 3.

using ModelingToolkit, ModelingToolkitStandardLibrary.Thermal, NonlinearSolve
using ModelingToolkit: t_nounits as t
include("../src/ThermalChain.jl"); using .ThermalChain

# build the uncompiled coupled chain with N axial cells (each cell: a fuel-pin
# radial stack feeding that cell's coolant), single channel.
function build_chain(N)
    mdot, cp, T_ref, T_in = 0.3, 5500.0, 273.15, 565.0
    h_in = cp * (T_in - T_ref)
    R = radial_resistances(; r_pellet = 4.10e-3, r_ci = 4.185e-3, r_co = 4.75e-3,
        L = 3.66 / N, k_fuel = 3.0, k_clad = 16.0, h_gap = 5_000.0, h_conv = 30_000.0)
    Q_cell = 18_000.0 * (3.66 / N)

    @named inlet  = MassFlowInlet(mdot = mdot, h_in = h_in)
    @named outlet = PressureOutlet(p_set = 15.5e6, h_amb = h_in)
    cells = [CoolantCell(; name = Symbol(:cell, i), cp = cp, T_ref = T_ref) for i in 1:N]
    src = [FixedHeatFlow(; name = Symbol(:src, i), Q_flow = Q_cell) for i in 1:N]
    Rf = [ThermalResistor(; name = Symbol(:Rf, i), R = R.R_fuel) for i in 1:N]
    Rg = [ThermalResistor(; name = Symbol(:Rg, i), R = R.R_gap)  for i in 1:N]
    Rc = [ThermalResistor(; name = Symbol(:Rc, i), R = R.R_clad) for i in 1:N]
    Rh = [ThermalResistor(; name = Symbol(:Rh, i), R = R.R_conv) for i in 1:N]

    conns = Equation[]
    push!(conns, connect(inlet.port, cells[1].port_a))
    for i in 1:(N - 1)
        push!(conns, connect(cells[i].port_b, cells[i + 1].port_a))
    end
    push!(conns, connect(cells[N].port_b, outlet.port))
    for i in 1:N
        push!(conns, connect(src[i].port, Rf[i].port_a))
        push!(conns, connect(Rf[i].port_b, Rg[i].port_a))
        push!(conns, connect(Rg[i].port_b, Rc[i].port_a))
        push!(conns, connect(Rc[i].port_b, Rh[i].port_a))
        push!(conns, connect(Rh[i].port_b, cells[i].heat))
    end
    @named chain = System(conns, t; systems = vcat(inlet, outlet, cells, src, Rf, Rg, Rc, Rh))
    return chain, h_in, Q_cell
end

function run_case(N; h_in, Q_cell, chain)
    t_compile = @elapsed (sys = mtkcompile(chain))
    nu = length(unknowns(sys))
    guesses = map(unknowns(sys)) do u
        s = string(u)
        u => (occursin("₊h(t)", s) ? h_in : occursin("Q_flow", s) ? Q_cell : 600.0)
    end
    prob = NonlinearProblem(sys, guesses)
    # cold solve includes Julia JIT of the generated residual/Jacobian (per shape);
    # warm solve is the true numeric cost (amortized when solved repeatedly, e.g.
    # transient). netflow has no JIT stage — so the warm solve is the fair compare.
    t_cold = @elapsed (sol = solve(prob, NewtonRaphson(); abstol = 1e-4, maxiters = 1000))
    t_warm = @elapsed solve(prob, NewtonRaphson(); abstol = 1e-4, maxiters = 1000)
    return (; nu, t_compile, t_cold, t_warm, retcode = sol.retcode)
end

let (c, h, q) = build_chain(3); run_case(3; h_in = h, Q_cell = q, chain = c); end

println(rpad("N_axial", 9), rpad("unknowns", 10), rpad("compile[s]", 12),
        rpad("solve_cold[s]", 14), rpad("solve_warm[s]", 14), "retcode")
for N in (10, 30, 100, 300)
    chain, h_in, Q_cell = build_chain(N)
    r = run_case(N; h_in, Q_cell, chain)
    println(rpad(N, 9), rpad(r.nu, 10), rpad(round(r.t_compile, digits = 3), 12),
            rpad(round(r.t_cold, digits = 3), 14), rpad(round(r.t_warm, digits = 6), 14), r.retcode)
end
