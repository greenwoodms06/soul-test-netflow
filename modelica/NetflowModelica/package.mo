within ;
package NetflowModelica "Idiomatic Modelica reimplementation of the netflow thermal chain"
  extends Modelica.Icons.Package;

  annotation (
    version="0.1.0",
    uses(Modelica(version="4.1.0")),
    Documentation(info="<html>
<p>Third leg of a paradigm triangulation (netflow Python &rarr; soultest-julia MTK &rarr; this).
Built on Modelica Standard Library + <code>Modelica.Media.Water.StandardWater</code>
(IAPWS-IF97). Abstraction layer named in <code>../docs/adr/0001</code>.</p>

<p>Bounded scope: fuel pin &rarr; coolant channel &rarr; coupled chain; steady then
transient. Not a TRANSFORM-equivalent library; one chain.</p>
</html>"));
end NetflowModelica;
