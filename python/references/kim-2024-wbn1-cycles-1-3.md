---
id: kim-2024-wbn1-cycles-1-3
csl: references.json#kim-2024-wbn1-cycles-1-3
access: provided-by-body          # NRC ADAMS ML25113A083 / ORNL TM; provided by the Body 2026-05-20
retrieved: 2026-05-20
file: nrc-ml25113a083.pdf         # extracted text: nrc-ml25113a083.txt (111 pp)
grounds: []                       # CONTEXT — full-core measured neutronics, not netflow-reproducible
key-values:
  - value: 1291 ppm (meas) vs 1281 (calc)
    defines: WBN1 HZP critical boron concentration (measured vs Polaris-PARCS)
    status: verified
    locus: Table 3.8
  - value: -2.17 pcm/F (meas) vs -3.39 (calc)
    defines: WBN1 isothermal temperature coefficient (ITC)
    status: verified
    locus: Table 3.8
  - value: -10.77 pcm/ppm (meas) vs -10.18 (calc)
    defines: WBN1 boron worth
    status: verified
    locus: Table 3.8
related: [[kim-2023-wbn1-polaris-parcs]], [[godfrey-2014-vera-spec]]
---
The fuller technical-report version (ORNL/TM-2023/2981, NRC ADAMS ML25113A083) of
the [[kim-2023-wbn1-polaris-parcs]] conference paper: WBN1 Cycles 1-3 with SCALE
6.3/Polaris-PARCS, including MEASURED HZP physics-test data (critical boron, ITC,
control-bank and boron worths, 3D flux maps) versus calculation. Genuine measured
reference truth — but full-core neutronics, which netflow's verification-grade
1-group bare-slab cannot reproduce. CONTEXT, not a netflow validation point.
