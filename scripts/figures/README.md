# Figure scripts

Regenerate every figure in the report and paper (Python 3.10+, `matplotlib`, `opencv-python`, `numpy`, `torch`/`torchvision` for augmentations, and Graphviz `dot`).

| Script | Produces |
|---|---|
| `fundus_synth.py` | Synthetic (schematic) fundus images used in illustrations — not patient data |
| `figs.py` | Report charts: burden, anatomy, ICDR grades, optics, circuit, pre-processing, Gantt, risk map, cost |
| `diagrams.py` | Graphviz diagrams: block diagram, flowcharts, state machine, DFD, software architecture |
| `paperfigs.py` | Single-column (3.5″) figures for the IEEE paper |
| `resfigs.py` | Result figures from the 2026-10-31 training run |
| `preproc_code.py` | Shared pre-processing functions |

Note: output paths inside the scripts point to the original build folders — edit `OUT` at the top of each script.
