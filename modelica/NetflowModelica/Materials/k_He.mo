within NetflowModelica.Materials;

function k_He "Helium gas-gap thermal conductivity, 200-1500 K"
  input Modelica.Units.SI.Temperature T;
  output Modelica.Units.SI.ThermalConductivity k;
algorithm
  k := 2.682e-3 * T ^ 0.71;
  annotation (Inline = true);
end k_He;
