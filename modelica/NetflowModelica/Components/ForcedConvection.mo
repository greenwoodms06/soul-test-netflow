within NetflowModelica.Components;

model ForcedConvection
  "Single-phase forced-convection coupling: 2 HeatPorts + Dittus-Boelter h(T_film).

   q = h(T_film) * A_ht * (T_wall - T_fluid)
   h = Nu * k_f / D_h,  Nu = 0.023 * Re^0.8 * Pr_f^n
   Re = mdot * D_h / (mu * A_xs),  A_xs = pi * D_h^2 / 4 by default

   Properties (mu, k_f, Pr) come from the supplied Medium evaluated at
   T_film = (T_wall + T_fluid)/2 and p_ref. Default exponent n=0.4 (heating).

   DEBT: only Dittus-Boelter implemented (no Gnielinski). Heating direction
   assumed (caller picks n_DB). Forward flow only (mdot > 0); reversal would
   make Re negative and Re^0.8 NaN — guarded by parameter sign in callers,
   not by an assert here.
   DEBT: state_film is always computed (Modelica forbids conditional record
   declarations); when useFittedProps=true the medium state is built but the
   transport-property results are not read.
  "
  import Modelica.Constants.pi;
  import Modelica.Units.SI;

  replaceable package Medium = Modelica.Media.Water.StandardWater
    constrainedby Modelica.Media.Interfaces.PartialMedium;

  parameter SI.MassFlowRate mdot = 0.30 "Tube-side mass flow";
  parameter SI.Length D_h = 12.0e-3 "Hydraulic diameter";
  parameter SI.Area A_ht = 3.14e-2 "Heat-transfer area";
  parameter SI.Area A_xs = pi * D_h ^ 2 / 4 "Cross-section area";
  parameter Medium.AbsolutePressure p_ref = 15.5e6 "Pressure for property eval";
  parameter Real n_DB = 0.4 "Dittus-Boelter exponent (0.4 heating, 0.3 cooling)";
  parameter Boolean useFittedProps = false
    "If true, use Materials.water_props_fit_585_610K instead of Medium (for
     code-comparison parity against netflow's CoolProp HEOS backend)";

  Modelica.Thermal.HeatTransfer.Interfaces.HeatPort_a solid "Wall side";
  Modelica.Thermal.HeatTransfer.Interfaces.HeatPort_b fluid "Bulk fluid side";

  SI.Temperature T_film;
  SI.DynamicViscosity mu_f;
  SI.ThermalConductivity k_f;
  Real Pr_f(unit = "1");
  Real Re(unit = "1");
  Real Nu(unit = "1");
  SI.CoefficientOfHeatTransfer h_conv;
  SI.HeatFlowRate Q "wall → fluid";

  Medium.ThermodynamicState state_film;
equation
  T_film = 0.5 * (solid.T + fluid.T);
  // state always computed (Modelica forbids conditional declarations of
  // structural sub-records); when useFittedProps is true the state is
  // unused for mu/k/Pr though still computed.
  state_film = Medium.setState_pTX(p_ref, T_film, fill(0.0, Medium.nXi));
  if useFittedProps then
    mu_f = Materials.water_props_fit_585_610K.mu(T_film);
    k_f  = Materials.water_props_fit_585_610K.k(T_film);
    Pr_f = Materials.water_props_fit_585_610K.Pr(T_film);
  else
    mu_f = Medium.dynamicViscosity(state_film);
    k_f  = Medium.thermalConductivity(state_film);
    Pr_f = Medium.prandtlNumber(state_film);
  end if;
  Re   = mdot * D_h / (mu_f * A_xs);
  Nu   = 0.023 * Re ^ 0.8 * Pr_f ^ n_DB;
  h_conv = Nu * k_f / D_h;

  Q = h_conv * A_ht * (solid.T - fluid.T);
  solid.Q_flow = Q;
  fluid.Q_flow = -Q;
end ForcedConvection;
