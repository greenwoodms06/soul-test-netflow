within NetflowModelica.Tests;

model TransientChain
  "Slice 6 test: full transient coupled chain (slice 3 + storage at every node).

   Topology: inlet → 10 CoolantCellDyn cells → outlet
             10 parallel pin radial stacks (FixedHeatFlow + HeatCapacitor at
             centerline + 4 resistors + ThermalResistor convection) → cells[i].heat

   Step power at t=0 (the heaters carry the full Q_per_cell immediately;
   capacitors at each centerline + each cell's fluid mass smooth the response).

   Verification (in Python driver): at t_end (≈ 10τ_pin), every centerline and
   every cell T must match the slice-3 STEADY answer (which is the t→∞ limit
   of this transient). Apples-to-apples with slice 3 — same connectors, same
   resistances; only storage added.

   DEBT: lumped centerline capacity ONLY (no separate clad capacity, no
   coolant mass dynamics finer than M_cool per cell). This makes the model
   structurally first-order per pin, so overshoot cannot appear — physically
   correct for this slow-thermal regime but a real BWR/PWR with
   gap-conductance dynamics or fast scram transients would need finer
   storage breakdown.
   DEBT: M_cool uses rho_cool=700 kg/m³ as the order-of-magnitude coolant
   density at PWR conditions; couples to ~5% error in fluid time constant
   but does NOT affect the t→∞ steady state.
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
  final parameter SI.ThermalResistance R_tot = R_fuel + R_gap + R_clad + R_conv;

  parameter SI.Density rho_UO2 = 10900.0;
  parameter SI.SpecificHeatCapacity cp_pellet = 300.0;
  final parameter SI.HeatCapacity C_fuel =
    pi * r_pellet ^ 2 * dz * rho_UO2 * cp_pellet;

  // coolant mass per cell — order-of-magnitude estimate matching Julia
  // (700 kg/m³ × π·D_h²/4 × dz at PWR conditions)
  parameter SI.Length D_h = 12.0e-3;
  parameter SI.Density rho_cool = 700.0;
  final parameter SI.Mass M_cool = rho_cool * pi * D_h ^ 2 / 4 * dz;

  Components.CoolantInlet inlet(
    redeclare package Medium = Medium,
    mdot = mdot, p_ref = p_nom, T_in = T_in);
  Components.CoolantOutlet outlet(
    redeclare package Medium = Medium,
    p_set = p_nom, T_ambient = T_in);

  Components.CoolantCellDyn cells[n](
    redeclare each package Medium = Medium,
    each p_start = p_nom, each T_start = T_in, each M = M_cool);

  Modelica.Thermal.HeatTransfer.Sources.FixedHeatFlow srcs[n](
    each Q_flow = Q_per_cell);
  Modelica.Thermal.HeatTransfer.Components.HeatCapacitor caps[n](
    each C = C_fuel, each T(start = T_in, fixed = true));
  Modelica.Thermal.HeatTransfer.Components.ThermalResistor Rfs[n](each R = R_fuel);
  Modelica.Thermal.HeatTransfer.Components.ThermalResistor Rgs[n](each R = R_gap);
  Modelica.Thermal.HeatTransfer.Components.ThermalResistor Rcs[n](each R = R_clad);
  Modelica.Thermal.HeatTransfer.Components.ThermalResistor Rhs[n](each R = R_conv);

  // monitor outputs (per-slice T_cool + T_centerline arrays)
  SI.Temperature T_cool[n] = {cells[i].T for i in 1:n};
  SI.Temperature T_centerline[n] = {caps[i].T for i in 1:n};
equation
  // coolant chain
  connect(inlet.port, cells[1].port_a);
  for i in 1:(n - 1) loop
    connect(cells[i].port_b, cells[i + 1].port_a);
  end for;
  connect(cells[n].port_b, outlet.port);

  // per-slice radial stack with centerline storage
  for i in 1:n loop
    connect(srcs[i].port, caps[i].port);
    connect(caps[i].port, Rfs[i].port_a);
    connect(Rfs[i].port_b, Rgs[i].port_a);
    connect(Rgs[i].port_b, Rcs[i].port_a);
    connect(Rcs[i].port_b, Rhs[i].port_a);
    connect(Rhs[i].port_b, cells[i].heat);
  end for;

  annotation (experiment(StopTime = 60.0, Tolerance = 1e-8));
end TransientChain;
