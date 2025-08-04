# GUI Tab Mockups

## Tab 2: PSF Generation

```
┌─────────────────────────────────────────────────┐
│ PSF Generation                                  │
├─────────────────────────────────────────────────┤
│                                                 │
│ Generate Point Spread Function from single      │
│ electron spot simulation.                       │
│                                                 │
│ ┌─────────────────────────────────────────┐   │
│ │ Simulation Parameters                    │   │
│ ├─────────────────────────────────────────┤   │
│ │ Number of Events: [100,000    ] ▼       │   │
│ │                                         │   │
│ │ Output Filename: [psf_data.csv     ]    │   │
│ └─────────────────────────────────────────┘   │
│                                                 │
│ [    Generate PSF    ] Status: Ready           │
│                                                 │
│ ▓▓▓▓▓▓▓▓▓▓░░░░░░░░░ 50%                       │
│                                                 │
│ ┌─────────────────────────────────────────┐   │
│ │ PSF Preview                             │   │
│ │  ╱╲                                     │   │
│ │ ╱  ╲___                                │   │
│ │        ───___________                   │   │
│ └─────────────────────────────────────────┘   │
│                                                 │
│ ✓ PSF generated successfully                    │
│ Peak at: 0 nm, FWHM: 45 nm                    │
│                                                 │
│ [ → Next: Pattern Design ]                     │
└─────────────────────────────────────────────────┘
```

## Tab 3: Pattern Design

```
┌─────────────────────────────────────────────────┐
│ Pattern Design                                  │
├─────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────┐   │
│ │ Pattern Configuration                    │   │
│ ├─────────────────────────────────────────┤   │
│ │ Pattern Type: [Square      ▼]           │   │
│ │ Pattern Size: [1.0    ] μm              │   │
│ │ Center X,Y:   [0.0] [0.0] μm           │   │
│ └─────────────────────────────────────────┘   │
│                                                 │
│ ┌─────────────────────────────────────────┐   │
│ │ JEOL Parameters                         │   │
│ ├─────────────────────────────────────────┤   │
│ │ EOS Mode: [Mode 3 (500μm) ▼]           │   │
│ │ Shot Pitch: [4     ]                    │   │
│ │ Beam Current: [2.0   ] nA               │   │
│ │ Base Dose: [400    ] μC/cm²            │   │
│ │                                         │   │
│ │ Exposure Grid: 4 nm                     │   │
│ │ Shots Required: 62,500                  │   │
│ └─────────────────────────────────────────┘   │
│                                                 │
│ ┌─────────────────────────────────────────┐   │
│ │ Pattern Preview                         │   │
│ │ ┌─────────────┐                        │   │
│ │ │             │  ← 1 μm →              │   │
│ │ │   Square    │                        │   │
│ │ │             │                        │   │
│ │ └─────────────┘                        │   │
│ └─────────────────────────────────────────┘   │
│                                                 │
│ [ → Next: Proximity Analysis ]                 │
└─────────────────────────────────────────────────┘
```

## Tab 4: Proximity Analysis

```
┌─────────────────────────────────────────────────┐
│ Proximity Analysis                              │
├─────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────┐   │
│ │ PSF Model                               │   │
│ ├─────────────────────────────────────────┤   │
│ │ [Load PSF from File] [Use Theoretical]  │   │
│ │                                         │   │
│ │ ✓ PSF Loaded: psf_data.csv             │   │
│ │ α=0.3, β=0.7, σf=20nm, σb=5μm         │   │
│ └─────────────────────────────────────────┘   │
│                                                 │
│ ┌─────────────────────────────────────────┐   │
│ │ Dose Modulation                         │   │
│ ├─────────────────────────────────────────┤   │
│ │ Interior: [1.00 ] ████████████ 100%    │   │
│ │ Edge:     [0.85 ] ████████░░░  85%     │   │
│ │ Corner:   [0.75 ] ███████░░░░  75%     │   │
│ │                                         │   │
│ │ Presets: [None] [Light] [Medium] [Heavy]│   │
│ └─────────────────────────────────────────┘   │
│                                                 │
│ ┌─────────────────────────────────────────┐   │
│ │ Effect Preview                          │   │
│ ├─────────────┬───────────────────────────┤   │
│ │ No Correct. │ With Correction          │   │
│ │ ░░▓▓▓▓▓▓░░ │ ░░▒▒▒▒▒▒░░              │   │
│ │ ░▓▓███▓▓░ │ ░▒▒▒▒▒▒▒▒░              │   │
│ │ ░▓███████▓░ │ ░▒▒▒▒▒▒▒▒░              │   │
│ │ ░▓▓███▓▓░ │ ░▒▒▒▒▒▒▒▒░              │   │
│ │ ░░▓▓▓▓▓▓░░ │ ░░▒▒▒▒▒▒░░              │   │
│ │             │                          │   │
│ │ Overexposed │ Uniform dose             │   │
│ │ edges       │                          │   │
│ └─────────────┴───────────────────────────┘   │
│                                                 │
│ [ → Next: Run Simulation ]                     │
└─────────────────────────────────────────────────┘
```

## Tab 5: Run Simulation

```
┌─────────────────────────────────────────────────┐
│ Run Simulation                                  │
├─────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────┐   │
│ │ Simulation Mode                         │   │
│ ├─────────────────────────────────────────┤   │
│ │ ○ PSF Generation (Single Spot)          │   │
│ │ ● Pattern Simulation                    │   │
│ │                                         │   │
│ │ Current Configuration:                  │   │
│ │ • 1.0 μm square pattern                │   │
│ │ • 62,500 shots                         │   │
│ │ • Proximity correction enabled         │   │
│ └─────────────────────────────────────────┘   │
│                                                 │
│ ┌─────────────────────────────────────────┐   │
│ │ Physics Settings                        │   │
│ ├─────────────────────────────────────────┤   │
│ │ ☑ Fluorescence  ☑ Auger Cascades       │   │
│ └─────────────────────────────────────────┘   │
│                                                 │
│ ╔═══════════════════════════════════════╗   │
│ ║      RUN SIMULATION                   ║   │
│ ╚═══════════════════════════════════════╝   │
│                                                 │
│ Progress: ▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░ 60%          │
│ Events: 37,500 / 62,500                        │
│ Time Elapsed: 0:24                             │
│ Est. Remaining: 0:16                           │
│                                                 │
│ Status: Processing events...                   │
│                                                 │
│ [ View Output Log ]                            │
└─────────────────────────────────────────────────┘
```

This organization would make the workflow much clearer:
1. Set up your sample and beam
2. Generate a PSF 
3. Design your pattern
4. Apply proximity correction
5. Run the simulation
6. View all results in one place

The key improvements are:
- Logical flow from left to right
- Related controls grouped together
- Clear separation between PSF generation and pattern simulation
- Visual feedback showing what mode you're in
- Next step guidance