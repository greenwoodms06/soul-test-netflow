within NetflowModelica.Materials;

function k_UO2 "Fink-fit UO2 thermal conductivity, 300-3000 K (netflow parity)"
  input Modelica.Units.SI.Temperature T;
  output Modelica.Units.SI.ThermalConductivity k;
algorithm
  k := 1.0 / (0.0375 + 2.165e-4 * T)
       + 4.715e9 / (T * T) * Modelica.Math.exp(-16361.0 / T);
  annotation (Inline = true);
end k_UO2;
