within NetflowModelica.Components;

model FuelPinDynPower
  "Series-resistance fuel pin with SIGNAL-DRIVEN power (RealInput Q_flow_in).

   Identical thermal topology to FuelPinConst — pellet (analytic) + gap
   (constant h_gap) + clad (cylindrical conduction) — but the centerline
   power is a time-varying signal rather than a parameter. Used by step
   3b for pin-by-pin neutronics-feedback assemblies.

   Exposes:
     Q_flow_in  : RealInput        — instantaneous centerline power (W)
     clad_outer : HeatPort_b       — external coupling (typically to coolant)
     T_centerline_K              : monitor output (K), for feedback to kinetics

   Same convention as FuelPinConst: positive Q_flow injects heat at centerline.
  "
  import Modelica.Constants.pi;
  import Modelica.Units.SI;

  parameter SI.Radius r_pellet = 4.096e-3 "Pellet outer radius";
  parameter SI.Length gap_thickness = 0.084e-3 "Radial gap (pellet OR -> clad IR)";
  parameter SI.Radius r_clad_outer = 4.75e-3 "Clad outer radius";
  parameter SI.Length L = 1.0 "Active length";

  parameter SI.ThermalConductivity k_fuel = 3.0 "Constant pellet thermal conductivity";
  parameter SI.ThermalConductivity k_clad = 16.0 "Constant clad thermal conductivity";
  parameter SI.CoefficientOfHeatTransfer h_gap = 7500.0
    "Gap conductance (VERA P6 empirical value)";

  final parameter SI.Radius r_clad_inner = r_pellet + gap_thickness;

  final parameter SI.ThermalResistance R_pellet = 1.0 / (4.0 * pi * k_fuel * L);
  final parameter SI.ThermalResistance R_gap =
    1.0 / (2.0 * pi * r_pellet * h_gap * L);
  final parameter SI.ThermalResistance R_clad =
    Modelica.Math.log(r_clad_outer / r_clad_inner) / (2.0 * pi * k_clad * L);

  Modelica.Blocks.Interfaces.RealInput Q_flow_in
    "Time-varying centerline power [W]";
  Modelica.Thermal.HeatTransfer.Sources.PrescribedHeatFlow src;
  Modelica.Thermal.HeatTransfer.Components.ThermalResistor Rf(R = R_pellet);
  Modelica.Thermal.HeatTransfer.Components.ThermalResistor Rg(R = R_gap);
  Modelica.Thermal.HeatTransfer.Components.ThermalResistor Rc(R = R_clad);

  Modelica.Thermal.HeatTransfer.Interfaces.HeatPort_b clad_outer;

  Modelica.Thermal.HeatTransfer.Sensors.TemperatureSensor T_centerline_sens;
  SI.Temperature T_centerline_K = T_centerline_sens.T;
equation
  src.Q_flow = Q_flow_in;
  connect(src.port, Rf.port_a);
  connect(Rf.port_b, Rg.port_a);
  connect(Rg.port_b, Rc.port_a);
  connect(Rc.port_b, clad_outer);
  connect(T_centerline_sens.port, src.port);
end FuelPinDynPower;
