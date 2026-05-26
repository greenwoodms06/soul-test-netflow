within NetflowModelica.Tests;

model ParallelChannelFlowSplit
  "Slice 8 test: 3 parallel friction channels sharing inlet/outlet pressure.

   Verifies: ṁ_i = √(Δp / K_i) at machine precision, Σṁ = mass-conserving.
   The friction law Δp = K·ṁ·|ṁ| is the nonlinear case netflow's hydraulic
   plugin flagged; here Modelica's connect() with a pure pressure-pressure
   network resolves it cleanly.

   DEBT: isothermal (enthalpy carried but passive); steady; K constant.
   No zero-flow case here — that lives in ZeroFlowStartTrap below.
  "
  extends Modelica.Icons.Example;

  parameter Real K1(final unit = "Pa.s2/kg2") = 1.0e8;
  parameter Real K2(final unit = "Pa.s2/kg2") = 2.0e8;
  parameter Real K3(final unit = "Pa.s2/kg2") = 4.0e8;
  parameter Modelica.Units.SI.Pressure p_in = 2.0e5;
  parameter Modelica.Units.SI.Pressure p_out = 1.0e5;

  Components.PressureBoundary inlet(p_set = p_in);
  Components.PressureBoundary outlet(p_set = p_out);
  Components.FrictionPipe ch1(K = K1);
  Components.FrictionPipe ch2(K = K2);
  Components.FrictionPipe ch3(K = K3);

  // monitor outputs
  Modelica.Units.SI.MassFlowRate mdot1 = ch1.port_a.m_flow;
  Modelica.Units.SI.MassFlowRate mdot2 = ch2.port_a.m_flow;
  Modelica.Units.SI.MassFlowRate mdot3 = ch3.port_a.m_flow;
  Modelica.Units.SI.MassFlowRate mdot_total = mdot1 + mdot2 + mdot3;
equation
  connect(inlet.port, ch1.port_a);
  connect(inlet.port, ch2.port_a);
  connect(inlet.port, ch3.port_a);
  connect(ch1.port_b, outlet.port);
  connect(ch2.port_b, outlet.port);
  connect(ch3.port_b, outlet.port);

  annotation (experiment(StopTime = 1.0));
end ParallelChannelFlowSplit;
