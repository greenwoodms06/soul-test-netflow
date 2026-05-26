within NetflowModelica.Components;

model FrictionPipe
  "Quadratic friction pressure-drop pipe: Δp = K · ṁ · |ṁ|.

   Adiabatic — h is passed through (port-to-port) without modification.
   Mass balance steady (no storage). The Jacobian ∂(K·ṁ·|ṁ|)/∂ṁ = 2·K·|ṁ|
   is SINGULAR at ṁ=0 — the case netflow had to special-case for its
   Darcy-Weisbach edge.

   DEBT: constant K. Real Darcy-Weisbach has K = f·L/(D·2·ρ·A²) with f
   from a Colebrook/Haaland correlation; constant K is a pre-design proxy.
  "
  replaceable package Medium = Modelica.Media.Water.StandardWater
    constrainedby Modelica.Media.Interfaces.PartialMedium;

  parameter Real K(final unit = "Pa.s2/kg2") = 1.0e8
    "Quadratic-friction coefficient: Δp = K·ṁ·|ṁ|";

  Modelica.Fluid.Interfaces.FluidPort_a port_a(redeclare package Medium = Medium);
  Modelica.Fluid.Interfaces.FluidPort_b port_b(redeclare package Medium = Medium);
equation
  // mass balance — steady
  port_a.m_flow + port_b.m_flow = 0;

  // momentum: quadratic friction
  port_a.p - port_b.p = K * port_a.m_flow * abs(port_a.m_flow);

  // adiabatic enthalpy passthrough (each port emits what the OTHER side received)
  port_a.h_outflow = inStream(port_b.h_outflow);
  port_b.h_outflow = inStream(port_a.h_outflow);

  // pure water — no Xi/C
  port_a.Xi_outflow = zeros(Medium.nXi);
  port_b.Xi_outflow = zeros(Medium.nXi);
  port_a.C_outflow = zeros(Medium.nC);
  port_b.C_outflow = zeros(Medium.nC);
end FrictionPipe;
