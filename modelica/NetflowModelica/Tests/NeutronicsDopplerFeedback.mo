within NetflowModelica.Tests;

model NeutronicsDopplerFeedback
  "Slice 7 test: signal-domain point-kinetics ↔ acausal thermal feedback loop.

   Topology:
     PointKinetics.power  → PrescribedHeatFlow.Q_flow_in   (signal → heat)
     HeatCapacitor (fuel) + ThermalResistor R + FixedTemperature (cool)
     TemperatureSensor.T  → PointKinetics.T_fuel           (heat → signal)

   At t=0 the kinetics carries +100 pcm of external reactivity; power rises,
   fuel heats, negative Doppler returns reactivity to zero at a new
   equilibrium.

   Verification (Python driver):
     T_eq = T_ref - ρ_ext/α
     P_eq = (T_eq - T_cool)/R_th
     n_eq = P_eq/P0

   DEBT: lumped single-node fuel; one delayed group; constants illustrative.
  "
  extends Modelica.Icons.Example;

  parameter Modelica.Units.SI.Temperature T_cool = 593.0;
  parameter Modelica.Units.SI.ThermalResistance R_th = 0.036666;
  parameter Modelica.Units.SI.HeatCapacity C_fuel = 172.7;
  parameter Modelica.Units.SI.Temperature T_nom = T_cool + 18000.0 * R_th
    "Slice-1 steady centerline; matches PointKinetics.T_ref";

  Components.PointKinetics kin(
    rho_ext = 1e-3, T_ref = T_nom, P0 = 18000.0);
  Modelica.Thermal.HeatTransfer.Sources.PrescribedHeatFlow src;
  Modelica.Thermal.HeatTransfer.Components.HeatCapacitor fuel(
    C = C_fuel, T(start = T_nom, fixed = true));
  Modelica.Thermal.HeatTransfer.Components.ThermalResistor R(R = R_th);
  Modelica.Thermal.HeatTransfer.Sources.FixedTemperature cool(T = T_cool);
  Modelica.Thermal.HeatTransfer.Sensors.TemperatureSensor sensor;
equation
  // signal → heat
  connect(kin.y, src.Q_flow);
  // heat network: source + capacitor + sensor on the fuel node;
  // resistor to coolant
  connect(src.port, fuel.port);
  connect(fuel.port, R.port_a);
  connect(R.port_b, cool.port);
  connect(sensor.port, fuel.port);
  // heat → signal (feedback)
  connect(sensor.T, kin.u);

  annotation (experiment(StopTime = 300.0, Tolerance = 1e-9));
end NeutronicsDopplerFeedback;
