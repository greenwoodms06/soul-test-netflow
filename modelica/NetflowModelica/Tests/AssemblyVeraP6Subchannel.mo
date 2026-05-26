within NetflowModelica.Tests;

model AssemblyVeraP6Subchannel
  "AssemblyVeraP6 with subchannel cross-flow (step 3c of the unfreeze).

   Replaces the per-channel CoolantCell stack with CoolantCellSub cells that
   expose 4 lateral ports per axial level. Adjacent cells are connected
   directly (no orifices, no momentum) — the slice-4 'pressure equal across'
   choice generalized to lateral transport.

   Each axial level has the cross-flow lattice wired by connecting:
     - cells[i, j, iz].port_lat_xR ↔ cells[i, j+1, iz].port_lat_xL   (horizontal)
     - cells[i, j, iz].port_lat_yD ↔ cells[i+1, j, iz].port_lat_yU   (vertical)
   Boundary lateral ports (at the grid edges) are left open — m_flow forced
   to zero by the unmodeled-pressure default.

   What this tests:
     - Does Modelica's stream-connector formalism solve the 17×17 subchannel
       topology at MSL primitives only?
     - Does the no-momentum lateral closure produce sensible mass redistribution
       under non-uniform power?

   MSL-only (ADR-0002): CoolantCellSub built from Modelica.Fluid.Interfaces.

   PHYSICS NOTE: With no momentum and no orifice loss, lateral flow is
   determined purely by mass balance + pressure equality. Under uniform power
   and uniform inlet flow, lateral m_flows = 0 by symmetry. Under radial
   peaking (q_lin_factor[ip] != 1), the system may be under-determined —
   if Dymola objects, step 3c will need explicit SimpleGenericOrifice loss
   elements (deferred until that finding lands).
  "
  extends Modelica.Icons.Example;

  import Modelica.Constants.pi;
  import Modelica.Units.SI;

  replaceable package Medium = Modelica.Media.Water.StandardWater
    constrainedby Modelica.Media.Interfaces.PartialMedium;

  parameter Integer n_side = 17;
  final parameter Integer n_pin = n_side * n_side;
  parameter Integer n_axial = 30;
  parameter SI.Length L_total = 3.6576;
  final parameter SI.Length dz = L_total / n_axial;

  parameter SI.MassFlowRate mdot_per_pin = 85.98 / 264.0;
  parameter SI.Pressure p_nom = 15.51e6;
  parameter SI.Temperature T_in = 565.0;

  parameter Real q_lin_avg(final unit = "W/m") = 17838.0;
  parameter Real q_lin_factor[n_side, n_side] = ones(n_side, n_side);

  parameter SI.Radius r_pellet = 4.096e-3;
  parameter SI.Length gap_thickness = 0.084e-3;
  parameter SI.Radius r_clad_outer = 4.75e-3;
  final parameter SI.Radius r_clad_inner = r_pellet + gap_thickness;

  parameter SI.ThermalConductivity k_fuel = 3.0;
  parameter SI.ThermalConductivity k_clad = 16.0;
  parameter SI.CoefficientOfHeatTransfer h_gap = 7500.0;
  parameter SI.CoefficientOfHeatTransfer h_conv = 30000.0;
  final parameter SI.ThermalResistance R_conv =
    1.0 / (2 * pi * r_clad_outer * h_conv * dz);

  Components.CoolantInlet inlets[n_side, n_side](
    redeclare each package Medium = Medium,
    each mdot = mdot_per_pin, each p_ref = p_nom, each T_in = T_in);
  Components.CoolantOutlet outlets[n_side, n_side](
    redeclare each package Medium = Medium,
    each p_set = p_nom, each T_ambient = T_in);
  Components.CoolantCellSub cells[n_side, n_side, n_axial](
    redeclare each package Medium = Medium,
    each p_start = p_nom, each T_start = T_in);

  parameter Real G_lat(unit = "kg/(s.Pa)") = 1e-5
    "Lateral flow conductance per orifice (kg/s per Pa). Defaults to a
     weak coupling — strong enough to make the system non-singular,
     weak enough that uniform-input cases recover symmetric solutions
     to within numerical noise.";

  Components.LateralFlowLink linksH[n_side, n_side - 1, n_axial](
    redeclare each package Medium = Medium, each G = G_lat);
  Components.LateralFlowLink linksV[n_side - 1, n_side, n_axial](
    redeclare each package Medium = Medium, each G = G_lat);

  Components.FuelPinConst pins[n_side, n_side, n_axial](
    q_lin = {{{q_lin_avg * q_lin_factor[i, j] for iz in 1:n_axial}
              for j in 1:n_side} for i in 1:n_side},
    each L = dz,
    each r_pellet = r_pellet, each gap_thickness = gap_thickness,
    each r_clad_outer = r_clad_outer,
    each k_fuel = k_fuel, each k_clad = k_clad, each h_gap = h_gap);

  Modelica.Thermal.HeatTransfer.Components.ThermalResistor convs[n_side, n_side, n_axial](
    each R = R_conv);

  // Diagnostic outputs
  SI.Temperature T_cool_exit[n_side, n_side] = {
    {cells[i, j, n_axial].T for j in 1:n_side} for i in 1:n_side};
  SI.Temperature T_cool_exit_max = max(T_cool_exit);
  SI.Temperature T_cool_exit_min = min(T_cool_exit);
  SI.Temperature T_cool_exit_spread = T_cool_exit_max - T_cool_exit_min;
  SI.Temperature T_centerline_hot = max({
    pins[i, j, iz].T_centerline_K
    for i in 1:n_side, j in 1:n_side, iz in 1:n_axial});
  SI.HeatFlowRate Q_total_assembly = q_lin_avg * L_total * sum(q_lin_factor);

equation
  for i in 1:n_side loop
    for j in 1:n_side loop
      // Inlet → first axial cell
      connect(inlets[i, j].port, cells[i, j, 1].port_a);
      // Axial chain
      for iz in 1:(n_axial - 1) loop
        connect(cells[i, j, iz].port_b, cells[i, j, iz + 1].port_a);
      end for;
      connect(cells[i, j, n_axial].port_b, outlets[i, j].port);

      // Pin-to-coolant
      for iz in 1:n_axial loop
        connect(pins[i, j, iz].clad_outer, convs[i, j, iz].port_a);
        connect(convs[i, j, iz].port_b, cells[i, j, iz].heat);
      end for;
    end for;
  end for;

  // Horizontal cross-flow (right ↔ link ↔ left of neighbour)
  for i in 1:n_side loop
    for j in 1:(n_side - 1) loop
      for iz in 1:n_axial loop
        connect(cells[i, j, iz].port_lat_xR, linksH[i, j, iz].port_a);
        connect(linksH[i, j, iz].port_b, cells[i, j + 1, iz].port_lat_xL);
      end for;
    end for;
  end for;
  // Vertical cross-flow (down ↔ link ↔ up of neighbour)
  for i in 1:(n_side - 1) loop
    for j in 1:n_side loop
      for iz in 1:n_axial loop
        connect(cells[i, j, iz].port_lat_yD, linksV[i, j, iz].port_a);
        connect(linksV[i, j, iz].port_b, cells[i + 1, j, iz].port_lat_yU);
      end for;
    end for;
  end for;

  annotation (experiment(StopTime = 1.0));
end AssemblyVeraP6Subchannel;
