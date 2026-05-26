within NetflowModelica.Tests;

model FuelPinSteady
  "Slice 1 test: constant-property fuel pin with clad-outer pinned to T_cool.

   No states (pure algebraic). Dymola solves at initialization; we run a tiny
   stopTime so the result file contains the trivially-constant trajectory.
  "
  extends Modelica.Icons.Example;

  parameter Modelica.Units.SI.Temperature T_cool = 593.0 "Coolant boundary T";

  Components.FuelPinConst pin;
  Modelica.Thermal.HeatTransfer.Sources.FixedTemperature cool(T = T_cool);
equation
  connect(pin.clad_outer, cool.port);

  annotation (experiment(StopTime = 1.0));
end FuelPinSteady;
