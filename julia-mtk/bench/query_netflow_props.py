"""Extract netflow's water properties + the convection h for the quick-start case,
so the MTK port can use the SAME Dittus-Boelter physics without CoolProp.jl.
Reads frozen netflow; does not modify it.
"""
import sys, math
sys.path.insert(0, "/home/fig/soultest")
from netflow.plugins.thermal import CoolPropFluid, ForcedConvection

P = 15.5e6
fluid = CoolPropFluid("Water", default_P=P)

print("# water @ 15.5 MPa  (T[K]  rho  mu  k_f  Pr)")
for T in (560.0, 580.0, 600.0, 620.0):
    print(f"{T:7.1f}  rho={fluid.rho(T,P):8.3f}  mu={fluid.mu(T,P):.6e}  "
          f"k={fluid.k(T,P):.5f}  Pr={fluid.Pr(T,P):.5f}")

# reconstruct the quick-start convection edge and report its h at the solution
edge = ForcedConvection("clad_outer", "coolant", fluid=fluid,
                        mdot=0.30, D_h=12.0e-3, A_ht=3.14e-2)
T_clad_outer, T_cool = 611.7027, 593.0
T_film = 0.5 * (T_clad_outer + T_cool)
h = edge._h(T_clad_outer, T_cool)
A_xs = math.pi * (12.0e-3**2) / 4
print(f"\nT_film = {T_film:.3f} K")
print(f"A_xs   = {A_xs:.6e} m^2  (default pi*D_h^2/4)")
print(f"h(T_film) = {h:.3f} W/m^2-K")
print(f"hA = {h*3.14e-2:.4f} W/K ;  Q/(hA) = {18000/(h*3.14e-2):.3f} K  (netflow film drop = 18.70 K)")
