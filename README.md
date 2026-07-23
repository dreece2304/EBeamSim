# EBL PSF Simulation

Geant4-based Monte Carlo simulation of electron-beam lithography point spread functions (PSF).
You pick a resist material and beam energy, it simulates electron scattering in the resist/substrate
stack, and produces a PSF file you can import into **BEAMER** for proximity effect correction.

Validated at 100 keV on Si against published proximity parameters
(β ≈ 29 µm vs. literature 30 ± 3 µm; backscatter energy fraction ≈ 0.55).

---

## Quick start (machine already set up)

If you're on the shared lab PC or another machine where this repo is already built:

```bash
# Windows: open a WSL terminal first (search "Ubuntu" or "WSL" in the Start menu)
cd ~/projects/research/ebl-simulation   # or wherever the repo lives
./run_gui.sh
```

Then in the GUI:

1. **Resist Properties tab** — pick a preset (PMMA, HSQ, Alucone, Sn-MLD, Zincone) or type a
   composition like `Sn:1,C:8,H:8,O:4` (decimals allowed, e.g. `O:1.5`), set thickness and density.
2. **Beam Parameters tab** — set energy (typically 100 keV). **Leave beam size at 0 nm** — the PSF
   must be a point-source response; BEAMER applies your tool's beam blur separately.
3. **Simulation tab** — set event count (100k is a good default; more events = smoother tail),
   then click **Run Simulation**.
4. When the run finishes, results land in `output/` with descriptive names, and the PSF is plotted
   in the **1D PSF Visualization** tab.

### Getting the BEAMER file

The simulation writes a BEAMER-ready file directly: `output/<name>_beamer.dat`
(two columns: radius in **µm**, PSF normalized to peak = 1; `#` comment header).
Import this file in BEAMER as a numerical PSF.

You can also regenerate/post-process one from any PSF CSV via the **BEAMER** button in the
1D PSF tab (adds tail smoothing/extrapolation). Both writers produce the same format and agree
numerically.

---

## Install from scratch (new PC)

Tested on Ubuntu under WSL2 (Windows 11) and native Linux.

### 1. WSL2 (Windows only)

```powershell
wsl --install -d Ubuntu
```

Reboot, open Ubuntu. Windows 11's WSLg displays Linux GUI apps automatically — no X server needed.

### 2. System packages

```bash
sudo apt update
sudo apt install -y build-essential cmake libexpat1-dev qtbase5-dev libqt5opengl5-dev \
                    libxerces-c-dev libgl1-mesa-dev
```

### 3. Geant4 (11.3+, with Qt visualization)

```bash
cd ~
wget https://gitlab.cern.ch/geant4/geant4/-/archive/v11.3.0/geant4-v11.3.0.tar.gz
tar xzf geant4-v11.3.0.tar.gz && mkdir geant4-build && cd geant4-build
cmake ../geant4-v11.3.0 \
  -DCMAKE_INSTALL_PREFIX=$HOME/geant4-install \
  -DGEANT4_INSTALL_DATA=ON -DGEANT4_USE_QT=ON -DGEANT4_USE_OPENGL_X11=ON \
  -DCMAKE_BUILD_TYPE=Release
make -j$(nproc) && make install
echo 'source $HOME/geant4-install/bin/geant4.sh' >> ~/.bashrc && source ~/.bashrc
```

(This takes a while. Any Geant4 ≥ 11.x install works — point CMake at it with
`-DGeant4_DIR=/path/to/lib/cmake/Geant4` if it's elsewhere.)

### 4. This project

```bash
git clone <repo-url> ebl-simulation && cd ebl-simulation

# C++ simulation
mkdir -p build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)
cd ..

# Python GUI environment
conda env create -f environment.yml     # creates env "ebl-sim"
./run_gui.sh
```

No conda? `pip install -r scripts/gui/requirements.txt` into any Python ≥ 3.10 works too.

---

## Command line (no GUI)

```bash
./build/bin/ebl_sim macros/runs/run.mac          # standard 100 keV PSF run
./build/bin/ebl_sim -t 8 macros/runs/run.mac     # 8 threads
./build/bin/ebl_sim -n 500000 -m macros/runs/run.mac  # override event count
```

Ready-made per-material macros are in `macros/reference_psfs/` — copy one, edit the three
`/det/set...` lines for your material, and run it. **Detector settings must come before
`/run/initialize`** in a macro (see any `ref_*.mac` for the pattern), and `/gun/beamSize` must
be `0 nm` for a BEAMER PSF.

To (re)build the reference PSF library used by the GUI's comparison feature:

```bash
./scripts/generate_reference_psfs.sh    # outputs to data/reference_psfs/
```

## Output files

| File | Contents |
|---|---|
| `*_psf.csv` / `ebl_psf_data.csv` | Radial PSF: radius (nm), energy density (eV/nm²/e⁻), log-binned 0.5 nm – 100 µm |
| `*_beamer.dat` | **BEAMER import file**: radius (µm), PSF normalized to peak = 1 |
| `*_summary.txt` | Run parameters, energy accounting (incl. energy beyond the 100 µm PSF radius) |
| `*_psf2d.csv` | Depth × radius energy map for visualization |

GUI runs write to `output/` in the repo (gitignored). CLI runs write to the current directory
unless the macro sets `/ebl/output/setDirectory`.

## Troubleshooting

- **"ebl_sim not found" in the GUI** — build it (`mkdir -p build && cd build && cmake .. -DCMAKE_BUILD_TYPE=Release && make -j8`),
  or point the GUI at an existing binary via *File > Select Executable*.
- **GUI won't display (WSL2)** — on Windows 11, WSLg should just work. On Windows 10, run an
  X server (VcXsrv) and `export DISPLAY=:0` before `./run_gui.sh`.
- **`PySide6 not available`** — `conda env create -f environment.yml`, then rerun `./run_gui.sh`.
- **Runs are slow** — use more threads (`-t 8` on the CLI, or the Threads setting in the GUI);
  high-Z resists (Sn, Zn) are inherently slower due to finer physics cuts.
- **Progress bar not moving** — check the Output Log tab; the run may still be initializing
  (Geant4 physics tables take ~10–30 s at startup).

## Project layout

```
src/          Geant4 C++ (geometry, physics, beam, scoring)
apps/ebl_sim/ CLI entry point
macros/       Geant4 macro files (runs/, reference_psfs/, benchmarks/)
scripts/gui/  PySide6 GUI (entry point: ebl_gui.py; launch via ./run_gui.sh)
output/       Simulation outputs (gitignored)
data/         Reference PSF library
```

## License

MIT — see [LICENSE.md](LICENSE.md).
