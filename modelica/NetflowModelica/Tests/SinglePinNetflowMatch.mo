within NetflowModelica.Tests;

model SinglePinNetflowMatch
  "Slice 4 test: one T-dependent FuelPin + ForcedConvection (IF97 props at T_film)
   into a fixed-T coolant boundary at 593 K — exact netflow quickstart scenario.

   The four node temperatures are compared to netflow's re-measurement on the
   same machine (results/netflow_baseline.json). Code comparison (not validation).
  "
  extends Modelica.Icons.Example;

  Components.FuelPinTDep pin(q_lin = 18000.0, L = 1.0);
  Components.ForcedConvection conv(
    mdot = 0.30, D_h = 12.0e-3, A_ht = 3.14e-2, p_ref = 15.5e6, n_DB = 0.4);
  Modelica.Thermal.HeatTransfer.Sources.FixedTemperature cool(T = 593.0);
equation
  connect(pin.clad_outer, conv.solid);
  connect(conv.fluid, cool.port);

  annotation (experiment(StopTime = 1.0));
end SinglePinNetflowMatch;
