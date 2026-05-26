within NetflowModelica.Tests;

model TransientPinConst
  "Slice 5 test: constant-property pin with a HeatCapacitor at the centerline.

   First-order analytic system:
     C dT/dt = Q − (T − T_cool)/R_tot
     T(t) = T_inf + (T_cool − T_inf) exp(−t/τ)
     τ = R_tot · C,    T_inf = T_cool + Q · R_tot

   Verifies (Python driver):
     (a) T(t_end) → analytic first-order trajectory
     (b) T(∞) equals the slice-1 steady centerline (1252.99 K)

   This is the canonical 'add storage without changing connectors' demonstration
   the ADR named — the resistor stack from slice 1 is untouched; one HeatCapacitor
   connect() makes the system dynamic.
  "
  extends Modelica.Icons.Example;

  import Modelica.Constants.pi;
  import Modelica.Units.SI;

  // Match slice 1 / Julia constants exactly.
  parameter SI.Radius r_pellet = 4.10e-3;
  parameter SI.Length gap_thickness = 0.085e-3;
  parameter SI.Radius r_clad_outer = 4.75e-3;
  parameter SI.Length L = 1.0;
  parameter SI.HeatFlowRate Q = 18000.0;
  parameter SI.Temperature T_cool = 593.0;
  parameter SI.ThermalConductivity k_fuel = 3.0;
  parameter SI.ThermalConductivity k_clad = 16.0;
  parameter SI.CoefficientOfHeatTransfer h_gap = 5000.0;
  parameter SI.CoefficientOfHeatTransfer h_conv = 30000.0;

  final parameter SI.Radius r_clad_inner = r_pellet + gap_thickness;
  final parameter SI.ThermalResistance R_fuel = 1.0 / (4 * pi * k_fuel * L);
  final parameter SI.ThermalResistance R_gap =
    1.0 / (2 * pi * r_pellet * h_gap * L);
  final parameter SI.ThermalResistance R_clad =
    Modelica.Math.log(r_clad_outer / r_clad_inner) / (2 * pi * k_clad * L);
  final parameter SI.ThermalResistance R_conv =
    1.0 / (2 * pi * r_clad_outer * h_conv * L);
  final parameter SI.ThermalResistance R_tot = R_fuel + R_gap + R_clad + R_conv;

  // Lumped pellet thermal capacity (matches netflow's model)
  parameter SI.Density rho_UO2 = 10900.0;
  parameter SI.SpecificHeatCapacity cp_pellet = 300.0;
  final parameter SI.HeatCapacity C_fuel =
    pi * r_pellet ^ 2 * L * rho_UO2 * cp_pellet;
  final parameter SI.Time tau = R_tot * C_fuel;
  final parameter SI.Temperature T_inf = T_cool + Q * R_tot;

  Modelica.Thermal.HeatTransfer.Sources.FixedHeatFlow src(Q_flow = Q);
  Modelica.Thermal.HeatTransfer.Components.HeatCapacitor cap(C = C_fuel, T(start = T_cool, fixed = true));
  Modelica.Thermal.HeatTransfer.Components.ThermalResistor Rf(R = R_fuel);
  Modelica.Thermal.HeatTransfer.Components.ThermalResistor Rg(R = R_gap);
  Modelica.Thermal.HeatTransfer.Components.ThermalResistor Rc(R = R_clad);
  Modelica.Thermal.HeatTransfer.Components.ThermalResistor Rh(R = R_conv);
  Modelica.Thermal.HeatTransfer.Sources.FixedTemperature cool(T = T_cool);

  // monitor outputs
  SI.Temperature T_centerline_K = cap.T;
equation
  connect(src.port, cap.port);
  connect(cap.port, Rf.port_a);
  connect(Rf.port_b, Rg.port_a);
  connect(Rg.port_b, Rc.port_a);
  connect(Rc.port_b, Rh.port_a);
  connect(Rh.port_b, cool.port);

  annotation (experiment(StopTime = 80.0, Tolerance = 1e-9));
end TransientPinConst;
