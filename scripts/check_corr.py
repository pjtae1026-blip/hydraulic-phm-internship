import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src.data_loader import load_all_sensors, get_data_dir
import pandas as pd

data_dir = get_data_dir()
sensors = load_all_sensors(data_dir)

pressure = ['PS1','PS2','PS3','PS4','PS5','PS6']
means = {}
for ps in pressure:
    means[ps] = sensors[ps].mean(axis=1)
mean_df = pd.DataFrame(means)
corr = mean_df.corr()

print("Full Correlation Matrix:")
print(corr.round(4).to_string())
print()
for ps in pressure:
    print(f"  PS4 vs {ps}: r = {corr.loc['PS4', ps]:.4f}")
print()
print(f"  PS1 vs PS2: r = {corr.loc['PS1','PS2']:.4f}")
print(f"  PS5 vs PS6: r = {corr.loc['PS5','PS6']:.4f}")
print(f"  PS3 vs PS1: r = {corr.loc['PS3','PS1']:.4f}")
print(f"  PS3 vs PS2: r = {corr.loc['PS3','PS2']:.4f}")
print(f"  PS3 vs PS5: r = {corr.loc['PS3','PS5']:.4f}")
print(f"  PS1 vs PS5: r = {corr.loc['PS1','PS5']:.4f}")
print(f"  PS2 vs PS5: r = {corr.loc['PS2','PS5']:.4f}")
