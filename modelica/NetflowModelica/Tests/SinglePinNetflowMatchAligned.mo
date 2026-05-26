within NetflowModelica.Tests;

model SinglePinNetflowMatchAligned
  "Slice 4b: same as SinglePinNetflowMatch but with useFittedProps=true so the
   convection h uses the exact same quadratic-fit water properties netflow's
   CoolProp HEOS backend supplies — isolates the IF97-vs-HEOS transport-property
   formulation difference from any model-structure / closure mismatch.

   This is the strict apples-to-apples 'matching netflow's exact closures'
   check, matching Julia's slice4 strategy.
  "
  extends Modelica.Icons.Example;

  Components.FuelPinTDep pin(q_lin = 18000.0, L = 1.0);
  Components.ForcedConvection conv(
    mdot = 0.30, D_h = 12.0e-3, A_ht = 3.14e-2,
    p_ref = 15.5e6, n_DB = 0.4,
    useFittedProps = true);
  Modelica.Thermal.HeatTransfer.Sources.FixedTemperature cool(T = 593.0);
equation
  connect(pin.clad_outer, conv.solid);
  connect(conv.fluid, cool.port);

  annotation (experiment(StopTime = 1.0));
end SinglePinNetflowMatchAligned;
