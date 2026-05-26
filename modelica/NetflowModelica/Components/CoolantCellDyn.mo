within NetflowModelica.Components;

model CoolantCellDyn
  "Coolant cell with fluid energy storage M·dh/dt — transient extension of CoolantCell.

   Identical port surface and equations as CoolantCell except the energy
   balance becomes
       M * dh/dt = ṁ_in*h_in + ṁ_out*h_out + Q
   instead of the steady form (LHS = 0). Connectors UNCHANGED — slice 5/6's
   demonstration that adding storage doesn't break the bounded model.
  "
  replaceable package Medium = Modelica.Media.Water.StandardWater
    constrainedby Modelica.Media.Interfaces.PartialMedium;

  parameter Medium.AbsolutePressure p_start = 15.5e6 "Nominal/start pressure";
  parameter Medium.Temperature T_start = 565.0;
  parameter Modelica.Units.SI.Mass M = 0.03 "Coolant mass in the cell";
  // DEBT: M is supplied by the caller; we do not derive it from cell volume
  // because that would couple to a hydraulic geometry not in the cell's
  // interface. Callers compute M = rho_cool × π·D_h²/4 × dz with an
  // approximate rho_cool ~ 700 kg/m³ (good to ~5% at 565-610 K, p=15.5 MPa).
  final parameter Medium.SpecificEnthalpy h_start =
    Medium.specificEnthalpy_pT(p_start, T_start);

  Modelica.Fluid.Interfaces.FluidPort_a port_a(redeclare package Medium = Medium);
  Modelica.Fluid.Interfaces.FluidPort_b port_b(redeclare package Medium = Medium);
  Modelica.Thermal.HeatTransfer.Interfaces.HeatPort_a heat;

  Medium.SpecificEnthalpy h(start = h_start, fixed = true);
  Medium.Temperature T;
  Medium.AbsolutePressure p;
  Modelica.Units.SI.HeatFlowRate Q;

  Medium.ThermodynamicState state;
equation
  // mass balance — steady (incompressible-ish; cell mass M is constant)
  port_a.m_flow + port_b.m_flow = 0;

  port_a.p = p;
  port_b.p = p;

  port_a.h_outflow = h;
  port_b.h_outflow = h;
  port_a.Xi_outflow = zeros(Medium.nXi);
  port_b.Xi_outflow = zeros(Medium.nXi);
  port_a.C_outflow = zeros(Medium.nC);
  port_b.C_outflow = zeros(Medium.nC);

  state = Medium.setState_phX(p, h, fill(0.0, Medium.nXi));
  T = Medium.temperature(state);

  heat.T = T;
  Q = heat.Q_flow;

  // energy balance — TRANSIENT (M dh/dt = net enthalpy + heat)
  M * der(h) =
      port_a.m_flow * actualStream(port_a.h_outflow)
    + port_b.m_flow * actualStream(port_b.h_outflow)
    + Q;
end CoolantCellDyn;
