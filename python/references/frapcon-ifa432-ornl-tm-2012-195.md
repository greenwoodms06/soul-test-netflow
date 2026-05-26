---
id: frapcon-ifa432-ornl-tm-2012-195
csl: references.json#frapcon-ifa432-ornl-tm-2012-195
access: public               # openly on OSTI / info.ornl.gov
retrieved: 2026-05-20
file: frapcon-ifa432-ornl-pub36515.pdf   # extracted text: ...txt (67 pp)
grounds:
  - "POTENTIAL netflow fuel-temperature VALIDATION (not yet performed)"
key-values:
  - value: IFA-432 Rods 1/2/3/5 measured fuel CENTERLINE temperature vs linear heat rate (LHGR) and burnup
    defines: thermocouple-measured fuel centerline temperature, Halden BWR test rods
    status: figure-derived          # plotted (Figs B.1-B.x), measured-vs-FRAPCON
    locus: Sec. 2.4 / Appendix B
related: [[ifa432-final-data-report]], [[ifpe-ifa432-nea1488]], [[godfrey-2014-vera-spec]]
---
**The first netflow-RELEVANT measured dataset.** Unlike the full-core VERA/WBN1
references, this is a single instrumented fuel rod: measured fuel CENTERLINE
temperature vs linear heat rate (beginning-of-life and with burnup) for Halden
IFA-432 rods, exactly the quantity netflow's fuel-pin model computes. ORNL FRAPCON
analysis report (ORNL/TM-2012/195). The measured points are in figures (Appendix
B); the clean tabulated raw data lives in the IFPE dataset
[[ifpe-ifa432-nea1488]] (NEA member access) and the primary
[[ifa432-final-data-report]]. This is the path from "code comparison" to a real
fuel-temperature validation for netflow — not yet performed.
