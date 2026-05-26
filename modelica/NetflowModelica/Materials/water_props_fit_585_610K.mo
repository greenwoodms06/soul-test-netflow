within NetflowModelica.Materials;

package water_props_fit_585_610K
  "Quadratic fits of CoolProp HEOS water properties over 585-610 K, p~15.5 MPa.

   Identical to the fits the Julia attempt (soultest-julia, slice4) used to
   substitute for IAPWS-IF97 in MTK where no IF97 binding was available.
   Reproduced here ONLY so the Modelica build can demonstrate the same code-
   comparison agreement against netflow when the property formulation is the
   same — the IF97-vs-HEOS difference is what otherwise drives slice 4's
   sub-K disagreement.

   These functions are NOT the recommended default — the ForcedConvection
   component uses the supplied Medium (default IF97) unless useFittedProps
   is explicitly set true.
  "
  extends Modelica.Icons.UtilitiesPackage;
  // DEBT: validity range 585-610 K only. Outside this range these fits
  // silently extrapolate. Slice 4 stays within range by construction (T_film
  // ~ 602 K); reusing this package elsewhere needs a range check by caller.

  function mu "Dynamic viscosity quadratic fit, valid 585-610 K"
    input Modelica.Units.SI.Temperature T;
    output Modelica.Units.SI.DynamicViscosity mu;
  algorithm
    mu := -2.0223992769e-9 * T ^ 2 + 1.9761159982e-6 * T - 3.8012592650e-4;
    annotation (Inline = true);
  end mu;

  function k "Thermal conductivity quadratic fit, valid 585-610 K"
    input Modelica.Units.SI.Temperature T;
    output Modelica.Units.SI.ThermalConductivity k;
  algorithm
    k := -1.3080990232e-5 * T ^ 2 + 1.3581205087e-2 * T - 2.9242712999;
    annotation (Inline = true);
  end k;

  function Pr "Prandtl quadratic fit, valid 585-610 K"
    input Modelica.Units.SI.Temperature T;
    output Real Pr(unit = "1");
  algorithm
    Pr := 2.1996090686e-4 * T ^ 2 - 2.5487516332e-1 * T + 7.4721737357e1;
    annotation (Inline = true);
  end Pr;
end water_props_fit_585_610K;
