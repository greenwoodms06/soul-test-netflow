within NetflowModelica.Components;

model FuelPinTDep
  "T-dependent fuel pin matching netflow's Fink-UO2 + He-gap + Zr-clad + gray radiation.

   Same node topology as FuelPinConst (centerline → pellet_surface →
   clad_inner → clad_outer) but:
     * pellet/gap-cond/clad conductivities are evaluated at LAYER-MEAN
       temperature (T_a + T_b)/2 — same convention netflow uses;
     * gap heat = parallel gas-conduction + gray-body radiation;
     * exposes per-node temperatures as monitor outputs.

   No internal convection: the clad_outer HeatPort is the external coupling
   point. Slice 4 wires it to ForcedConvection.
  "
  import Modelica.Constants.pi;
  import Modelica.Units.SI;

  // geometry / power (defaults = netflow quick-start)
  parameter SI.Radius r_pellet = 4.10e-3;
  parameter SI.Length gap_thickness = 0.085e-3;
  parameter SI.Radius r_clad_outer = 4.75e-3;
  parameter SI.Length L = 1.0;
  parameter Real q_lin(final unit = "W/m") = 18000.0;
  parameter Real gap_emissivity = 0.85
    "Effective emissivity for pellet ↔ clad radiation (0 disables radiation)";

  final parameter SI.Radius r_clad_inner = r_pellet + gap_thickness;
  final parameter SI.Power Q_total = q_lin * L;
  final parameter SI.Area A_gap = 2 * pi * r_pellet * L;
  final parameter Real sigma_SB(final unit = "W/(m2.K4)") = 5.670374419e-8;

  // exposed nodal temperatures (the 4 unknowns of this nonlinear system)
  SI.Temperature T_centerline(start = 1200.0);
  SI.Temperature T_pellet_surface(start = 830.0);
  SI.Temperature T_clad_inner(start = 635.0);
  SI.Temperature T_clad_outer(start = 610.0);

  // heat flows (a → b positive)
  SI.HeatFlowRate Q_pellet "centerline → pellet_surface";
  SI.HeatFlowRate Q_gap_cond "pellet_surface → clad_inner via He conduction";
  SI.HeatFlowRate Q_gap_rad  "pellet_surface → clad_inner via gray radiation";
  SI.HeatFlowRate Q_clad "clad_inner → clad_outer";

  // monitor aliases (clearer column names in the .mat)
  SI.Temperature T_centerline_K = T_centerline;
  SI.Temperature T_pellet_surface_K = T_pellet_surface;
  SI.Temperature T_clad_inner_K = T_clad_inner;
  SI.Temperature T_clad_outer_K = T_clad_outer;

  Modelica.Thermal.HeatTransfer.Interfaces.HeatPort_b clad_outer
    "External coupling port; T = T_clad_outer, Q_flow = heat leaving the clad";
equation
  // ---- Pellet (solid-cylinder uniform-generation analytic closed form) -----
  // R_eff = 1/(4 pi k L); flux = 4 pi k(Tmean) L (T_cl - T_ps)
  Q_pellet = 4 * pi * Materials.k_UO2(0.5 * (T_centerline + T_pellet_surface))
             * L * (T_centerline - T_pellet_surface);

  // ---- Gap (gas conduction || gray radiation) ------------------------------
  Q_gap_cond = 2 * pi * L * Materials.k_He(0.5 * (T_pellet_surface + T_clad_inner))
               / Modelica.Math.log(r_clad_inner / r_pellet)
               * (T_pellet_surface - T_clad_inner);
  Q_gap_rad  = sigma_SB * gap_emissivity * A_gap
               * (T_pellet_surface ^ 4 - T_clad_inner ^ 4);

  // ---- Clad (radial cylindrical conduction with T-dependent k_Zr) ----------
  Q_clad = 2 * pi * L * Materials.k_Zr(0.5 * (T_clad_inner + T_clad_outer))
           / Modelica.Math.log(r_clad_outer / r_clad_inner)
           * (T_clad_inner - T_clad_outer);

  // ---- Nodal balances ------------------------------------------------------
  // centerline: q_lin*L = Q_pellet
  Q_total = Q_pellet;
  // pellet_surface: Q_pellet = Q_gap_cond + Q_gap_rad
  Q_pellet = Q_gap_cond + Q_gap_rad;
  // clad_inner: Q_gap_cond + Q_gap_rad = Q_clad
  Q_gap_cond + Q_gap_rad = Q_clad;
  // clad_outer port: emits T = T_clad_outer; Q_flow leaves via the port
  clad_outer.T = T_clad_outer;
  clad_outer.Q_flow = -Q_clad;
end FuelPinTDep;
