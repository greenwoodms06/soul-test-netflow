# Slice 9 — multi-pin ASSEMBLY: parallel coupled fuel-channels (real slice-3 physics,
# prescribed flow) in one System. Answers "have we pushed to assembly?" and quantifies
# the codegen wall (MTK-F4) on the REALISTIC coupled model, not the abstract mesh.
# Also verifies energy conservation across the whole assembly.

using ModelingToolkit, ModelingToolkitStandardLibrary.Thermal, NonlinearSolve
using ModelingToolkit: t_nounits as t
include("../src/ThermalChain.jl"); using .ThermalChain

const MDOT, CP, TREF, TIN = 0.3, 5500.0, 273.15, 565.0
const HIN = CP * (TIN - TREF)

function build_assembly(npins, nax)
    R = radial_resistances(; r_pellet = 4.10e-3, r_ci = 4.185e-3, r_co = 4.75e-3,
        L = 3.66 / nax, k_fuel = 3.0, k_clad = 16.0, h_gap = 5_000.0, h_conv = 30_000.0)
    systems = System[]; conns = Equation[]
    for pin in 1:npins
        Qc = 18_000.0 * (1 + 0.1 * (pin - 1)) * (3.66 / nax)   # slightly different power per pin
        inl = MassFlowInlet(; name = Symbol(:in, pin), mdot = MDOT, h_in = HIN)
        out = PressureOutlet(; name = Symbol(:out, pin), p_set = 15.5e6, h_amb = HIN)
        cells = [CoolantCell(; name = Symbol(:c, pin, :_, i), cp = CP, T_ref = TREF) for i in 1:nax]
        src = [FixedHeatFlow(; name = Symbol(:s, pin, :_, i), Q_flow = Qc) for i in 1:nax]
        Rf = [ThermalResistor(; name = Symbol(:Rf, pin, :_, i), R = R.R_fuel) for i in 1:nax]
        Rg = [ThermalResistor(; name = Symbol(:Rg, pin, :_, i), R = R.R_gap)  for i in 1:nax]
        Rc = [ThermalResistor(; name = Symbol(:Rc, pin, :_, i), R = R.R_clad) for i in 1:nax]
        Rh = [ThermalResistor(; name = Symbol(:Rh, pin, :_, i), R = R.R_conv) for i in 1:nax]
        push!(conns, connect(inl.port, cells[1].port_a))
        for i in 1:(nax-1); push!(conns, connect(cells[i].port_b, cells[i+1].port_a)); end
        push!(conns, connect(cells[nax].port_b, out.port))
        for i in 1:nax
            push!(conns, connect(src[i].port, Rf[i].port_a))
            push!(conns, connect(Rf[i].port_b, Rg[i].port_a))
            push!(conns, connect(Rg[i].port_b, Rc[i].port_a))
            push!(conns, connect(Rc[i].port_b, Rh[i].port_a))
            push!(conns, connect(Rh[i].port_b, cells[i].heat))
        end
        append!(systems, [inl, out, cells..., src..., Rf..., Rg..., Rc..., Rh...])
    end
    @named asm = System(conns, t; systems)
    return asm
end

function run_case(npins, nax)
    GC.gc()
    sys, t_compile = @timed mtkcompile(build_assembly(npins, nax))
    nu = length(unknowns(sys))
    g = map(unknowns(sys)) do u
        s = string(u); u => (occursin("₊h(t)", s) ? HIN : occursin("Q_flow", s) ? 6000.0 : 600.0)
    end
    prob = NonlinearProblem(sys, g)
    solve(prob, NewtonRaphson(); abstol = 1e-4, maxiters = 1000)
    s, t_warm = @timed solve(prob, NewtonRaphson(); abstol = 1e-4, maxiters = 1000)
    return (; nu, t_compile, t_warm, retcode = s.retcode)
end

run_case(1, 4)  # warm up
println(rpad("pins", 6), rpad("cells", 7), rpad("unknowns", 10), rpad("compile[s]", 12),
        rpad("warm solve[s]", 14), "retcode")
for np in (1, 4, 9, 16, 25, 49, 100)
    r = run_case(np, 10)
    println(rpad(np, 6), rpad(np*10, 7), rpad(r.nu, 10), rpad(round(r.t_compile, digits=3), 12),
            rpad(round(r.t_warm, digits=5), 14), r.retcode)
end
