within NetflowModelica.Tests;

model AxialConductionChain
  "Slice 10 test: coupled chain + axial centerline-to-centerline conduction.

   Adds (n-1) ThermalConductors between adjacent pin centerlines. With a
   peaked axial power profile, axial conduction smooths the centerline peak;
   energy is only REDISTRIBUTED, so total ṁ·Δh = ΣQ still holds exactly
   regardless of G_axial. Tests Modelica with wider-band coupling.

   DEBT: constant props; lumped centerline-to-centerline path; peaked power
   is cosine, normalized to the same total Q as CoupledChain.
  "
  extends Modelica.Icons.Example;

  import Modelica.Constants.pi;
  import Modelica.Units.SI;

  replaceable package Medium = Modelica.Media.Water.StandardWater
    constrainedby Modelica.Media.Interfaces.PartialMedium;

  parameter Integer n = 10;
  parameter SI.Length L_total = 3.66;
  final parameter SI.Length dz = L_total / n;

  parameter SI.MassFlowRate mdot = 0.30;
  parameter SI.Pressure p_nom = 15.5e6;
  parameter SI.Temperature T_in = 565.0;

  parameter SI.ThermalConductivity k_fuel = 3.0;
  parameter SI.ThermalConductivity k_clad = 16.0;
  parameter SI.CoefficientOfHeatTransfer h_gap = 5000.0;
  parameter SI.CoefficientOfHeatTransfer h_conv = 30000.0;

  parameter SI.Radius r_pellet = 4.10e-3;
  parameter SI.Length gap_thickness = 0.085e-3;
  parameter SI.Radius r_clad_outer = 4.75e-3;
  final parameter SI.Radius r_clad_inner = r_pellet + gap_thickness;

  parameter SI.ThermalConductance G_axial = 5.0
    "Centerline-to-centerline axial conductance per pair (W/K)";

  // peaked cosine power: q_i = (1 + 0.8 * cos(π·(i - 0.5)/n - π/2)) normalised
  // to total Q = q_lin_avg * L_total
  parameter Real q_lin_avg(final unit = "W/m") = 18000.0;
  final parameter SI.HeatFlowRate Q_total = q_lin_avg * L_total;

  // We compute the raw axial weights, then per-cell power.
  final parameter Real q_w[n] = {1 + 0.8 * Modelica.Math.cos(pi * ((i - 0.5)/n - 0.5)) for i in 1:n};
  final parameter Real q_w_sum = sum(q_w);
  final parameter SI.HeatFlowRate Q_per_cell[n] = {Q_total * q_w[i] / q_w_sum for i in 1:n};

  final parameter SI.ThermalResistance R_fuel = 1.0 / (4 * pi * k_fuel * dz);
  final parameter SI.ThermalResistance R_gap =
    1.0 / (2 * pi * r_pellet * h_gap * dz);
  final parameter SI.ThermalResistance R_clad =
    Modelica.Math.log(r_clad_outer / r_clad_inner) / (2 * pi * k_clad * dz);
  final parameter SI.ThermalResistance R_conv =
    1.0 / (2 * pi * r_clad_outer * h_conv * dz);
  final parameter SI.ThermalResistance R_tot = R_fuel + R_gap + R_clad + R_conv;

  Components.CoolantInlet inlet(
    redeclare package Medium = Medium,
    mdot = mdot, p_ref = p_nom, T_in = T_in);
  Components.CoolantOutlet outlet(
    redeclare package Medium = Medium,
    p_set = p_nom, T_ambient = T_in);

  Components.CoolantCell cells[n](
    redeclare each package Medium = Medium,
    each p_start = p_nom, each T_start = T_in);

  Modelica.Thermal.HeatTransfer.Sources.FixedHeatFlow srcs[n](
    Q_flow = Q_per_cell);
  Modelica.Thermal.HeatTransfer.Components.ThermalResistor Rfs[n](each R = R_fuel);
  Modelica.Thermal.HeatTransfer.Components.ThermalResistor Rgs[n](each R = R_gap);
  Modelica.Thermal.HeatTransfer.Components.ThermalResistor Rcs[n](each R = R_clad);
  Modelica.Thermal.HeatTransfer.Components.ThermalResistor Rhs[n](each R = R_conv);
  Modelica.Thermal.HeatTransfer.Components.ThermalConductor axials[n - 1](
    each G = G_axial);

  // monitor outputs
  Modelica.Units.SI.Temperature T_cool[n] = {cells[i].T for i in 1:n};
  // centerline T is read off the FixedHeatFlow port (it's at the centerline node)
  Modelica.Units.SI.Temperature T_centerline[n] = {srcs[i].port.T for i in 1:n};
  Modelica.Units.SI.SpecificEnthalpy h_in_K = inlet.h_in;
  Modelica.Units.SI.SpecificEnthalpy h_out_K = cells[n].h;
  Modelica.Units.SI.HeatFlowRate mdot_dh = mdot * (h_out_K - h_in_K);
equation
  connect(inlet.port, cells[1].port_a);
  for i in 1:(n - 1) loop
    connect(cells[i].port_b, cells[i + 1].port_a);
  end for;
  connect(cells[n].port_b, outlet.port);

  for i in 1:n loop
    connect(srcs[i].port, Rfs[i].port_a);
    connect(Rfs[i].port_b, Rgs[i].port_a);
    connect(Rgs[i].port_b, Rcs[i].port_a);
    connect(Rcs[i].port_b, Rhs[i].port_a);
    connect(Rhs[i].port_b, cells[i].heat);
  end for;
  // axial centerline coupling
  for i in 1:(n - 1) loop
    connect(srcs[i].port, axials[i].port_a);
    connect(axials[i].port_b, srcs[i + 1].port);
  end for;

  annotation (experiment(StopTime = 1.0));
end AxialConductionChain;
