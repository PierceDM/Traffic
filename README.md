# Traffic Signal Simulator

A comprehensive traffic simulation system with visual demonstration of traffic interactions and signal timing optimization. Built to help determine optimal traffic signal configurations for different conditions.

## Features

### Visual Simulation
- Real-time 2D visualization of traffic flow
- Color-coded vehicles (cars in various colors, trucks in gray)
- Animated traffic signals with proper state transitions
- Crosswalk markings and road lane indicators

### City Building
- **Manual Building**: Click to place roads, intersections, and signals
- **Random Generation**: Generate realistic city grid layouts
- **OpenStreetMap Import**: Import location-inspired layouts
- **Save/Load**: Export and import your layouts as JSON

### Traffic Signal Types (US Standard)
- Traffic Lights (red/yellow/green with configurable timing)
- Stop Signs
- Four-Way Stops
- Yield Signs
- Flashing Yellow Lights
- Flashing Red Lights
- Roundabouts
- Pedestrian Signals

### Adjustable Conditions
All sliders can be collapsed/hidden when not needed:

**Weather Conditions:**
- Clear, Rain, Heavy Rain, Snow, Fog, Ice
- Each affects reaction time and max speed based on research data

**Time of Day:**
- Morning Rush, Midday, Evening Rush, Evening, Night, Late Night
- Affects driver behavior and reaction times

**Distraction Level:**
- None, Light, Moderate, Heavy
- Simulates phone use, eating, etc.

**Vehicle Settings:**
- Traffic Density (how many vehicles spawn)
- Heavy Vehicle Ratio (semi-trucks vs passenger cars)
- Pedestrian Enable/Disable
- Tourism Area Pedestrian Rate

### Signal Timing Controls
- Green time for North/South direction (10-120 seconds)
- Green time for East/West direction (10-120 seconds)
- Yellow light duration (2-8 seconds)
- All-red clearance interval (1-5 seconds)
- Apply to all signals or edit individual intersections

### Analytics & Comparison
- **Real-time Statistics:**
  - Active vehicles
  - Completed trips (throughput)
  - Average wait time
  - Maximum wait time
  - Total stopped time
  - Average speed
  - Efficiency percentage

- **Simulation Snapshots:** Save current simulation state for comparison
- **Side-by-Side Comparison:** Compare multiple configurations
- **Ranking:** Automatically rank by efficiency (lowest wait time)
- **CSV Export:** Export all comparison data for external analysis

### Tourism Areas
- Mark intersections as tourism areas
- Increased pedestrian crossing frequency
- Adjustable pedestrian delay multiplier
- Visual indicator (purple-tinted blocks)

## Research-Based Defaults

The simulator uses research-backed default values:

### Reaction & Acceleration Times
| Parameter | Passenger Car | Semi-Truck (80,000 lbs) |
|-----------|---------------|-------------------------|
| Perception-Reaction Time | 1.5s | 1.5s |
| Startup Lost Time | 2.0s | 2.0s |
| Acceleration Rate | 8.0 ft/s² (~5.5 mph/s) | 2.5 ft/s² (~1.7 mph/s) |
| Comfortable Deceleration | 11.2 ft/s² (0.35g) | 8.0 ft/s² |
| Stopping Distance (35 mph) | ~136 ft | ~250 ft |

### Weather Impact on Driving
| Condition | Reaction Multiplier | Speed Reduction |
|-----------|---------------------|-----------------|
| Clear | 1.0x | 0% |
| Rain | 1.25x | 15% |
| Heavy Rain | 1.5x | 25% |
| Snow | 1.75x | 40% |
| Fog | 1.4x | 30% |
| Ice | 2.0x | 50% |

### Sources
- [FHWA Road Weather Management](https://ops.fhwa.dot.gov/weather/roadimpact.htm)
- [ITE Traffic Engineering Handbook](https://www.ite.org/)
- [SAE Technical Papers on Vehicle Acceleration](https://www.sae.org/publications/technical-papers/content/950136/)
- [FMCSA Vehicle Weight Standards](https://www.fmcsa.dot.gov/)
- [Truck Acceleration Study - ScienceDirect](https://www.sciencedirect.com/science/article/pii/S204604301630034X)
- [Weather Impact on Traffic Safety - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC10794278/)

## Installation & Running

### Requirements
- Python 3.8 or higher
- tkinter (included with standard Python installation)

### Running the Simulator
```bash
cd /home/user/Traffic
python3 traffic_simulator.py
```

## Usage Guide

### Building a City
1. Select "Build Tools" panel
2. Choose build mode: Road, Signal, Tourism, or Delete
3. Select road type (4-Way, N-S Road, E-W Road, T-intersections)
4. Left-click on grid to place
5. Or click "Random City Grid" for auto-generation

### Configuring Signals
1. Right-click on any intersection to edit individual timing
2. Use "Signal Timing" panel sliders to set defaults
3. Click "Apply to All Signals" to update existing signals

### Running Analysis
1. Configure weather, time, and traffic conditions
2. Click "Start" to begin simulation
3. Adjust simulation speed (0.1x to 10x)
4. Watch real-time statistics in Analytics panel
5. Click "Save Snapshot for Comparison" to record results
6. Repeat with different configurations
7. Click "Compare All" to see rankings
8. Export to CSV for detailed analysis

### Finding Optimal Timing
1. Start with default timing (30s green each direction)
2. Run simulation for 2-3 minutes at 5x speed
3. Save snapshot
4. Adjust timing (try longer green for busier direction)
5. Reset and run again
6. Compare results to find lowest average wait time

## Controls Summary

| Action | Mouse/Key |
|--------|-----------|
| Place road/signal | Left-click |
| Edit signal | Right-click |
| Pan view | (future feature) |
| Start/Pause | Start button |
| Speed up | Speed slider |

## File Formats

### Layout JSON
```json
{
  "grid_size": 8,
  "cells": [
    {
      "x": 2, "y": 2,
      "road_type": "INTERSECTION",
      "is_tourism": false,
      "signal": {
        "type": "TRAFFIC_LIGHT",
        "green_ns": 30,
        "green_ew": 30,
        "yellow": 4,
        "all_red": 2
      }
    }
  ]
}
```

### Comparison CSV
Exports: Name, Duration, Total Vehicles, Throughput, Avg Wait, Max Wait, Total Stopped, Avg Speed, Weather, Time, Green NS, Green EW, Density, Trucks

## License

MIT License - Feel free to modify and use for your traffic analysis needs.
