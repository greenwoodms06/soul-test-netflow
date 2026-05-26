within NetflowModelica.Tests;

model Assembly17x17
  "17×17 PWR assembly stress test: 289 parallel channels × n_axial slices.

   Same physics as CoupledChain but spreads across n_pin parallel channels
   (no cross-coupling — that's slice 10's job; this is the SCALING test).
   Each channel has its own inlet/outlet so flow rates are independent.

   Target: 17×17 = 289 channels × 30 axial = 8,670 pin nodes (Julia MTK-F9
   anchor) → ~17k unknowns. Julia extrapolated 25-40 min mtkcompile @ this
   scale; we measure whether Dymola does better.
  "
  extends Modelica.Icons.Example;

  import Modelica.Constants.pi;
  import Modelica.Units.SI;

  replaceable package Medium = Modelica.Media.Water.StandardWater
    constrainedby Modelica.Media.Interfaces.PartialMedium;

  parameter Integer n_pin = 17 * 17 "number of parallel pin channels";
  parameter Integer n_axial = 30 "axial slices per channel";
  parameter SI.Length L_total = 3.66;
  final parameter SI.Length dz = L_total / n_axial;

  parameter SI.MassFlowRate mdot_per_pin = 0.30;
  parameter SI.Pressure p_nom = 15.5e6;
  parameter SI.Temperature T_in = 565.0;
  parameter Real q_lin(final unit = "W/m") = 18000.0;

  parameter SI.ThermalConductivity k_fuel = 3.0;
  parameter SI.ThermalConductivity k_clad = 16.0;
  parameter SI.CoefficientOfHeatTransfer h_gap = 5000.0;
  parameter SI.CoefficientOfHeatTransfer h_conv = 30000.0;

  parameter SI.Radius r_pellet = 4.10e-3;
  parameter SI.Length gap_thickness = 0.085e-3;
  parameter SI.Radius r_clad_outer = 4.75e-3;
  final parameter SI.Radius r_clad_inner = r_pellet + gap_thickness;

  final parameter SI.HeatFlowRate Q_per_cell = q_lin * dz;

  final parameter SI.ThermalResistance R_fuel = 1.0 / (4 * pi * k_fuel * dz);
  final parameter SI.ThermalResistance R_gap =
    1.0 / (2 * pi * r_pellet * h_gap * dz);
  final parameter SI.ThermalResistance R_clad =
    Modelica.Math.log(r_clad_outer / r_clad_inner) / (2 * pi * k_clad * dz);
  final parameter SI.ThermalResistance R_conv =
    1.0 / (2 * pi * r_clad_outer * h_conv * dz);

  Components.CoolantInlet inlets[n_pin](
    redeclare each package Medium = Medium,
    each mdot = mdot_per_pin, each p_ref = p_nom, each T_in = T_in);
  Components.CoolantOutlet outlets[n_pin](
    redeclare each package Medium = Medium,
    each p_set = p_nom, each T_ambient = T_in);

  Components.CoolantCell cells[n_pin, n_axial](
    redeclare each package Medium = Medium,
    each p_start = p_nom, each T_start = T_in);

  Components.FuelPinConst pins[n_pin, n_axial](
    each q_lin = q_lin, each L = dz,
    each r_pellet = r_pellet, each gap_thickness = gap_thickness,
    each r_clad_outer = r_clad_outer,
    each k_fuel = k_fuel, each k_clad = k_clad, each h_gap = h_gap);

  Modelica.Thermal.HeatTransfer.Components.ThermalResistor convs[n_pin, n_axial](
    each R = R_conv);

  // summary outputs (small enough to read from .mat)
  Modelica.Units.SI.Temperature T_centerline_hot = max(
    {pins[ip, iz].T_centerline_K for ip in 1:n_pin, iz in 1:n_axial});
  Modelica.Units.SI.Temperature T_cool_outlet_max = max(
    {cells[ip, n_axial].T for ip in 1:n_pin});
  Modelica.Units.SI.HeatFlowRate Q_total_assembly = q_lin * L_total * n_pin;
equation
  for ip in 1:n_pin loop
    // each channel: inlet → cell[1] → cell[2] → ... → cell[n_axial] → outlet
    connect(inlets[ip].port, cells[ip, 1].port_a);
    for iz in 1:(n_axial - 1) loop
      connect(cells[ip, iz].port_b, cells[ip, iz + 1].port_a);
    end for;
    connect(cells[ip, n_axial].port_b, outlets[ip].port);

    for iz in 1:n_axial loop
      connect(pins[ip, iz].clad_outer, convs[ip, iz].port_a);
      connect(convs[ip, iz].port_b, cells[ip, iz].heat);
    end for;
  end for;

  annotation (experiment(StopTime = 1.0));
end Assembly17x17;
