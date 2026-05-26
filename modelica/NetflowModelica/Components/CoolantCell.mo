within NetflowModelica.Components;

model CoolantCell
  "Single-phase steady well-mixed coolant cell with stream-connector ports.

   - state variable: specific enthalpy h
   - thermodynamic state from (p, h) via the Medium (IF97 by default)
   - upwind enthalpy via Modelica's actualStream() — symmetric in flow direction
   - heat exchanges with the wall via HeatPort 'heat'

   Forward and backward flow are both correct via actualStream(); the netflow /
   Julia variants used a one-sided upwind because their stacks only ran forward.

   Storage is added in CoolantCellDyn for transient slices (5/6).
  "
  replaceable package Medium = Modelica.Media.Water.StandardWater
    constrainedby Modelica.Media.Interfaces.PartialMedium;

  parameter Medium.AbsolutePressure p_start = 15.5e6 "Nominal/start pressure";
  parameter Medium.Temperature T_start = 593.0 "Start temperature for h_start";
  final parameter Medium.SpecificEnthalpy h_start =
    Medium.specificEnthalpy_pT(p_start, T_start) "Start enthalpy";

  Modelica.Fluid.Interfaces.FluidPort_a port_a(redeclare package Medium = Medium);
  Modelica.Fluid.Interfaces.FluidPort_b port_b(redeclare package Medium = Medium);
  Modelica.Thermal.HeatTransfer.Interfaces.HeatPort_a heat;

  Medium.SpecificEnthalpy h(start = h_start);
  Medium.Temperature T;
  Medium.AbsolutePressure p;
  Modelica.Units.SI.HeatFlowRate Q;

  Medium.ThermodynamicState state;
equation
  // mass balance (steady — no storage)
  port_a.m_flow + port_b.m_flow = 0;

  // pressure equal across the cell (no momentum)
  port_a.p = p;
  port_b.p = p;

  // both ports send h as their outflow enthalpy
  port_a.h_outflow = h;
  port_b.h_outflow = h;

  // pure water → no mass fractions / trace constituents
  port_a.Xi_outflow = zeros(Medium.nXi);
  port_b.Xi_outflow = zeros(Medium.nXi);
  port_a.C_outflow = zeros(Medium.nC);
  port_b.C_outflow = zeros(Medium.nC);

  // thermodynamic state from (p, h)
  state = Medium.setState_phX(p, h, fill(0.0, Medium.nXi));
  T = Medium.temperature(state);

  // wall heat coupling
  heat.T = T;
  Q = heat.Q_flow;

  // energy balance (steady): enthalpy in/out + wall heat = 0
  port_a.m_flow * actualStream(port_a.h_outflow)
    + port_b.m_flow * actualStream(port_b.h_outflow)
    + Q = 0;
end CoolantCell;
