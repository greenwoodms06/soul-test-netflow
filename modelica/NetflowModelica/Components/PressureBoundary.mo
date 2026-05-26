within NetflowModelica.Components;

model PressureBoundary
  "FluidPort source pinning pressure (and a backflow enthalpy reference).

   Distinct from CoolantOutlet only in convention: use this in momentum
   networks where 'inlet' and 'outlet' are both pressure boundaries (slice 8).
  "
  replaceable package Medium = Modelica.Media.Water.StandardWater
    constrainedby Modelica.Media.Interfaces.PartialMedium;

  parameter Medium.AbsolutePressure p_set = 1.0e5;
  parameter Medium.Temperature T_ref = 593.0
    "Reference T used to compute the backflow h_outflow";
  final parameter Medium.SpecificEnthalpy h_set =
    Medium.specificEnthalpy_pT(p_set, T_ref);

  Modelica.Fluid.Interfaces.FluidPort_a port(redeclare package Medium = Medium);
equation
  port.p = p_set;
  port.h_outflow = h_set;
  port.Xi_outflow = zeros(Medium.nXi);
  port.C_outflow = zeros(Medium.nC);
end PressureBoundary;
