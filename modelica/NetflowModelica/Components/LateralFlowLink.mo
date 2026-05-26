within NetflowModelica.Components;

model LateralFlowLink
  "Two-port linear-flow link for subchannel cross-flow (MSL primitives only).

   Closes the under-determination that AssemblyVeraP6Subchannel hits when
   adjacent cells are connected directly — without a pressure-drop relation,
   lateral m_flow is structurally singular. This element provides:

     m_flow = G * (port_a.p - port_b.p)

   with G [kg/(s·Pa)] a tunable parameter. Steady-state; no momentum
   integration; just a linear algebraic relation. Bidirectional (flow
   reverses if pressure differential reverses).

   Energy carried via stream-connector pass-through (inStream() on each side).

   This is the slice-4 'no momentum' choice generalized to lateral flow:
   uses the simplest closure that gives a well-posed solve.
  "
  replaceable package Medium = Modelica.Media.Water.StandardWater
    constrainedby Modelica.Media.Interfaces.PartialMedium;

  parameter Real G(unit = "kg/(s.Pa)") = 1e-5
    "Linear flow conductance: m_flow = G * (p_a - p_b)";

  Modelica.Fluid.Interfaces.FluidPort_a port_a(redeclare package Medium = Medium);
  Modelica.Fluid.Interfaces.FluidPort_b port_b(redeclare package Medium = Medium);
equation
  // Mass balance
  port_a.m_flow + port_b.m_flow = 0;
  // Linear pressure-drop relation
  port_a.m_flow = G * (port_a.p - port_b.p);
  // Stream pass-through: enthalpy flows with the m_flow direction
  port_a.h_outflow = inStream(port_b.h_outflow);
  port_b.h_outflow = inStream(port_a.h_outflow);
  port_a.Xi_outflow = inStream(port_b.Xi_outflow);
  port_b.Xi_outflow = inStream(port_a.Xi_outflow);
  port_a.C_outflow = inStream(port_b.C_outflow);
  port_b.C_outflow = inStream(port_a.C_outflow);
end LateralFlowLink;
