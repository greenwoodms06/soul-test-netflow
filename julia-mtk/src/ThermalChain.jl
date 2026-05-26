# ThermalChain — acausal thermal-fluid components for the fuel-channel→coolant→loop
# dogfood (MTK v11). See docs/adr/0001 for the abstraction layer.
#
# Components (proven in test/slice1, slice2):
#   FluidPort      — Modelica-style stream connector (m_flow Flow + h_outflow Stream)
#   CoolantCell    — steady well-mixed single-phase cell, instream() upwind energy
#   MassFlowInlet  — prescribes ṁ and inlet enthalpy
#   PressureOutlet — prescribes p (and backflow enthalpy, unused on forward flow)
#   radial_resistances — textbook fuel-pin series resistances from geometry+props
#
# Standing limits (greppable):
# DEBT: forward-flow only; constant cp single-phase; no momentum/pressure-drop.
module ThermalChain

using ModelingToolkit
using ModelingToolkitStandardLibrary.Thermal
using ModelingToolkit: t_nounits as t, D_nounits as D
using ModelingToolkit: instream, Flow, Stream

export FluidPort, CoolantCell, CoolantCellDyn, MassFlowInlet, PressureOutlet, radial_resistances

@connector function FluidPort(; name)
    vars = @variables begin
        p(t), [guess = 15.5e6]
        m_flow(t), [guess = 0.0, connect = Flow]
        h_outflow(t), [guess = 1.2e6, connect = Stream]
    end
    System(Equation[], t, vars, []; name)
end

function CoolantCell(; name, cp = 5500.0, T_ref = 273.15)
    @named port_a = FluidPort()
    @named port_b = FluidPort()
    @named heat   = HeatPort()
    ps   = @parameters cp=cp T_ref=T_ref
    vars = @variables h(t) T(t) Q(t)
    eqs = [
        port_a.m_flow + port_b.m_flow ~ 0,
        port_a.h_outflow ~ h,
        port_b.h_outflow ~ h,
        h ~ cp * (T - T_ref),
        Q ~ heat.Q_flow,
        heat.T ~ T,
        port_a.p ~ port_b.p,
        port_a.m_flow * instream(port_a.h_outflow) + port_b.m_flow * port_b.h_outflow + Q ~ 0,
    ]
    System(eqs, t, vars, ps; name, systems = [port_a, port_b, heat])
end

# transient variant: adds fluid energy storage M·dh/dt (M = coolant mass in cell)
function CoolantCellDyn(; name, cp = 5500.0, T_ref = 273.15, M = 0.03)
    @named port_a = FluidPort()
    @named port_b = FluidPort()
    @named heat   = HeatPort()
    ps   = @parameters cp=cp T_ref=T_ref M=M
    vars = @variables h(t) T(t) Q(t)
    eqs = [
        port_a.m_flow + port_b.m_flow ~ 0,
        port_a.h_outflow ~ h,
        port_b.h_outflow ~ h,
        h ~ cp * (T - T_ref),
        Q ~ heat.Q_flow,
        heat.T ~ T,
        port_a.p ~ port_b.p,
        M * D(h) ~ port_a.m_flow * instream(port_a.h_outflow) + port_b.m_flow * port_b.h_outflow + Q,
    ]
    System(eqs, t, vars, ps; name, systems = [port_a, port_b, heat])
end

function MassFlowInlet(; name, mdot = 0.3, h_in = 1.2e6)
    @named port = FluidPort()
    ps = @parameters mdot=mdot h_in=h_in
    eqs = [port.m_flow ~ -mdot, port.h_outflow ~ h_in]
    System(eqs, t, [], ps; name, systems = [port])
end

function PressureOutlet(; name, p_set = 15.5e6, h_amb = 1.2e6)
    @named port = FluidPort()
    ps = @parameters p_set=p_set h_amb=h_amb
    eqs = [port.p ~ p_set, port.h_outflow ~ h_amb]
    System(eqs, t, [], ps; name, systems = [port])
end

"""
    radial_resistances(; r_pellet, r_ci, r_co, L, k_fuel, k_clad, h_gap, h_conv)

Textbook fuel-pin series thermal resistances [K/W] from coolant to centerline.
Fuel uses the solid-cylinder uniform-generation effective resistance 1/(4π k L).
"""
function radial_resistances(; r_pellet, r_ci, r_co, L, k_fuel, k_clad, h_gap, h_conv)
    R_fuel = 1 / (4π * k_fuel * L)
    R_gap  = 1 / (2π * r_pellet * h_gap * L)
    R_clad = log(r_co / r_ci) / (2π * k_clad * L)
    R_conv = 1 / (2π * r_co * h_conv * L)
    (; R_fuel, R_gap, R_clad, R_conv, R_tot = R_fuel + R_gap + R_clad + R_conv)
end

end # module
