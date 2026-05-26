within NetflowModelica.Tests;

model CoolantChannelHeated
  "Slice 2 test: inlet -> 5 CoolantCells in series with prescribed heat -> outlet.

   Each cell receives an equal share of Q_total via a FixedHeatFlow at its
   HeatPort. The expected outlet enthalpy is h_in + Q_total / mdot, and the
   expected outlet T comes from the Medium's (p, h) -> T inverse.
  "
  extends Modelica.Icons.Example;

  replaceable package Medium = Modelica.Media.Water.StandardWater
    constrainedby Modelica.Media.Interfaces.PartialMedium;

  parameter Integer n = 5 "Number of cells";
  parameter Modelica.Units.SI.MassFlowRate mdot = 0.30;
  parameter Modelica.Units.SI.Pressure p_nom = 15.5e6;
  parameter Modelica.Units.SI.Temperature T_in = 593.0;
  parameter Modelica.Units.SI.HeatFlowRate Q_total = 18000.0
    "Total power added across the channel";
  final parameter Modelica.Units.SI.HeatFlowRate Q_per_cell = Q_total / n;

  Components.CoolantInlet inlet(
    redeclare package Medium = Medium,
    mdot = mdot, p_ref = p_nom, T_in = T_in);
  Components.CoolantOutlet outlet(
    redeclare package Medium = Medium,
    p_set = p_nom, T_ambient = T_in);

  Components.CoolantCell cells[n](
    redeclare each package Medium = Medium,
    each p_start = p_nom, each T_start = T_in);

  Modelica.Thermal.HeatTransfer.Sources.FixedHeatFlow heaters[n](
    each Q_flow = Q_per_cell);

  // monitor outputs
  Medium.SpecificEnthalpy h_out_K = cells[n].h;
  Medium.Temperature T_out_K = cells[n].T;
equation
  // wire heaters → each cell's HeatPort
  for i in 1:n loop
    connect(heaters[i].port, cells[i].heat);
  end for;
  // cell-to-cell stream connections
  connect(inlet.port, cells[1].port_a);
  for i in 1:(n - 1) loop
    connect(cells[i].port_b, cells[i + 1].port_a);
  end for;
  connect(cells[n].port_b, outlet.port);

  annotation (experiment(StopTime = 1.0));
end CoolantChannelHeated;
