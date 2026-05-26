within NetflowModelica.Tests;

model AssemblyVeraP6
  "17×17 PWR assembly parameterized on the VERA Problem 6 operating point.

   VERA Problem 6 = single Watts Bar Unit 1 fuel assembly at HFP. P6 specifies
   inputs only (Godfrey 2014); every published P6 result is a CODE-TO-CODE
   solution (Kelly 2017 MC21/CTF, Aviles 2017 MC21/COBRA-IE, VERA/MPACT). This
   model carries the spec's operating point so step 3 physics extensions
   (cross-pin conduction, neutronics feedback, subchannel cross-flow) get an
   anchored comparison surface against:

     - Kelly 2017 Fig. 11 :  6.6 K coolant exit spread (MC21/CTF, VERA);
                             8.7 K spread (MC21/COBRA-IE)
     - Kelly 2017 Fig. 24 :  1065.8 °C peak volume-average fuel pin T
                             (this is a P7 number; P6 hot-pin volavg is lower)
     - Kelly 2017 Fig. 10 :  axially-integrated pin power 0.96-1.05
                             (~5% radial peaking in the 1/4-assembly)

   Parallel-independent channels (no cross-flow) — that's step 3c's job. This
   model is the SHELL the step-3 extensions attach to. Power profile is
   parameterized: q_lin_per_pin[ip] lets a power map be supplied, defaulting
   to uniform-average if not set.

   See docs/adr/0002-msl-only-carries-through-all-extensions.md for the scope.
  "
  extends Modelica.Icons.Example;

  import Modelica.Constants.pi;
  import Modelica.Units.SI;

  replaceable package Medium = Modelica.Media.Water.StandardWater
    constrainedby Modelica.Media.Interfaces.PartialMedium;

  // ---------------- VERA P6 operating point (from Godfrey 2014 + Kelly 2017) ---
  parameter Integer n_pin = 17 * 17 "Lattice positions (264 fuel + 24 guide + 1 inst)";
  parameter Integer n_axial = 30 "axial slices per channel";
  parameter SI.Length L_total = 3.6576 "Active fuel length (VERA P6)";
  final parameter SI.Length dz = L_total / n_axial;

  // Per-fuel-rod flow (VERA P6: 85.98 kg/s / 264 fuel rods = 0.326 kg/s).
  parameter SI.MassFlowRate mdot_per_pin = 85.98 / 264.0;
  parameter SI.Pressure p_nom = 15.51e6 "VERA P6: 2250 psia";
  parameter SI.Temperature T_in = 565.0 "VERA P6 inlet temperature";

  // VERA P6 average linear heat: 17.67 MW * 0.974 / (264 * 3.6576) = 17 838 W/m.
  parameter Real q_lin_avg(final unit = "W/m") = 17838.0
    "Average linear heat rate per fuel rod (VERA P6 derivation)";

  // Radial peaking map: defaults to uniform; an outer model can override.
  // Range ~0.96-1.05 per Kelly Fig. 10 for the 1/4-assembly normalized power.
  parameter Real q_lin_factor[n_pin] = ones(n_pin)
    "Per-pin radial peaking factor; product with q_lin_avg gives this pin's q_lin";

  // ---------------- VERA P6 fuel pin geometry ---------------------------------
  parameter SI.Radius r_pellet = 4.096e-3 "Pellet outer radius (P6: 0.8192 cm OD)";
  parameter SI.Length gap_thickness = 0.084e-3 "Radial gap (P6: 84 µm)";
  parameter SI.Radius r_clad_outer = 4.75e-3 "Clad outer radius (P6: 0.95 cm OD)";
  final parameter SI.Radius r_clad_inner = r_pellet + gap_thickness;

  // Closures (constant-property; T-dep closures swap in via FuelPinTDep variant).
  parameter SI.ThermalConductivity k_fuel = 3.0;
  parameter SI.ThermalConductivity k_clad = 16.0;
  parameter SI.CoefficientOfHeatTransfer h_gap = 7500.0
    "Gap conductance, netflow VERA codecompare value (vs slice-1 default 5000)";
  parameter SI.CoefficientOfHeatTransfer h_conv = 30000.0;

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

  // Pin power per channel: q_lin[ip] = q_lin_avg * q_lin_factor[ip] (axially uniform).
  // Nested braces give [n_pin, n_axial] matrix; flat comma comprehension's
  // dimension ordering in Modelica is iter-first which inverts that.
  Components.FuelPinConst pins[n_pin, n_axial](
    q_lin = {{q_lin_avg * q_lin_factor[ip] for iz in 1:n_axial} for ip in 1:n_pin},
    each L = dz,
    each r_pellet = r_pellet, each gap_thickness = gap_thickness,
    each r_clad_outer = r_clad_outer,
    each k_fuel = k_fuel, each k_clad = k_clad, each h_gap = h_gap);

  Modelica.Thermal.HeatTransfer.Components.ThermalResistor convs[n_pin, n_axial](
    each R = R_conv);

  // ---------------- Outputs for code-comparison ------------------------------
  // Outlet T per channel — the surface that maps to Kelly Fig. 11.
  SI.Temperature T_cool_exit[n_pin] = {cells[ip, n_axial].T for ip in 1:n_pin};
  // Spread = max - min over fuel-rod channels (here uniform; guide-tube
  // subtraction comes in step 3c when bypass topology is added).
  SI.Temperature T_cool_exit_max = max(T_cool_exit);
  SI.Temperature T_cool_exit_min = min(T_cool_exit);
  SI.Temperature T_cool_exit_spread = T_cool_exit_max - T_cool_exit_min;
  // Peak fuel volume-average T over all pins, all axials — surface for Kelly Fig. 24.
  // Volume average over a parabolic pellet profile = (T_center + T_surface) / 2.
  SI.Temperature T_fuel_volavg[n_pin, n_axial] = {
    {0.5 * (pins[ip, iz].T_centerline_K + pins[ip, iz].T_pellet_surface_K)
     for iz in 1:n_axial}
    for ip in 1:n_pin};
  SI.Temperature T_fuel_volavg_peak = max(T_fuel_volavg);
  // Total assembly thermal power (sanity invariant).
  SI.HeatFlowRate Q_total_assembly = q_lin_avg * L_total * sum(q_lin_factor);
equation
  for ip in 1:n_pin loop
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
end AssemblyVeraP6;
