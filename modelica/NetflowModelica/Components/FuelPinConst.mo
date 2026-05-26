within NetflowModelica.Components;

model FuelPinConst
  "Series-resistance fuel pin with CONSTANT thermal properties — slice 1 verification anchor.

   Models pellet (analytic 1/(4 pi k L) centerline-to-surface resistance for a
   solid cylinder with uniform volumetric generation) + gas gap (constant h_gap
   at the pellet surface) + clad (1-D radial cylindrical conduction). Constant
   k_fuel / k_clad / h_gap; T-dependent UO2/He/Zr closures come in slice 4.

   Exposes:
     clad_outer : HeatPort_b for external coupling (typically to the coolant).
     T_centerline_K, T_pellet_surface_K, T_clad_inner_K : monitor outputs (K).

   Convention: positive q_lin injects heat at the centerline.
  "
  import Modelica.Constants.pi;
  import Modelica.Units.SI;

  parameter SI.Radius r_pellet = 4.10e-3 "Pellet outer radius";
  parameter SI.Length gap_thickness = 0.085e-3 "Radial gap (pellet OR -> clad IR)";
  parameter SI.Radius r_clad_outer = 4.75e-3 "Clad outer radius";
  parameter SI.Length L = 1.0 "Active length";

  parameter Real q_lin(final unit = "W/m") = 18000.0
    "Linear power (total power into the centerline = q_lin * L)";

  parameter SI.ThermalConductivity k_fuel = 3.0 "Constant pellet thermal conductivity";
  parameter SI.ThermalConductivity k_clad = 16.0 "Constant clad thermal conductivity";
  parameter SI.CoefficientOfHeatTransfer h_gap = 5000.0
    "Constant gap conductance referenced at the pellet outer surface";

  final parameter SI.Radius r_clad_inner = r_pellet + gap_thickness
    "Derived clad inner radius";
  final parameter SI.Power Q_total = q_lin * L "Derived total injected power";

  // Series resistances [K/W]. Pellet uses the solid-cylinder uniform-generation
  // closed form: dT(centerline->surface) = q'''*r^2/(4k) with q_lin = pi r^2 q'''
  // gives R_pellet = 1/(4 pi k L).
  final parameter SI.ThermalResistance R_pellet = 1.0 / (4.0 * pi * k_fuel * L);
  final parameter SI.ThermalResistance R_gap =
    1.0 / (2.0 * pi * r_pellet * h_gap * L);
  final parameter SI.ThermalResistance R_clad =
    Modelica.Math.log(r_clad_outer / r_clad_inner) / (2.0 * pi * k_clad * L);

  Modelica.Thermal.HeatTransfer.Sources.FixedHeatFlow src(Q_flow = Q_total)
    "Power injected at the centerline";
  Modelica.Thermal.HeatTransfer.Components.ThermalResistor Rf(R = R_pellet)
    "Pellet centerline -> pellet surface";
  Modelica.Thermal.HeatTransfer.Components.ThermalResistor Rg(R = R_gap)
    "Pellet surface -> clad inner (gap conductance)";
  Modelica.Thermal.HeatTransfer.Components.ThermalResistor Rc(R = R_clad)
    "Clad inner -> clad outer (radial conduction)";

  Modelica.Thermal.HeatTransfer.Interfaces.HeatPort_b clad_outer
    "External coupling port (typically to forced convection)";

  Modelica.Thermal.HeatTransfer.Sensors.TemperatureSensor T_centerline_sens;
  Modelica.Thermal.HeatTransfer.Sensors.TemperatureSensor T_pellet_surface_sens;
  Modelica.Thermal.HeatTransfer.Sensors.TemperatureSensor T_clad_inner_sens;

  // Output aliases in Kelvin (clearer to read from .mat than the *_sens.T form)
  SI.Temperature T_centerline_K = T_centerline_sens.T;
  SI.Temperature T_pellet_surface_K = T_pellet_surface_sens.T;
  SI.Temperature T_clad_inner_K = T_clad_inner_sens.T;
  SI.Temperature T_clad_outer_K = clad_outer.T;
equation
  // Series wiring: centerline -> pellet -> gap -> clad -> clad_outer port
  connect(src.port, Rf.port_a);
  connect(Rf.port_b, Rg.port_a);
  connect(Rg.port_b, Rc.port_a);
  connect(Rc.port_b, clad_outer);

  // Passive sensors
  connect(T_centerline_sens.port, src.port);
  connect(T_pellet_surface_sens.port, Rg.port_a);
  connect(T_clad_inner_sens.port, Rc.port_a);
end FuelPinConst;
