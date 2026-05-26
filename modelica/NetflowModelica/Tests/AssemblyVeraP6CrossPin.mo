within NetflowModelica.Tests;

model AssemblyVeraP6CrossPin
  "AssemblyVeraP6 + cross-pin conduction (step 3a of the unfreeze).

   Adds ThermalConductors between adjacent fuel pin CLAD OUTERS at the same
   axial level, indexed by 17×17-grid adjacency. (FuelPinConst exposes
   `clad_outer` as the external HeatPort; the centerline is internal and
   not directly connectable. Clad-outer-to-clad-outer is the physically
   meaningful pin-to-pin conduction path through coolant gap + clad metal.)

   Physically the path between adjacent UO2 pellets through 5 mm of coolant +
   2 mm of clad on each side is weak — the dominant heat-transfer mode is
   radiation — but topologically this widens the Jacobian band by the
   slice-10 pattern at assembly scale.

   What this tests:
     - Does Dymola's solver still converge with cross-pin conductance edges?
     - Does the compile-time wall move when generated C reflects the cross-
       coupling? (Per ideas.md / COMPARISON.md §9 candidate #2.)
     - Do peak T_centerline values DROP slightly when cross-pin transport
       smooths the radial temperature distribution?

   MSL-only (ADR-0002): uses `Modelica.Thermal.HeatTransfer.Components.
   ThermalConductor` and the existing slice-1 closures. No third-party
   library imports.
  "
  extends AssemblyVeraP6;

  // Cross-pin conduction parameter — small by default (weak coupling).
  // For a stress test that exercises the topology, raise this to a larger
  // value; the topology cost is independent of the magnitude.
  parameter Modelica.Units.SI.ThermalConductance G_cross = 0.05
    "Cross-pin conductance per axial slice (W/K). 0.05 W/K ≈ weak coupling
     representing radiative + coolant-mediated transport; raise for stress
     tests of solver topology.";

  parameter Integer n_side = integer(sqrt(n_pin))
    "Grid side (17 for the canonical assembly)";

  // Horizontal (left-right) and vertical (up-down) connectors per axial slice.
  // Adjacency-by-construction: pin index ip = (i-1)*n_side + j, so the
  // right-neighbor of (i, j) is (i, j+1) with ip+1; the down-neighbor is
  // (i+1, j) with ip+n_side. Two arrays of conductors total.
  Modelica.Thermal.HeatTransfer.Components.ThermalConductor crossH[
    n_side, n_side - 1, n_axial](each G = G_cross)
    "Horizontal (j ↔ j+1) cross-pin conductors";
  Modelica.Thermal.HeatTransfer.Components.ThermalConductor crossV[
    n_side - 1, n_side, n_axial](each G = G_cross)
    "Vertical (i ↔ i+1) cross-pin conductors";

equation
  // Connect horizontal neighbors at each axial level.
  for i in 1:n_side loop
    for j in 1:(n_side - 1) loop
      for iz in 1:n_axial loop
        connect(pins[(i - 1) * n_side + j, iz].clad_outer,
                crossH[i, j, iz].port_a);
        connect(crossH[i, j, iz].port_b,
                pins[(i - 1) * n_side + j + 1, iz].clad_outer);
      end for;
    end for;
  end for;
  // Connect vertical neighbors at each axial level.
  for i in 1:(n_side - 1) loop
    for j in 1:n_side loop
      for iz in 1:n_axial loop
        connect(pins[(i - 1) * n_side + j, iz].clad_outer,
                crossV[i, j, iz].port_a);
        connect(crossV[i, j, iz].port_b,
                pins[i * n_side + j, iz].clad_outer);
      end for;
    end for;
  end for;

  annotation (experiment(StopTime = 1.0));
end AssemblyVeraP6CrossPin;
