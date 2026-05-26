within NetflowModelica.Components;

model CoolantInlet
  "Prescribes mass-flow + inlet conditions (T, p) at a single FluidPort.

   Computes the inlet enthalpy from (p, T) via the Medium. Sign convention:
   port.m_flow < 0 means the inlet ejects fluid into the downstream network.
  "
  replaceable package Medium = Modelica.Media.Water.StandardWater
    constrainedby Modelica.Media.Interfaces.PartialMedium;

  parameter Modelica.Units.SI.MassFlowRate mdot = 0.30
    "Mass flow rate INTO the downstream network (must be positive)";
  parameter Medium.AbsolutePressure p_ref = 15.5e6
    "Reference pressure used only to evaluate the inlet enthalpy from T_in
     (does NOT pin the network pressure — outlet sets that)";
  parameter Medium.Temperature T_in = 593.0 "Inlet temperature";
  final parameter Medium.SpecificEnthalpy h_in =
    Medium.specificEnthalpy_pT(p_ref, T_in);

  Modelica.Fluid.Interfaces.FluidPort_b port(redeclare package Medium = Medium);
equation
  assert(mdot > 0,
    "CoolantInlet.mdot must be > 0; reverse the connection if backflow is intended.");
  port.m_flow = -mdot;
  port.h_outflow = h_in;
  port.Xi_outflow = zeros(Medium.nXi);
  port.C_outflow = zeros(Medium.nC);
end CoolantInlet;
