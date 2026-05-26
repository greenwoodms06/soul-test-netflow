within NetflowModelica.Components;

block PointKinetics
  "Signal-domain point-kinetics with 1 delayed group + Doppler reactivity.

   Inputs:  T_fuel (RealInput, K)  — fuel-temperature feedback signal
   Outputs: power  (RealOutput, W) — instantaneous thermal power

   ρ(t)  = ρ_ext + α (T_fuel − T_ref)
   dn/dt = ((ρ − β)/Λ) n + λ C
   dC/dt = (β/Λ) n − λ C
   P(t)  = P0 · n(t)

   Crosses the signal/acausal boundary the same way MTK's Blocks library does:
   this block lives in the SIGNAL domain (RealInput/RealOutput); a
   PrescribedHeatFlow's signal input wires the power output to a HeatPort.

   DEBT: one delayed group; α/β/Λ illustrative for the slice-7 scenario.
  "
  extends Modelica.Blocks.Interfaces.SISO;
  // ^ provides RealInput u (renamed T_fuel via 'final equation' alias below)
  //   and RealOutput y (renamed power similarly). We rename for readability.

  parameter Real beta = 0.0065 "Delayed-neutron fraction";
  parameter Real Lambda(unit = "s") = 2e-5 "Prompt-neutron generation time";
  parameter Real lambda(unit = "1/s") = 0.08 "Decay constant of delayed group";
  parameter Real alpha_doppler(unit = "1/K") = -2.5e-5 "Doppler reactivity coefficient";
  parameter Real rho_ext = 1e-3 "Externally inserted reactivity";
  parameter Modelica.Units.SI.Temperature T_ref = 1253.0 "Reference fuel T (ρ_Doppler = 0)";
  parameter Modelica.Units.SI.Power P0 = 18000.0 "Reference thermal power at n=1";
  parameter Real n_start = 1.0 "Initial relative power";

  Real n(start = n_start, fixed = true) "relative neutron population";
  Real C(start = (beta / (Lambda * lambda)) * n_start, fixed = true) "delayed precursor";
  Real rho "total reactivity";
equation
  rho = rho_ext + alpha_doppler * (u - T_ref);
  der(n) = ((rho - beta) / Lambda) * n + lambda * C;
  der(C) = (beta / Lambda) * n - lambda * C;
  y = P0 * n;
end PointKinetics;
