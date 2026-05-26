---
id: godfrey-2014-vera-spec
csl: references.json#godfrey-2014-vera-spec
access: public
retrieved: 2026-05-20
file: godfrey-2014-vera-spec.pdf      # extracted text: godfrey-2014-vera-spec.txt
grounds:
  - netflow VERA statepoint (geometry + operating point)
  - code-comparison-not-validation framing
  - derived Doppler reference
key-values:
  - value: '"no reference solution exists for this problem at this time"'
    defines: status of Problems 6 and 7 — inputs only, no benchmark truth
    status: verified
    locus: pp. 79, 81
  - value: pellet OD 0.8192 cm; clad OD 0.95 cm; gap 84 um; pitch 1.26 cm; active 365.76 cm
    defines: Westinghouse 17x17 geometry (P6 = P3 geometry)
    status: verified
    locus: Table 1
  - value: inlet 565 K; 15.51 MPa; 1300 ppm; 3.10 wt%; 17.67 MW/assembly; 85.98 kg/s
    defines: Problem 6 operating point (97.4% in fuel, 9% bypass)
    status: verified
    locus: Tables 18, P6-1
  - value: -2 to -2.5 pcm/K
    defines: fuel-temperature Doppler coefficient, fresh 3.10 wt% UO2
    status: derived-by-us
    locus: from P1/P2 KENO-VI eigenvalues, Tables P1-5, P2-5
related: [[kelly-2017-mc21-ctf-vera]], [[aviles-2017-mc21-cobra-ie]]
---
The authoritative VERA benchmark specification. Defines inputs for the progression
problems and states that Problems 6 and 7 have no reference solution — the fact
that reframed netflow's "validation" as a code-to-code comparison. Establishes the
exact geometry and operating point we run; provides reference KENO-VI eigenvalues
for Problems 1-5 (from which the Doppler coefficient is derived). Does NOT contain
absolute P6/P7 fuel or coolant results — those live only in the code-solution
papers ([[kelly-2017-mc21-ctf-vera]], [[aviles-2017-mc21-cobra-ie]]).
