within NetflowModelica.Tests;

model CoupledChain
  "Slice 3 test: full fuel-channel → coolant chain.

   N axial slices, each with its own FuelPinConst + constant-h convection
   resistor + CoolantCell. Coolant advects upstream → downstream.

   Verifies (computed in the Python driver):
     (a) energy closure: mdot * (h_out - h_in) == ΣQ_i  (all pin power lands
         in coolant; stream balance closes the loop)
     (b) per-pin radial drop: T_centerline_i = T_cell_i + Q_per_slice * R_tot

   Constant properties — matches the Julia slice 3 setup. T-dependent closures
   land in slice 4 / FuelPinTDep.
  "
  extends Modelica.Icons.Example;

  replaceable package Medium = Modelica.Media.Water.StandardWater
    constrainedby Modelica.Media.Interfaces.PartialMedium;

  parameter Integer n = 10 "Number of axial slices";
  parameter Modelica.Units.SI.Length L_total = 3.66 "Active fuel length";
  parameter Modelica.Units.SI.Length dz = L_total / n;

  parameter Modelica.Units.SI.MassFlowRate mdot = 0.30;
  parameter Modelica.Units.SI.Pressure p_nom = 15.5e6;
  parameter Modelica.Units.SI.Temperature T_in = 565.0;
  parameter Real q_lin(final unit = "W/m") = 18000.0;

  parameter Modelica.Units.SI.ThermalConductivity k_fuel = 3.0;
  parameter Modelica.Units.SI.ThermalConductivity k_clad = 16.0;
  parameter Modelica.Units.SI.CoefficientOfHeatTransfer h_gap = 5000.0;
  parameter Modelica.Units.SI.CoefficientOfHeatTransfer h_conv = 30000.0;

  // Pin geometry (netflow defaults)
  parameter Modelica.Units.SI.Radius r_pellet = 4.10e-3;
  parameter Modelica.Units.SI.Length gap_thickness = 0.085e-3;
  parameter Modelica.Units.SI.Radius r_clad_outer = 4.75e-3;
  final parameter Modelica.Units.SI.Radius r_clad_inner = r_pellet + gap_thickness;

  // External convection resistance per slice [K/W] (constant h_conv at r_clad_outer)
  final parameter Modelica.Units.SI.ThermalResistance R_conv =
    1.0 / (2.0 * Modelica.Constants.pi * r_clad_outer * h_conv * dz);

  Components.CoolantInlet inlet(
    redeclare package Medium = Medium,
    mdot = mdot, p_ref = p_nom, T_in = T_in);
  Components.CoolantOutlet outlet(
    redeclare package Medium = Medium,
    p_set = p_nom, T_ambient = T_in);

  Components.CoolantCell cells[n](
    redeclare each package Medium = Medium,
    each p_start = p_nom, each T_start = T_in);

  Components.FuelPinConst pins[n](
    each q_lin = q_lin,
    each L = dz,
    each r_pellet = r_pellet,
    each gap_thickness = gap_thickness,
    each r_clad_outer = r_clad_outer,
    each k_fuel = k_fuel,
    each k_clad = k_clad,
    each h_gap = h_gap);

  Modelica.Thermal.HeatTransfer.Components.ThermalResistor convs[n](
    each R = R_conv);

  // monitor outputs (per-slice T_cool for the radial-drop check)
  Modelica.Units.SI.Temperature T_cool[n] = {cells[i].T for i in 1:n};
  Modelica.Units.SI.Temperature T_centerline[n] = {pins[i].T_centerline_K for i in 1:n};
  Modelica.Units.SI.SpecificEnthalpy h_in_K = inlet.h_in;
  Modelica.Units.SI.SpecificEnthalpy h_out_K = cells[n].h;
  // total pin power (constant, useful as a single scalar in the .mat)
  parameter Modelica.Units.SI.HeatFlowRate Q_per_slice = q_lin * dz;
  parameter Modelica.Units.SI.HeatFlowRate Q_total = q_lin * L_total;
  parameter Modelica.Units.SI.ThermalResistance R_tot_radial =
    1.0 / (4 * Modelica.Constants.pi * k_fuel * dz)
    + 1.0 / (2 * Modelica.Constants.pi * r_pellet * h_gap * dz)
    + Modelica.Math.log(r_clad_outer / r_clad_inner) / (2 * Modelica.Constants.pi * k_clad * dz)
    + R_conv;
equation
  // coolant chain
  connect(inlet.port, cells[1].port_a);
  for i in 1:(n - 1) loop
    connect(cells[i].port_b, cells[i + 1].port_a);
  end for;
  connect(cells[n].port_b, outlet.port);

  // per-slice: pin clad_outer -> convection -> cell heat
  for i in 1:n loop
    connect(pins[i].clad_outer, convs[i].port_a);
    connect(convs[i].port_b, cells[i].heat);
  end for;

  annotation (experiment(StopTime = 1.0));
end CoupledChain;
