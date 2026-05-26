within NetflowModelica.Tests;

model AssemblyVeraP6Neutronics
  "AssemblyVeraP6 + per-pin point-kinetics feedback (step 3b of the unfreeze).

   Replaces the static FuelPinConst stack with FuelPinDynPower instances
   driven by per-pin PointKinetics blocks. Each pin's centerline temperature
   feeds its own kinetics block via the Doppler reactivity coefficient; the
   kinetics block's power output drives the centerline heat-flow of that
   pin's axial column (divided evenly across axial slices).

   Each pin has ONE kinetics block — the integrator state lives at the pin
   level, not the axial-slice level. T_fuel feedback uses the pin's mid-
   axial centerline temperature as the representative feedback signal.

   What this tests:
     - Does Dymola's integrator handle 289 coupled ODE systems (n, C per pin)
       on top of 289 × 30 = 8 670 thermal nodes?
     - Does the equilibrium drift across pins (radial peaking induced by
       inhomogeneous initial conditions or Doppler)?

   MSL-only (ADR-0002): PointKinetics block in NetflowModelica.Components;
   FuelPinDynPower in same. Only `Modelica.Blocks.*` and
   `Modelica.Thermal.HeatTransfer.*` and `Modelica.Fluid.*` imports.
  "
  extends Modelica.Icons.Example;

  import Modelica.Constants.pi;
  import Modelica.Units.SI;

  replaceable package Medium = Modelica.Media.Water.StandardWater
    constrainedby Modelica.Media.Interfaces.PartialMedium;

  parameter Integer n_pin = 17 * 17 "Lattice positions";
  parameter Integer n_axial = 30 "axial slices per channel";
  parameter SI.Length L_total = 3.6576 "Active length (VERA P6)";
  final parameter SI.Length dz = L_total / n_axial;

  parameter SI.MassFlowRate mdot_per_pin = 85.98 / 264.0;
  parameter SI.Pressure p_nom = 15.51e6;
  parameter SI.Temperature T_in = 565.0;

  parameter Real q_lin_avg(final unit = "W/m") = 17838.0;
  parameter Real q_lin_factor[n_pin] = ones(n_pin);

  parameter SI.Radius r_pellet = 4.096e-3;
  parameter SI.Length gap_thickness = 0.084e-3;
  parameter SI.Radius r_clad_outer = 4.75e-3;
  final parameter SI.Radius r_clad_inner = r_pellet + gap_thickness;

  parameter SI.ThermalConductivity k_fuel = 3.0;
  parameter SI.ThermalConductivity k_clad = 16.0;
  parameter SI.CoefficientOfHeatTransfer h_gap = 7500.0;
  parameter SI.CoefficientOfHeatTransfer h_conv = 30000.0;
  final parameter SI.ThermalResistance R_conv =
    1.0 / (2 * pi * r_clad_outer * h_conv * dz);

  // Reference centerline T for Doppler — picked from the slice-3 outlet
  // analytical estimate so initial Doppler is near zero.
  parameter SI.Temperature T_ref_centerline = 1253.0;

  // Per-pin reference power (W) — equals q_lin * L_total for that pin
  final parameter SI.Power P_ref_per_pin[n_pin] = {
    q_lin_avg * q_lin_factor[ip] * L_total for ip in 1:n_pin};
  final parameter SI.Power P_per_axial_ref[n_pin] = P_ref_per_pin ./ n_axial;

  Components.CoolantInlet inlets[n_pin](
    redeclare each package Medium = Medium,
    each mdot = mdot_per_pin, each p_ref = p_nom, each T_in = T_in);
  Components.CoolantOutlet outlets[n_pin](
    redeclare each package Medium = Medium,
    each p_set = p_nom, each T_ambient = T_in);
  Components.CoolantCell cells[n_pin, n_axial](
    redeclare each package Medium = Medium,
    each p_start = p_nom, each T_start = T_in);

  // Per-pin point-kinetics block (one per pin, not per axial slice).
  // P0 is the steady-state per-pin power; the block output is divided among axial slices.
  Components.PointKinetics kins[n_pin](
    P0 = P_ref_per_pin,
    each T_ref = T_ref_centerline,
    each rho_ext = 0.0,
    each alpha_doppler = -2.5e-5,
    each beta = 0.0065,
    each Lambda = 2e-5,
    each lambda = 0.08);

  // Per-pin, per-axial fuel pin (signal-driven power).
  Components.FuelPinDynPower pins[n_pin, n_axial](
    each L = dz,
    each r_pellet = r_pellet, each gap_thickness = gap_thickness,
    each r_clad_outer = r_clad_outer,
    each k_fuel = k_fuel, each k_clad = k_clad, each h_gap = h_gap);

  Modelica.Thermal.HeatTransfer.Components.ThermalResistor convs[n_pin, n_axial](
    each R = R_conv);

  // Mid-axial sensor index for T_fuel feedback (representative centerline T).
  final parameter Integer iz_mid = max(1, integer(n_axial / 2));

  // Diagnostic outputs.
  SI.Temperature T_centerline_hot = max({
    pins[ip, iz].T_centerline_K for ip in 1:n_pin, iz in 1:n_axial});
  SI.Power P_total = sum({kins[ip].y for ip in 1:n_pin});
  SI.Power P_total_ref = sum(P_ref_per_pin);
  SI.Temperature T_cool_outlet_max = max({
    cells[ip, n_axial].T for ip in 1:n_pin});
equation
  for ip in 1:n_pin loop
    // Feedback: pin's mid-axial centerline T -> kinetics block input
    kins[ip].u = pins[ip, iz_mid].T_centerline_K;
    // Distribute the kinetics power output evenly across this pin's axials
    for iz in 1:n_axial loop
      pins[ip, iz].Q_flow_in = kins[ip].y / n_axial;
    end for;

    // Coolant chain
    connect(inlets[ip].port, cells[ip, 1].port_a);
    for iz in 1:(n_axial - 1) loop
      connect(cells[ip, iz].port_b, cells[ip, iz + 1].port_a);
    end for;
    connect(cells[ip, n_axial].port_b, outlets[ip].port);

    // Pin-to-coolant coupling
    for iz in 1:n_axial loop
      connect(pins[ip, iz].clad_outer, convs[ip, iz].port_a);
      connect(convs[ip, iz].port_b, cells[ip, iz].heat);
    end for;
  end for;

  annotation (experiment(StopTime = 50.0, Tolerance = 1e-6));
end AssemblyVeraP6Neutronics;
