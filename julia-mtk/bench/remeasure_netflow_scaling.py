"""Re-measure netflow's native scaling (resistor mesh) on THIS machine — grounds
the performance comparison vs MTK instead of trusting README numbers. Reads frozen
netflow. Linear mesh: pure sparse-assembly + factorization cost, no symbolic/JIT
stage (the structural contrast with MTK)."""
import sys
sys.path.insert(0, "/home/fig/soultest")
from netflow.bench.resistor_mesh import run

# 100 → ~90k nodes; spans MTK's wall and netflow's claimed 44k/8s regime
run(sizes=[10, 32, 100, 200, 300])
