within NetflowModelica.Components;

model CoolantOutlet
  "Pressure boundary at a single FluidPort.

   Pins p; supplies an ambient enthalpy that is used only on backflow.
   On forward flow the outlet absorbs whatever h the upstream component sends.
  "
  replaceable package Medium = Modelica.Media.Water.StandardWater
    constrainedby Modelica.Media.Interfaces.PartialMedium;

  parameter Medium.AbsolutePressure p_set = 15.5e6 "Outlet pressure";
  parameter Medium.Temperature T_ambient = 593.0
    "Backflow enthalpy reference (unused under forward flow)";
  final parameter Medium.SpecificEnthalpy h_ambient =
    Medium.specificEnthalpy_pT(p_set, T_ambient);

  Modelica.Fluid.Interfaces.FluidPort_a port(redeclare package Medium = Medium);
equation
  port.p = p_set;
  port.h_outflow = h_ambient;
  port.Xi_outflow = zeros(Medium.nXi);
  port.C_outflow = zeros(Medium.nC);
end CoolantOutlet;
