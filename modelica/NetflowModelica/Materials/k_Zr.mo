within NetflowModelica.Materials;

function k_Zr "Zircaloy-4 clad thermal conductivity, 250-1400 K"
  input Modelica.Units.SI.Temperature T;
  output Modelica.Units.SI.ThermalConductivity k;
algorithm
  k := 12.6 + 0.0048 * (T - 300.0);
  annotation (Inline = true);
end k_Zr;
