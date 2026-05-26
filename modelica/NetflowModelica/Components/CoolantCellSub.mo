within NetflowModelica.Components;

model CoolantCellSub
  "Coolant cell with axial + 4 lateral FluidPorts (subchannel cross-flow).

   Same physics as CoolantCell (single-phase, steady, well-mixed, no momentum)
   but exposes 4 lateral stream-connector ports — port_lat_xL/xR for left/right
   neighbours and port_lat_yU/yD for upper/lower neighbours in the 17x17 grid.
   Mass and energy balance over all 6 ports (2 axial + 4 lateral).

   Topology assumption: pressure equal across all ports (well-mixed cell);
   lateral flow is determined by adjacent cells' inlet imbalance + connect()
   constraints. No momentum equation here — that is the slice-4 choice
   carried forward to lateral transport.

   Used by AssemblyVeraP6Subchannel for step 3c of the unfreeze.
  "
  replaceable package Medium = Modelica.Media.Water.StandardWater
    constrainedby Modelica.Media.Interfaces.PartialMedium;

  parameter Medium.AbsolutePressure p_start = 15.5e6;
  parameter Medium.Temperature T_start = 593.0;
  final parameter Medium.SpecificEnthalpy h_start =
    Medium.specificEnthalpy_pT(p_start, T_start);

  Modelica.Fluid.Interfaces.FluidPort_a port_a(redeclare package Medium = Medium);
  Modelica.Fluid.Interfaces.FluidPort_b port_b(redeclare package Medium = Medium);
  // 4 lateral ports: xL ↔ left neighbour, xR ↔ right neighbour, yU ↔ upper,
  // yD ↔ lower (or whatever the assembly's grid convention is).
  Modelica.Fluid.Interfaces.FluidPort_b port_lat_xL(redeclare package Medium = Medium);
  Modelica.Fluid.Interfaces.FluidPort_b port_lat_xR(redeclare package Medium = Medium);
  Modelica.Fluid.Interfaces.FluidPort_b port_lat_yU(redeclare package Medium = Medium);
  Modelica.Fluid.Interfaces.FluidPort_b port_lat_yD(redeclare package Medium = Medium);
  Modelica.Thermal.HeatTransfer.Interfaces.HeatPort_a heat;

  Medium.SpecificEnthalpy h(start = h_start);
  Medium.Temperature T;
  Medium.AbsolutePressure p;
  Modelica.Units.SI.HeatFlowRate Q;

  Medium.ThermodynamicState state;
equation
  // Mass balance: sum over all 6 ports = 0 (no storage)
  port_a.m_flow + port_b.m_flow
    + port_lat_xL.m_flow + port_lat_xR.m_flow
    + port_lat_yU.m_flow + port_lat_yD.m_flow = 0;

  // Pressure equal across all 6 ports
  port_a.p = p;
  port_b.p = p;
  port_lat_xL.p = p;
  port_lat_xR.p = p;
  port_lat_yU.p = p;
  port_lat_yD.p = p;

  // All ports send h as outflow enthalpy
  port_a.h_outflow = h;
  port_b.h_outflow = h;
  port_lat_xL.h_outflow = h;
  port_lat_xR.h_outflow = h;
  port_lat_yU.h_outflow = h;
  port_lat_yD.h_outflow = h;

  port_a.Xi_outflow = zeros(Medium.nXi);
  port_b.Xi_outflow = zeros(Medium.nXi);
  port_lat_xL.Xi_outflow = zeros(Medium.nXi);
  port_lat_xR.Xi_outflow = zeros(Medium.nXi);
  port_lat_yU.Xi_outflow = zeros(Medium.nXi);
  port_lat_yD.Xi_outflow = zeros(Medium.nXi);
  port_a.C_outflow = zeros(Medium.nC);
  port_b.C_outflow = zeros(Medium.nC);
  port_lat_xL.C_outflow = zeros(Medium.nC);
  port_lat_xR.C_outflow = zeros(Medium.nC);
  port_lat_yU.C_outflow = zeros(Medium.nC);
  port_lat_yD.C_outflow = zeros(Medium.nC);

  state = Medium.setState_phX(p, h, fill(0.0, Medium.nXi));
  T = Medium.temperature(state);

  heat.T = T;
  Q = heat.Q_flow;

  // Energy balance: actualStream upwind enthalpy over all 6 ports + wall heat
  port_a.m_flow * actualStream(port_a.h_outflow)
    + port_b.m_flow * actualStream(port_b.h_outflow)
    + port_lat_xL.m_flow * actualStream(port_lat_xL.h_outflow)
    + port_lat_xR.m_flow * actualStream(port_lat_xR.h_outflow)
    + port_lat_yU.m_flow * actualStream(port_lat_yU.h_outflow)
    + port_lat_yD.m_flow * actualStream(port_lat_yD.h_outflow)
    + Q = 0;
end CoolantCellSub;
