#!/usr/bin/env python3
"""
Traffic Signal Simulator - A comprehensive traffic simulation system
with visual demonstration of traffic interactions and signal timing optimization.

Research-based defaults from transportation engineering studies.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import math
import random
import json
import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
from enum import Enum, auto
from collections import defaultdict
import copy
import threading
import urllib.request
import urllib.parse


# ============================================================================
# RESEARCH-BASED DEFAULTS (Oliver's Averages)
# Sources: FHWA, ITE Traffic Engineering Handbook, SAE studies
# ============================================================================

class TrafficDefaults:
    """
    Research-based traffic timing defaults.

    Sources:
    - FHWA Road Weather Management: https://ops.fhwa.dot.gov/weather/roadimpact.htm
    - ITE Traffic Engineering Handbook
    - SAE Technical Papers on Vehicle Acceleration
    - FMCSA Vehicle Weight Standards
    """

    # Reaction times (seconds) - time from signal change to foot off brake
    PERCEPTION_REACTION_TIME = 1.5  # Average driver perception-reaction time
    REACTION_TIME_DISTRACTED = 2.5  # Distracted driver
    REACTION_TIME_ELDERLY = 2.0     # Elderly driver adjustment
    REACTION_TIME_NIGHT = 1.8       # Nighttime adjustment

    # Startup lost time (seconds) - time for queue to start moving after green
    STARTUP_LOST_TIME = 2.0         # First vehicle in queue
    QUEUE_DISCHARGE_HEADWAY = 2.0   # Seconds between vehicles crossing stop line

    # Acceleration rates (feet per second squared)
    CAR_ACCELERATION = 8.0          # Passenger car: ~5.5 mph/s
    CAR_MAX_SPEED = 35.0            # mph in urban areas

    TRUCK_ACCELERATION = 2.5        # Semi-truck: ~1.7 mph/s (loaded)
    TRUCK_MAX_SPEED = 30.0          # mph in urban areas

    # Deceleration rates (comfortable)
    CAR_DECELERATION = 11.2         # ft/s² (~0.35g comfortable)
    TRUCK_DECELERATION = 8.0        # ft/s² (longer stopping distance)

    # Stopping distances at 35 mph
    CAR_STOPPING_DISTANCE = 136     # feet (perception + braking)
    TRUCK_STOPPING_DISTANCE = 250   # feet (much longer due to weight)

    # Weather impact multipliers on reaction time
    WEATHER_CLEAR = 1.0
    WEATHER_RAIN = 1.25             # 25% slower reactions
    WEATHER_HEAVY_RAIN = 1.5        # 50% slower
    WEATHER_SNOW = 1.75             # 75% slower
    WEATHER_FOG = 1.4               # 40% slower (visibility)
    WEATHER_ICE = 2.0               # Double reaction time

    # Weather impact on max speed (multiplier)
    SPEED_RAIN = 0.85               # 15% speed reduction
    SPEED_HEAVY_RAIN = 0.75         # 25% speed reduction
    SPEED_SNOW = 0.60               # 40% speed reduction
    SPEED_FOG = 0.70                # 30% speed reduction
    SPEED_ICE = 0.50                # 50% speed reduction

    # Time of day impacts
    TIME_DAY = 1.0                  # Baseline
    TIME_NIGHT = 1.2                # 20% slower
    TIME_RUSH_HOUR = 1.1            # 10% slower (stress/aggression)
    TIME_LATE_NIGHT = 1.3           # 30% slower (fatigue)

    # Distraction impact
    DISTRACTION_NONE = 1.0
    DISTRACTION_LIGHT = 1.15        # Radio, talking
    DISTRACTION_MODERATE = 1.35     # Eating, GPS
    DISTRACTION_HEAVY = 1.75        # Phone use

    # Signal timing defaults (seconds)
    YELLOW_LIGHT_DURATION = 4.0     # Standard yellow
    ALL_RED_CLEARANCE = 2.0         # All-red interval
    MIN_GREEN_TIME = 10.0           # Minimum green phase
    MAX_GREEN_TIME = 60.0           # Maximum green phase
    PEDESTRIAN_WALK_TIME = 7.0      # Walk signal
    PEDESTRIAN_CLEARANCE = 15.0     # Flashing don't walk

    # Pedestrian delays
    PEDESTRIAN_CROSSING_SPEED = 3.5  # ft/s average
    TOURIST_PEDESTRIAN_MULTIPLIER = 1.5  # Tourists walk slower, more frequent

    # Vehicle lengths (feet)
    CAR_LENGTH = 15.0
    TRUCK_LENGTH = 70.0             # Semi with trailer

    # Following distances
    MIN_FOLLOWING_DISTANCE = 10.0   # feet (stopped)
    FOLLOWING_TIME_GAP = 2.0        # seconds at speed


# ============================================================================
# ENUMS AND DATA CLASSES
# ============================================================================

class Direction(Enum):
    NORTH = 0
    EAST = 1
    SOUTH = 2
    WEST = 3

class SignalState(Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"
    FLASHING_YELLOW = "flashing_yellow"
    FLASHING_RED = "flashing_red"
    OFF = "off"

class SignalType(Enum):
    NONE = "none"
    TRAFFIC_LIGHT = "traffic_light"
    STOP_SIGN = "stop_sign"
    FOUR_WAY_STOP = "four_way_stop"
    YIELD_SIGN = "yield_sign"
    FLASHING_YELLOW = "flashing_yellow"
    FLASHING_RED = "flashing_red"
    ROUNDABOUT = "roundabout"
    PEDESTRIAN_SIGNAL = "pedestrian_signal"

class RoadType(Enum):
    NONE = 0
    STRAIGHT_NS = 1    # North-South
    STRAIGHT_EW = 2    # East-West
    INTERSECTION = 3   # 4-way intersection
    T_NORTH = 4        # T intersection (no south exit)
    T_SOUTH = 5
    T_EAST = 6
    T_WEST = 7
    CORNER_NE = 8
    CORNER_NW = 9
    CORNER_SE = 10
    CORNER_SW = 11
    ROUNDABOUT = 12    # Circular intersection

class VehicleType(Enum):
    CAR = "car"
    TRUCK = "truck"
    SEMI = "semi"

class WeatherType(Enum):
    CLEAR = "Clear"
    RAIN = "Rain"
    HEAVY_RAIN = "Heavy Rain"
    SNOW = "Snow"
    FOG = "Fog"
    ICE = "Ice"

class TimeOfDay(Enum):
    MORNING_RUSH = "Morning Rush (7-9 AM)"
    MIDDAY = "Midday (10 AM-3 PM)"
    EVENING_RUSH = "Evening Rush (4-7 PM)"
    EVENING = "Evening (7-10 PM)"
    NIGHT = "Night (10 PM-6 AM)"
    LATE_NIGHT = "Late Night (12-5 AM)"


@dataclass
class Vehicle:
    """Represents a vehicle in the simulation."""
    id: int
    vehicle_type: VehicleType
    x: float
    y: float
    direction: Direction
    lane: int = 0  # 0 = right lane (normal), 1 = left lane (opposite direction)
    lane_offset: float = 0.0  # Lateral offset within road for lane positioning
    speed: float = 0.0
    target_speed: float = 35.0
    length: float = 15.0
    width: float = 6.0
    acceleration: float = 8.0
    max_deceleration: float = 11.2
    color: str = "blue"
    waiting_time: float = 0.0
    total_stopped_time: float = 0.0
    distance_traveled: float = 0.0
    is_stopped: bool = False
    stop_start_time: float = 0.0
    # Individual vehicle modifiers
    distraction_level: float = 0.0  # 0-1 scale (individual distraction)
    reaction_modifier: float = 1.0  # Individual reaction time multiplier
    aggression: float = 0.5  # 0=passive, 1=aggressive (affects following distance)
    # Tracking
    spawn_time: float = 0.0
    stops_count: int = 0
    intersections_passed: int = 0

    def __post_init__(self):
        if self.vehicle_type == VehicleType.CAR:
            self.length = TrafficDefaults.CAR_LENGTH
            self.acceleration = TrafficDefaults.CAR_ACCELERATION
            self.max_deceleration = TrafficDefaults.CAR_DECELERATION
            self.target_speed = TrafficDefaults.CAR_MAX_SPEED
            self.color = random.choice(["#3498db", "#2ecc71", "#9b59b6", "#e74c3c", "#f39c12", "#1abc9c"])
            self.width = 6.0
        elif self.vehicle_type in (VehicleType.TRUCK, VehicleType.SEMI):
            self.length = TrafficDefaults.TRUCK_LENGTH if self.vehicle_type == VehicleType.SEMI else 35.0
            self.acceleration = TrafficDefaults.TRUCK_ACCELERATION
            self.max_deceleration = TrafficDefaults.TRUCK_DECELERATION
            self.target_speed = TrafficDefaults.TRUCK_MAX_SPEED
            self.color = "#7f8c8d" if self.vehicle_type == VehicleType.SEMI else "#95a5a6"
            self.width = 8.0  # Trucks are wider

        # Set lane offset based on direction (right-hand traffic)
        # Positive offset = right side of road center
        self._update_lane_offset()

    def _update_lane_offset(self):
        """Calculate lane offset for proper lane positioning."""
        # Lane width as fraction of cell (each lane ~0.2 of cell width)
        lane_width = 0.15
        if self.direction in (Direction.NORTH, Direction.EAST):
            # These directions travel on the right side (positive offset)
            self.lane_offset = lane_width
        else:
            # South and West travel on left side (negative offset from their perspective)
            self.lane_offset = -lane_width


@dataclass
class TrafficSignal:
    """Represents a traffic signal at an intersection."""
    signal_type: SignalType
    states: Dict[Direction, SignalState] = field(default_factory=dict)
    phase_time: float = 0.0
    current_phase: int = 0
    green_time_ns: float = 30.0
    green_time_ew: float = 30.0
    yellow_time: float = 4.0
    all_red_time: float = 2.0
    pedestrian_phase: bool = False
    pedestrian_time_remaining: float = 0.0
    is_tourism_area: bool = False
    pedestrian_frequency: float = 0.1  # Probability of pedestrian per cycle

    def __post_init__(self):
        if not self.states:
            for d in Direction:
                self.states[d] = SignalState.RED


@dataclass
class GridCell:
    """Represents a cell in the city grid."""
    x: int
    y: int
    road_type: RoadType = RoadType.NONE
    signal: Optional[TrafficSignal] = None
    speed_limit: float = 35.0
    is_tourism_area: bool = False


@dataclass
class SimulationStats:
    """Tracks simulation statistics for comparison."""
    name: str
    total_vehicles: int = 0
    total_stopped_time: float = 0.0
    total_travel_time: float = 0.0
    total_distance: float = 0.0
    average_speed: float = 0.0
    average_wait_time: float = 0.0
    max_wait_time: float = 0.0
    throughput: int = 0  # Vehicles that completed their route
    timestamp: float = 0.0
    config_snapshot: Dict = field(default_factory=dict)


# ============================================================================
# MAIN APPLICATION
# ============================================================================

class TrafficSimulator:
    def __init__(self, root):
        self.root = root
        self.root.title("Traffic Signal Simulator - Efficiency Analysis Tool")
        self.root.geometry("1600x900")

        # Simulation state
        self.grid_size = 12  # 12x12 grid (can be changed via UI)
        self.cell_size = 60  # pixels per cell
        self.grid: List[List[GridCell]] = []
        self.vehicles: List[Vehicle] = []
        self.vehicle_id_counter = 0
        self.simulation_running = False
        self.simulation_speed = 1.0
        self.sim_time = 0.0
        self.last_update_time = 0.0

        # Statistics
        self.current_stats = SimulationStats(name="Current")
        self.saved_simulations: List[SimulationStats] = []

        # Vehicle selection
        self.selected_vehicle: Optional[Vehicle] = None
        self.vehicle_info_window = None

        # Condition modifiers
        self.weather = WeatherType.CLEAR
        self.time_of_day = TimeOfDay.MIDDAY
        self.distraction_level = 0.0  # 0-1 scale
        self.heavy_vehicle_ratio = 0.1  # 10% trucks by default
        self.traffic_density = 0.5  # 0-1 scale

        # Pedestrian settings
        self.pedestrian_enabled = True
        self.tourism_pedestrian_multiplier = 1.5

        # Build mode
        self.build_mode = "road"  # road, signal, delete, tourism
        self.selected_signal_type = SignalType.TRAFFIC_LIGHT
        self.selected_road_type = RoadType.INTERSECTION

        # UI collapsed state
        self.panel_states = {
            "conditions": True,
            "vehicles": True,
            "signals": True,
            "build": True,
            "analytics": True
        }

        self._setup_ui()
        self._init_grid()

        # Start update loop
        self._update_loop()

    def _setup_ui(self):
        """Setup the main UI layout."""
        # Main container
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Left panel - Controls
        self.control_panel = ttk.Frame(self.main_frame, width=350)
        self.control_panel.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        self.control_panel.pack_propagate(False)

        # Create scrollable control panel
        self.control_canvas = tk.Canvas(self.control_panel)
        self.control_scrollbar = ttk.Scrollbar(self.control_panel, orient="vertical",
                                                command=self.control_canvas.yview)
        self.scrollable_frame = ttk.Frame(self.control_canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.control_canvas.configure(scrollregion=self.control_canvas.bbox("all"))
        )

        self.control_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.control_canvas.configure(yscrollcommand=self.control_scrollbar.set)

        self.control_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.control_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Bind mouse wheel
        self.control_canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        self._setup_control_panels()

        # Center - Canvas for simulation
        self.canvas_frame = ttk.Frame(self.main_frame)
        self.canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.canvas = tk.Canvas(self.canvas_frame, bg="#2c3e50")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Bind canvas events
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<Button-3>", self._on_canvas_right_click)
        self.canvas.bind("<Configure>", self._on_canvas_resize)

        # Right panel - Analytics
        self.analytics_panel = ttk.Frame(self.main_frame, width=300)
        self.analytics_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
        self.analytics_panel.pack_propagate(False)

        self._setup_analytics_panel()

        # Bottom - Status bar
        self.status_bar = ttk.Frame(self.root)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.status_label = ttk.Label(self.status_bar, text="Ready")
        self.status_label.pack(side=tk.LEFT, padx=5)

        self.time_label = ttk.Label(self.status_bar, text="Time: 0:00")
        self.time_label.pack(side=tk.RIGHT, padx=5)

    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling."""
        self.control_canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def _create_collapsible_panel(self, parent, title, key):
        """Create a collapsible panel section."""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=2)

        # Header with toggle button
        header = ttk.Frame(frame)
        header.pack(fill=tk.X)

        toggle_text = "[-]" if self.panel_states.get(key, True) else "[+]"
        toggle_btn = ttk.Button(header, text=toggle_text, width=3,
                                command=lambda: self._toggle_panel(key, content, toggle_btn))
        toggle_btn.pack(side=tk.LEFT)

        ttk.Label(header, text=title, font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)

        # Content frame
        content = ttk.Frame(frame)
        if self.panel_states.get(key, True):
            content.pack(fill=tk.X, padx=10, pady=5)

        return content

    def _toggle_panel(self, key, content, button):
        """Toggle a collapsible panel."""
        self.panel_states[key] = not self.panel_states.get(key, True)
        if self.panel_states[key]:
            content.pack(fill=tk.X, padx=10, pady=5)
            button.config(text="[-]")
        else:
            content.pack_forget()
            button.config(text="[+]")

    def _setup_control_panels(self):
        """Setup all control panel sections."""
        # Simulation Controls
        sim_frame = ttk.LabelFrame(self.scrollable_frame, text="Simulation")
        sim_frame.pack(fill=tk.X, padx=5, pady=5)

        btn_frame = ttk.Frame(sim_frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)

        self.start_btn = ttk.Button(btn_frame, text="Start", command=self._toggle_simulation)
        self.start_btn.pack(side=tk.LEFT, padx=2)

        ttk.Button(btn_frame, text="Reset", command=self._reset_simulation).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Clear", command=self._clear_vehicles).pack(side=tk.LEFT, padx=2)

        # Speed control
        speed_frame = ttk.Frame(sim_frame)
        speed_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(speed_frame, text="Speed:").pack(side=tk.LEFT)
        self.speed_var = tk.DoubleVar(value=1.0)
        speed_scale = ttk.Scale(speed_frame, from_=0.1, to=10.0, variable=self.speed_var,
                                orient=tk.HORIZONTAL, command=self._update_speed)
        speed_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.speed_label = ttk.Label(speed_frame, text="1.0x")
        self.speed_label.pack(side=tk.LEFT)

        # Weather & Conditions Panel
        conditions_content = self._create_collapsible_panel(
            self.scrollable_frame, "Weather & Conditions", "conditions")

        # Weather dropdown
        weather_frame = ttk.Frame(conditions_content)
        weather_frame.pack(fill=tk.X, pady=2)
        ttk.Label(weather_frame, text="Weather:").pack(side=tk.LEFT)
        self.weather_var = tk.StringVar(value=WeatherType.CLEAR.value)
        weather_combo = ttk.Combobox(weather_frame, textvariable=self.weather_var,
                                      values=[w.value for w in WeatherType], state="readonly")
        weather_combo.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=5)
        weather_combo.bind("<<ComboboxSelected>>", self._update_weather)

        # Time of day
        time_frame = ttk.Frame(conditions_content)
        time_frame.pack(fill=tk.X, pady=2)
        ttk.Label(time_frame, text="Time:").pack(side=tk.LEFT)
        self.time_var = tk.StringVar(value=TimeOfDay.MIDDAY.value)
        time_combo = ttk.Combobox(time_frame, textvariable=self.time_var,
                                   values=[t.value for t in TimeOfDay], state="readonly")
        time_combo.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=5)
        time_combo.bind("<<ComboboxSelected>>", self._update_time_of_day)

        # Distraction slider
        distract_frame = ttk.Frame(conditions_content)
        distract_frame.pack(fill=tk.X, pady=2)
        ttk.Label(distract_frame, text="Distraction:").pack(side=tk.LEFT)
        self.distraction_var = tk.DoubleVar(value=0.0)
        distract_scale = ttk.Scale(distract_frame, from_=0, to=1, variable=self.distraction_var,
                                    orient=tk.HORIZONTAL)
        distract_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.distraction_label = ttk.Label(distract_frame, text="None")
        self.distraction_label.pack(side=tk.RIGHT)
        self.distraction_var.trace("w", self._update_distraction_label)

        # Impact display
        self.impact_label = ttk.Label(conditions_content,
                                       text="Reaction modifier: 1.0x\nSpeed modifier: 1.0x",
                                       font=("Arial", 8))
        self.impact_label.pack(fill=tk.X, pady=5)

        # Vehicle Settings Panel
        vehicle_content = self._create_collapsible_panel(
            self.scrollable_frame, "Vehicle Settings", "vehicles")

        # Traffic density
        density_frame = ttk.Frame(vehicle_content)
        density_frame.pack(fill=tk.X, pady=2)
        ttk.Label(density_frame, text="Traffic Density:").pack(side=tk.LEFT)
        self.density_var = tk.DoubleVar(value=0.5)
        density_scale = ttk.Scale(density_frame, from_=0.1, to=1.0, variable=self.density_var,
                                   orient=tk.HORIZONTAL)
        density_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.density_label = ttk.Label(density_frame, text="50%")
        self.density_label.pack(side=tk.RIGHT)
        self.density_var.trace("w", self._update_density_label)

        # Heavy vehicle ratio
        truck_frame = ttk.Frame(vehicle_content)
        truck_frame.pack(fill=tk.X, pady=2)
        ttk.Label(truck_frame, text="Heavy Vehicles:").pack(side=tk.LEFT)
        self.truck_var = tk.DoubleVar(value=0.1)
        truck_scale = ttk.Scale(truck_frame, from_=0, to=0.5, variable=self.truck_var,
                                 orient=tk.HORIZONTAL)
        truck_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.truck_label = ttk.Label(truck_frame, text="10%")
        self.truck_label.pack(side=tk.RIGHT)
        self.truck_var.trace("w", self._update_truck_label)

        # Pedestrian settings
        ped_frame = ttk.Frame(vehicle_content)
        ped_frame.pack(fill=tk.X, pady=2)
        self.ped_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(ped_frame, text="Enable Pedestrians",
                        variable=self.ped_var).pack(side=tk.LEFT)

        tourism_frame = ttk.Frame(vehicle_content)
        tourism_frame.pack(fill=tk.X, pady=2)
        ttk.Label(tourism_frame, text="Tourism Ped. Rate:").pack(side=tk.LEFT)
        self.tourism_var = tk.DoubleVar(value=1.5)
        tourism_scale = ttk.Scale(tourism_frame, from_=1.0, to=3.0, variable=self.tourism_var,
                                   orient=tk.HORIZONTAL)
        tourism_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.tourism_label = ttk.Label(tourism_frame, text="1.5x")
        self.tourism_label.pack(side=tk.RIGHT)
        self.tourism_var.trace("w", self._update_tourism_label)

        # Signal Settings Panel
        signal_content = self._create_collapsible_panel(
            self.scrollable_frame, "Signal Timing", "signals")

        # Green time NS
        green_ns_frame = ttk.Frame(signal_content)
        green_ns_frame.pack(fill=tk.X, pady=2)
        ttk.Label(green_ns_frame, text="Green N/S (s):").pack(side=tk.LEFT)
        self.green_ns_var = tk.DoubleVar(value=30.0)
        green_ns_scale = ttk.Scale(green_ns_frame, from_=10, to=120, variable=self.green_ns_var,
                                    orient=tk.HORIZONTAL)
        green_ns_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.green_ns_label = ttk.Label(green_ns_frame, text="30s")
        self.green_ns_label.pack(side=tk.RIGHT)
        self.green_ns_var.trace("w", self._update_green_ns_label)

        # Green time EW
        green_ew_frame = ttk.Frame(signal_content)
        green_ew_frame.pack(fill=tk.X, pady=2)
        ttk.Label(green_ew_frame, text="Green E/W (s):").pack(side=tk.LEFT)
        self.green_ew_var = tk.DoubleVar(value=30.0)
        green_ew_scale = ttk.Scale(green_ew_frame, from_=10, to=120, variable=self.green_ew_var,
                                    orient=tk.HORIZONTAL)
        green_ew_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.green_ew_label = ttk.Label(green_ew_frame, text="30s")
        self.green_ew_label.pack(side=tk.RIGHT)
        self.green_ew_var.trace("w", self._update_green_ew_label)

        # Yellow time
        yellow_frame = ttk.Frame(signal_content)
        yellow_frame.pack(fill=tk.X, pady=2)
        ttk.Label(yellow_frame, text="Yellow (s):").pack(side=tk.LEFT)
        self.yellow_var = tk.DoubleVar(value=4.0)
        yellow_scale = ttk.Scale(yellow_frame, from_=2, to=8, variable=self.yellow_var,
                                  orient=tk.HORIZONTAL)
        yellow_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.yellow_label = ttk.Label(yellow_frame, text="4s")
        self.yellow_label.pack(side=tk.RIGHT)
        self.yellow_var.trace("w", self._update_yellow_label)

        # All red time
        red_frame = ttk.Frame(signal_content)
        red_frame.pack(fill=tk.X, pady=2)
        ttk.Label(red_frame, text="All-Red (s):").pack(side=tk.LEFT)
        self.all_red_var = tk.DoubleVar(value=2.0)
        red_scale = ttk.Scale(red_frame, from_=1, to=5, variable=self.all_red_var,
                               orient=tk.HORIZONTAL)
        red_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.red_label = ttk.Label(red_frame, text="2s")
        self.red_label.pack(side=tk.RIGHT)
        self.all_red_var.trace("w", self._update_red_label)

        # Apply to all signals button
        ttk.Button(signal_content, text="Apply to All Signals",
                   command=self._apply_signal_timing).pack(fill=tk.X, pady=5)

        # Build Mode Panel
        build_content = self._create_collapsible_panel(
            self.scrollable_frame, "Build Tools", "build")

        # Build mode buttons
        mode_frame = ttk.Frame(build_content)
        mode_frame.pack(fill=tk.X, pady=2)

        self.build_mode_var = tk.StringVar(value="road")
        modes = [("Road", "road"), ("Signal", "signal"), ("Tourism", "tourism"), ("Delete", "delete")]
        for text, mode in modes:
            ttk.Radiobutton(mode_frame, text=text, variable=self.build_mode_var,
                           value=mode, command=self._update_build_mode).pack(side=tk.LEFT, padx=2)

        # Road type selector
        road_frame = ttk.LabelFrame(build_content, text="Road Type")
        road_frame.pack(fill=tk.X, pady=5)

        self.road_type_var = tk.StringVar(value="INTERSECTION")
        road_types = [
            ("4-Way", "INTERSECTION"),
            ("N-S Road", "STRAIGHT_NS"),
            ("E-W Road", "STRAIGHT_EW"),
            ("T-North", "T_NORTH"),
            ("T-South", "T_SOUTH"),
            ("T-East", "T_EAST"),
            ("T-West", "T_WEST"),
        ]

        for i, (text, rtype) in enumerate(road_types):
            ttk.Radiobutton(road_frame, text=text, variable=self.road_type_var,
                           value=rtype).grid(row=i//2, column=i%2, sticky="w", padx=5)

        # Signal type selector
        signal_frame = ttk.LabelFrame(build_content, text="Signal Type")
        signal_frame.pack(fill=tk.X, pady=5)

        self.signal_type_var = tk.StringVar(value="TRAFFIC_LIGHT")
        signal_types = [
            ("Traffic Light", "TRAFFIC_LIGHT"),
            ("Stop Sign", "STOP_SIGN"),
            ("4-Way Stop", "FOUR_WAY_STOP"),
            ("Yield", "YIELD_SIGN"),
            ("Flash Yellow", "FLASHING_YELLOW"),
            ("Flash Red", "FLASHING_RED"),
            ("Roundabout", "ROUNDABOUT"),
            ("Ped Signal", "PEDESTRIAN_SIGNAL"),
        ]

        for i, (text, stype) in enumerate(signal_types):
            ttk.Radiobutton(signal_frame, text=text, variable=self.signal_type_var,
                           value=stype).grid(row=i//2, column=i%2, sticky="w", padx=5)

        # Grid Size selector
        grid_frame = ttk.LabelFrame(build_content, text="Grid Size")
        grid_frame.pack(fill=tk.X, pady=5)

        size_frame = ttk.Frame(grid_frame)
        size_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(size_frame, text="Size:").pack(side=tk.LEFT)
        self.grid_size_var = tk.IntVar(value=self.grid_size)
        grid_sizes = [8, 10, 12, 16, 20, 24, 32]
        self.grid_size_combo = ttk.Combobox(size_frame, textvariable=self.grid_size_var,
                                            values=grid_sizes, width=5, state="readonly")
        self.grid_size_combo.pack(side=tk.LEFT, padx=5)
        self.grid_size_label = ttk.Label(size_frame, text=f"({self.grid_size}x{self.grid_size})")
        self.grid_size_label.pack(side=tk.LEFT)

        ttk.Button(grid_frame, text="Apply Grid Size",
                   command=self._apply_grid_size).pack(fill=tk.X, padx=5, pady=2)

        ttk.Label(grid_frame, text="Note: Larger grids need more CPU",
                  font=("Arial", 8)).pack(padx=5)

        # Generation buttons
        gen_frame = ttk.LabelFrame(build_content, text="Generation")
        gen_frame.pack(fill=tk.X, pady=5)

        ttk.Button(gen_frame, text="Random City Grid",
                   command=self._generate_random_city).pack(fill=tk.X, padx=5, pady=2)
        ttk.Button(gen_frame, text="Clear Grid",
                   command=self._clear_grid).pack(fill=tk.X, padx=5, pady=2)

        # Import/Export
        io_frame = ttk.Frame(gen_frame)
        io_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Button(io_frame, text="Save Layout",
                   command=self._save_layout).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        ttk.Button(io_frame, text="Load Layout",
                   command=self._load_layout).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        ttk.Button(gen_frame, text="Import from OpenStreetMap",
                   command=self._import_osm).pack(fill=tk.X, padx=5, pady=2)

    def _setup_analytics_panel(self):
        """Setup the analytics and comparison panel."""
        ttk.Label(self.analytics_panel, text="Analytics & Comparison",
                  font=("Arial", 12, "bold")).pack(pady=5)

        # Current stats
        stats_frame = ttk.LabelFrame(self.analytics_panel, text="Current Simulation")
        stats_frame.pack(fill=tk.X, padx=5, pady=5)

        self.stats_labels = {}
        stats = [
            ("vehicles", "Active Vehicles: 0"),
            ("throughput", "Completed: 0"),
            ("avg_wait", "Avg Wait: 0.0s"),
            ("max_wait", "Max Wait: 0.0s"),
            ("total_stopped", "Total Stopped: 0.0s"),
            ("avg_speed", "Avg Speed: 0.0 mph"),
            ("efficiency", "Efficiency: 0%"),
        ]

        for key, text in stats:
            label = ttk.Label(stats_frame, text=text)
            label.pack(anchor="w", padx=5, pady=1)
            self.stats_labels[key] = label

        # Save current simulation
        ttk.Button(stats_frame, text="Save Snapshot for Comparison",
                   command=self._save_simulation_snapshot).pack(fill=tk.X, padx=5, pady=5)

        # Comparison section
        compare_frame = ttk.LabelFrame(self.analytics_panel, text="Comparison")
        compare_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Saved simulations list
        self.comparison_listbox = tk.Listbox(compare_frame, height=6)
        self.comparison_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.comparison_listbox.bind("<<ListboxSelect>>", self._show_comparison_details)

        # Comparison details
        self.comparison_text = tk.Text(compare_frame, height=10, width=30, font=("Courier", 9))
        self.comparison_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        btn_frame = ttk.Frame(compare_frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(btn_frame, text="Compare All",
                   command=self._compare_all_simulations).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Delete Selected",
                   command=self._delete_selected_comparison).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Export CSV",
                   command=self._export_comparison_csv).pack(side=tk.LEFT, padx=2)

    def _init_grid(self):
        """Initialize the city grid."""
        self.grid = []
        for y in range(self.grid_size):
            row = []
            for x in range(self.grid_size):
                row.append(GridCell(x=x, y=y))
            self.grid.append(row)

    def _draw_grid(self):
        """Draw the city grid on the canvas."""
        self.canvas.delete("all")

        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        # Calculate cell size based on canvas size
        self.cell_size = min(canvas_width, canvas_height) // (self.grid_size + 2)

        # Calculate offset to center grid
        offset_x = (canvas_width - self.cell_size * self.grid_size) // 2
        offset_y = (canvas_height - self.cell_size * self.grid_size) // 2

        # Draw background (buildings/blocks)
        for y in range(self.grid_size):
            for x in range(self.grid_size):
                cell = self.grid[y][x]
                x1 = offset_x + x * self.cell_size
                y1 = offset_y + y * self.cell_size
                x2 = x1 + self.cell_size
                y2 = y1 + self.cell_size

                if cell.road_type == RoadType.NONE:
                    # Building block
                    color = "#95a5a6" if not cell.is_tourism_area else "#e8daef"
                    self.canvas.create_rectangle(x1+2, y1+2, x2-2, y2-2,
                                                  fill=color, outline="#7f8c8d")
                else:
                    # Road
                    self._draw_road_cell(cell, x1, y1, x2, y2)

        # Draw vehicles
        for vehicle in self.vehicles:
            self._draw_vehicle(vehicle, offset_x, offset_y)

        # Store offset for click handling
        self.grid_offset = (offset_x, offset_y)

    def _draw_road_cell(self, cell: GridCell, x1, y1, x2, y2):
        """Draw a road cell with two lanes and appropriate markings."""
        # Road surface
        base_color = "#34495e"
        if cell.is_tourism_area:
            base_color = "#5d6d7e"

        self.canvas.create_rectangle(x1, y1, x2, y2, fill=base_color, outline="")

        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        road_width = self.cell_size

        road_type = cell.road_type

        # Draw road markings based on type - with two lanes
        if road_type == RoadType.STRAIGHT_NS:
            # Yellow center dividing line (double line for no passing)
            self.canvas.create_line(cx-1, y1, cx-1, y2, fill="#f1c40f", width=2)
            self.canvas.create_line(cx+1, y1, cx+1, y2, fill="#f1c40f", width=2)
            # White edge lines (road boundaries)
            edge_offset = road_width * 0.35
            self.canvas.create_line(x1+3, y1, x1+3, y2, fill="white", width=1)
            self.canvas.create_line(x2-3, y1, x2-3, y2, fill="white", width=1)
            # Lane markers (dashed white lines in each lane)
            lane_pos = road_width * 0.17
            self.canvas.create_line(cx-lane_pos, y1, cx-lane_pos, y2, fill="white", width=1, dash=(8,8))
            self.canvas.create_line(cx+lane_pos, y1, cx+lane_pos, y2, fill="white", width=1, dash=(8,8))

        elif road_type == RoadType.STRAIGHT_EW:
            # Yellow center dividing line
            self.canvas.create_line(x1, cy-1, x2, cy-1, fill="#f1c40f", width=2)
            self.canvas.create_line(x1, cy+1, x2, cy+1, fill="#f1c40f", width=2)
            # White edge lines
            self.canvas.create_line(x1, y1+3, x2, y1+3, fill="white", width=1)
            self.canvas.create_line(x1, y2-3, x2, y2-3, fill="white", width=1)
            # Lane markers
            lane_pos = road_width * 0.17
            self.canvas.create_line(x1, cy-lane_pos, x2, cy-lane_pos, fill="white", width=1, dash=(8,8))
            self.canvas.create_line(x1, cy+lane_pos, x2, cy+lane_pos, fill="white", width=1, dash=(8,8))

        elif road_type == RoadType.INTERSECTION:
            # Stop lines for each approach
            stop_line_offset = road_width * 0.4
            line_width = 3

            # North approach stop line
            self.canvas.create_line(x1+5, y1+stop_line_offset, cx-2, y1+stop_line_offset,
                                   fill="white", width=line_width)
            # South approach stop line
            self.canvas.create_line(cx+2, y2-stop_line_offset, x2-5, y2-stop_line_offset,
                                   fill="white", width=line_width)
            # East approach stop line
            self.canvas.create_line(x2-stop_line_offset, y1+5, x2-stop_line_offset, cy-2,
                                   fill="white", width=line_width)
            # West approach stop line
            self.canvas.create_line(x1+stop_line_offset, cy+2, x1+stop_line_offset, y2-5,
                                   fill="white", width=line_width)

            # Crosswalk markings (zebra stripes)
            stripe_width = 2
            stripe_gap = 3
            crosswalk_width = road_width * 0.15

            for i in range(-4, 5):
                offset = i * (stripe_width + stripe_gap)
                # North crosswalk
                self.canvas.create_rectangle(cx + offset, y1+2,
                                            cx + offset + stripe_width, y1+2+crosswalk_width,
                                            fill="white", outline="")
                # South crosswalk
                self.canvas.create_rectangle(cx + offset, y2-2-crosswalk_width,
                                            cx + offset + stripe_width, y2-2,
                                            fill="white", outline="")
                # East crosswalk
                self.canvas.create_rectangle(x2-2-crosswalk_width, cy + offset,
                                            x2-2, cy + offset + stripe_width,
                                            fill="white", outline="")
                # West crosswalk
                self.canvas.create_rectangle(x1+2, cy + offset,
                                            x1+2+crosswalk_width, cy + offset + stripe_width,
                                            fill="white", outline="")

        elif road_type == RoadType.ROUNDABOUT:
            # Draw roundabout with proper lanes
            r = self.cell_size * 0.4
            # Outer edge
            self.canvas.create_oval(cx-r, cy-r, cx+r, cy+r, fill="#34495e", outline="white", width=2)
            # Center island
            r2 = r * 0.4
            self.canvas.create_oval(cx-r2, cy-r2, cx+r2, cy+r2, fill="#27ae60", outline="#229954", width=2)
            # Lane divider circle
            r3 = r * 0.7
            self.canvas.create_oval(cx-r3, cy-r3, cx+r3, cy+r3, fill="", outline="#f1c40f", width=2, dash=(5,5))

        # Draw signal if present
        if cell.signal:
            self._draw_signal(cell.signal, cx, cy, cell.road_type)

    def _draw_signal(self, signal: TrafficSignal, cx, cy, road_type):
        """Draw traffic signal at intersection."""
        if signal.signal_type == SignalType.TRAFFIC_LIGHT:
            # Draw signal heads for each direction
            positions = [
                (cx, cy - self.cell_size*0.35, Direction.SOUTH),  # For southbound
                (cx, cy + self.cell_size*0.35, Direction.NORTH),  # For northbound
                (cx - self.cell_size*0.35, cy, Direction.EAST),   # For eastbound
                (cx + self.cell_size*0.35, cy, Direction.WEST),   # For westbound
            ]

            for px, py, direction in positions:
                state = signal.states.get(direction, SignalState.RED)
                if state == SignalState.GREEN:
                    color = "#2ecc71"
                elif state == SignalState.YELLOW:
                    color = "#f1c40f"
                else:
                    color = "#e74c3c"

                self.canvas.create_oval(px-5, py-5, px+5, py+5, fill=color, outline="black")

        elif signal.signal_type == SignalType.STOP_SIGN:
            # Draw octagonal stop sign
            self._draw_stop_sign(cx, cy - self.cell_size*0.3)

        elif signal.signal_type == SignalType.FOUR_WAY_STOP:
            # Draw stop signs at all corners
            offsets = [(-0.3, -0.3), (0.3, -0.3), (-0.3, 0.3), (0.3, 0.3)]
            for ox, oy in offsets:
                self._draw_stop_sign(cx + self.cell_size*ox, cy + self.cell_size*oy, small=True)

        elif signal.signal_type == SignalType.YIELD_SIGN:
            # Draw yield triangle
            self._draw_yield_sign(cx, cy - self.cell_size*0.3)

        elif signal.signal_type == SignalType.FLASHING_YELLOW:
            # Flashing yellow light
            flash = (int(self.sim_time * 2) % 2 == 0)
            color = "#f1c40f" if flash else "#7d6608"
            self.canvas.create_oval(cx-8, cy-8, cx+8, cy+8, fill=color, outline="black", width=2)

        elif signal.signal_type == SignalType.FLASHING_RED:
            flash = (int(self.sim_time * 2) % 2 == 0)
            color = "#e74c3c" if flash else "#7b241c"
            self.canvas.create_oval(cx-8, cy-8, cx+8, cy+8, fill=color, outline="black", width=2)

        elif signal.signal_type == SignalType.ROUNDABOUT:
            pass  # Roundabout is drawn in road cell

        elif signal.signal_type == SignalType.PEDESTRIAN_SIGNAL:
            # Draw pedestrian signal
            state = "WALK" if signal.pedestrian_phase else "WAIT"
            color = "#2ecc71" if signal.pedestrian_phase else "#e74c3c"
            self.canvas.create_rectangle(cx-10, cy-15, cx+10, cy+15, fill="#2c3e50", outline="white")
            self.canvas.create_text(cx, cy, text=state[0], fill=color, font=("Arial", 10, "bold"))

    def _draw_stop_sign(self, x, y, small=False):
        """Draw an octagonal stop sign."""
        size = 6 if small else 10
        points = []
        for i in range(8):
            angle = math.pi/8 + i * math.pi/4
            px = x + size * math.cos(angle)
            py = y + size * math.sin(angle)
            points.extend([px, py])
        self.canvas.create_polygon(points, fill="#e74c3c", outline="white", width=1)
        if not small:
            self.canvas.create_text(x, y, text="STOP", fill="white", font=("Arial", 5, "bold"))

    def _draw_yield_sign(self, x, y):
        """Draw a yield sign (inverted triangle)."""
        size = 10
        points = [x, y + size, x - size, y - size/2, x + size, y - size/2]
        self.canvas.create_polygon(points, fill="white", outline="#e74c3c", width=2)

    def _draw_vehicle(self, vehicle: Vehicle, offset_x, offset_y):
        """Draw a vehicle on the canvas with proper lane positioning."""
        # Convert grid position to canvas position
        px = offset_x + vehicle.x * self.cell_size
        py = offset_y + vehicle.y * self.cell_size

        # Apply lane offset based on direction
        lane_offset_px = vehicle.lane_offset * self.cell_size
        if vehicle.direction in (Direction.NORTH, Direction.SOUTH):
            # N/S roads: offset horizontally
            px += lane_offset_px
        else:
            # E/W roads: offset vertically
            py += lane_offset_px

        # Vehicle size (scaled to cell size) - make vehicles smaller to fit in lanes
        length = min(vehicle.length / 15, 1.5) * self.cell_size * 0.2
        width = min(vehicle.width / 6, 1.0) * self.cell_size * 0.1

        # Ensure minimum visibility
        length = max(length, 10)
        width = max(width, 6)

        # Calculate rectangle based on direction
        if vehicle.direction == Direction.NORTH:
            x1, y1 = px - width/2, py - length/2
            x2, y2 = px + width/2, py + length/2
        elif vehicle.direction == Direction.SOUTH:
            x1, y1 = px - width/2, py - length/2
            x2, y2 = px + width/2, py + length/2
        elif vehicle.direction == Direction.EAST:
            x1, y1 = px - length/2, py - width/2
            x2, y2 = px + length/2, py + width/2
        else:  # WEST
            x1, y1 = px - length/2, py - width/2
            x2, y2 = px + length/2, py + width/2

        # Store vehicle bounds for click detection
        vehicle._canvas_bounds = (x1, y1, x2, y2)

        # Check if this vehicle is selected
        is_selected = (self.selected_vehicle is not None and
                      self.selected_vehicle.id == vehicle.id)

        # Draw selection highlight if selected
        if is_selected:
            highlight_pad = 3
            self.canvas.create_rectangle(x1-highlight_pad, y1-highlight_pad,
                                        x2+highlight_pad, y2+highlight_pad,
                                        fill="", outline="#00ff00", width=2)

        # Draw vehicle body
        outline_color = "#00ff00" if is_selected else "black"
        outline_width = 2 if is_selected else 1
        self.canvas.create_rectangle(x1, y1, x2, y2, fill=vehicle.color,
                                     outline=outline_color, width=outline_width)

        # Draw vehicle ID number on top
        id_text = str(vehicle.id)
        font_size = max(6, int(min(width, length) * 0.6))
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        self.canvas.create_text(cx, cy, text=id_text, fill="white",
                               font=("Arial", font_size, "bold"))

        # Draw headlights/taillights
        hl_size = max(2, width * 0.25)
        if vehicle.direction == Direction.NORTH:
            self.canvas.create_oval(x1+1, y1, x1+1+hl_size, y1+hl_size, fill="#ffff00", outline="")
            self.canvas.create_oval(x2-1-hl_size, y1, x2-1, y1+hl_size, fill="#ffff00", outline="")
        elif vehicle.direction == Direction.SOUTH:
            self.canvas.create_oval(x1+1, y2-hl_size, x1+1+hl_size, y2, fill="#ff0000", outline="")
            self.canvas.create_oval(x2-1-hl_size, y2-hl_size, x2-1, y2, fill="#ff0000", outline="")
        elif vehicle.direction == Direction.EAST:
            self.canvas.create_oval(x2-hl_size, y1+1, x2, y1+1+hl_size, fill="#ffff00", outline="")
            self.canvas.create_oval(x2-hl_size, y2-1-hl_size, x2, y2-1, fill="#ffff00", outline="")
        else:  # WEST
            self.canvas.create_oval(x1, y1+1, x1+hl_size, y1+1+hl_size, fill="#ff0000", outline="")
            self.canvas.create_oval(x1, y2-1-hl_size, x1+hl_size, y2-1, fill="#ff0000", outline="")

    def _on_canvas_click(self, event):
        """Handle left click on canvas - select vehicle or place road/signal."""
        if not hasattr(self, 'grid_offset'):
            return

        # First, check if a vehicle was clicked
        clicked_vehicle = self._get_vehicle_at_position(event.x, event.y)
        if clicked_vehicle:
            self.selected_vehicle = clicked_vehicle
            self._show_vehicle_info_window(clicked_vehicle)
            self._draw_grid()  # Redraw to show selection
            return

        # If no vehicle clicked, deselect
        if self.selected_vehicle:
            self.selected_vehicle = None
            self._draw_grid()

        offset_x, offset_y = self.grid_offset

        # Calculate grid cell
        gx = int((event.x - offset_x) / self.cell_size)
        gy = int((event.y - offset_y) / self.cell_size)

        if 0 <= gx < self.grid_size and 0 <= gy < self.grid_size:
            cell = self.grid[gy][gx]
            mode = self.build_mode_var.get()

            if mode == "road":
                road_type = RoadType[self.road_type_var.get()]
                cell.road_type = road_type
                # Auto-add signal for intersections
                if road_type == RoadType.INTERSECTION:
                    cell.signal = TrafficSignal(signal_type=SignalType.TRAFFIC_LIGHT)
                elif road_type == RoadType.ROUNDABOUT:
                    cell.signal = TrafficSignal(signal_type=SignalType.ROUNDABOUT)
                else:
                    cell.signal = None

            elif mode == "signal":
                if cell.road_type != RoadType.NONE:
                    signal_type = SignalType[self.signal_type_var.get()]
                    cell.signal = TrafficSignal(
                        signal_type=signal_type,
                        green_time_ns=self.green_ns_var.get(),
                        green_time_ew=self.green_ew_var.get(),
                        yellow_time=self.yellow_var.get(),
                        all_red_time=self.all_red_var.get()
                    )

            elif mode == "tourism":
                cell.is_tourism_area = not cell.is_tourism_area
                if cell.signal:
                    cell.signal.is_tourism_area = cell.is_tourism_area

            elif mode == "delete":
                cell.road_type = RoadType.NONE
                cell.signal = None
                cell.is_tourism_area = False

            self._draw_grid()

    def _on_canvas_right_click(self, event):
        """Handle right click - show cell info/edit signal timing."""
        if not hasattr(self, 'grid_offset'):
            return

        # Check for vehicle right-click first
        clicked_vehicle = self._get_vehicle_at_position(event.x, event.y)
        if clicked_vehicle:
            self._show_vehicle_properties_window(clicked_vehicle)
            return

        offset_x, offset_y = self.grid_offset
        gx = int((event.x - offset_x) / self.cell_size)
        gy = int((event.y - offset_y) / self.cell_size)

        if 0 <= gx < self.grid_size and 0 <= gy < self.grid_size:
            cell = self.grid[gy][gx]
            if cell.signal:
                self._show_signal_editor(cell)

    def _get_vehicle_at_position(self, canvas_x, canvas_y) -> Optional[Vehicle]:
        """Find a vehicle at the given canvas position."""
        for vehicle in self.vehicles:
            if hasattr(vehicle, '_canvas_bounds'):
                x1, y1, x2, y2 = vehicle._canvas_bounds
                if x1 <= canvas_x <= x2 and y1 <= canvas_y <= y2:
                    return vehicle
        return None

    def _show_vehicle_info_window(self, vehicle: Vehicle):
        """Show a live-updating info window for the selected vehicle."""
        # Close existing window if open
        if self.vehicle_info_window and self.vehicle_info_window.winfo_exists():
            self.vehicle_info_window.destroy()

        self.vehicle_info_window = tk.Toplevel(self.root)
        self.vehicle_info_window.title(f"Vehicle #{vehicle.id} Info")
        self.vehicle_info_window.geometry("280x400")
        self.vehicle_info_window.transient(self.root)

        # Header
        header = ttk.Frame(self.vehicle_info_window)
        header.pack(fill=tk.X, padx=10, pady=5)

        type_text = vehicle.vehicle_type.value.upper()
        ttk.Label(header, text=f"Vehicle #{vehicle.id} - {type_text}",
                  font=("Arial", 12, "bold")).pack()

        # Color indicator
        color_frame = tk.Frame(header, bg=vehicle.color, width=30, height=30)
        color_frame.pack(pady=5)

        # Stats frame (will be updated)
        stats_frame = ttk.LabelFrame(self.vehicle_info_window, text="Live Stats")
        stats_frame.pack(fill=tk.X, padx=10, pady=5)

        self._vehicle_info_labels = {}
        stats = [
            ("speed", "Speed: 0.0 mph"),
            ("position", "Position: (0.0, 0.0)"),
            ("direction", "Direction: North"),
            ("waiting", "Waiting Time: 0.0s"),
            ("stopped", "Total Stopped: 0.0s"),
            ("distance", "Distance: 0.0 mi"),
            ("stops", "Stops: 0"),
            ("status", "Status: Moving"),
        ]

        for key, text in stats:
            label = ttk.Label(stats_frame, text=text)
            label.pack(anchor="w", padx=10, pady=2)
            self._vehicle_info_labels[key] = label

        # Individual settings
        settings_frame = ttk.LabelFrame(self.vehicle_info_window, text="Individual Settings")
        settings_frame.pack(fill=tk.X, padx=10, pady=5)

        # Distraction
        dist_frame = ttk.Frame(settings_frame)
        dist_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(dist_frame, text="Distraction:").pack(side=tk.LEFT)
        self._veh_distract_var = tk.DoubleVar(value=vehicle.distraction_level)
        ttk.Scale(dist_frame, from_=0, to=1, variable=self._veh_distract_var,
                  orient=tk.HORIZONTAL, command=lambda v: self._update_vehicle_distraction(vehicle)).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Reaction modifier
        react_frame = ttk.Frame(settings_frame)
        react_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(react_frame, text="Reaction:").pack(side=tk.LEFT)
        self._veh_react_var = tk.DoubleVar(value=vehicle.reaction_modifier)
        ttk.Scale(react_frame, from_=0.5, to=2.0, variable=self._veh_react_var,
                  orient=tk.HORIZONTAL, command=lambda v: self._update_vehicle_reaction(vehicle)).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Aggression
        aggr_frame = ttk.Frame(settings_frame)
        aggr_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(aggr_frame, text="Aggression:").pack(side=tk.LEFT)
        self._veh_aggr_var = tk.DoubleVar(value=vehicle.aggression)
        ttk.Scale(aggr_frame, from_=0, to=1, variable=self._veh_aggr_var,
                  orient=tk.HORIZONTAL, command=lambda v: self._update_vehicle_aggression(vehicle)).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Buttons
        btn_frame = ttk.Frame(self.vehicle_info_window)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(btn_frame, text="Track Vehicle",
                   command=lambda: self._track_vehicle(vehicle)).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Remove Vehicle",
                   command=lambda: self._remove_vehicle(vehicle)).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Close",
                   command=self.vehicle_info_window.destroy).pack(side=tk.RIGHT, padx=2)

        # Start updating
        self._update_vehicle_info_window(vehicle)

    def _update_vehicle_info_window(self, vehicle: Vehicle):
        """Update the vehicle info window with current stats."""
        if not self.vehicle_info_window or not self.vehicle_info_window.winfo_exists():
            return

        if vehicle not in self.vehicles:
            self.vehicle_info_window.destroy()
            return

        # Update labels
        direction_names = {Direction.NORTH: "North", Direction.SOUTH: "South",
                          Direction.EAST: "East", Direction.WEST: "West"}

        self._vehicle_info_labels["speed"].config(text=f"Speed: {vehicle.speed:.1f} mph")
        self._vehicle_info_labels["position"].config(text=f"Position: ({vehicle.x:.2f}, {vehicle.y:.2f})")
        self._vehicle_info_labels["direction"].config(text=f"Direction: {direction_names[vehicle.direction]}")
        self._vehicle_info_labels["waiting"].config(text=f"Waiting Time: {vehicle.waiting_time:.1f}s")
        self._vehicle_info_labels["stopped"].config(text=f"Total Stopped: {vehicle.total_stopped_time:.1f}s")
        self._vehicle_info_labels["distance"].config(text=f"Distance: {vehicle.distance_traveled/5280:.2f} mi")
        self._vehicle_info_labels["stops"].config(text=f"Stops: {vehicle.stops_count}")

        status = "Stopped" if vehicle.is_stopped else "Moving"
        self._vehicle_info_labels["status"].config(text=f"Status: {status}")

        # Schedule next update
        self.vehicle_info_window.after(100, lambda: self._update_vehicle_info_window(vehicle))

    def _update_vehicle_distraction(self, vehicle: Vehicle):
        """Update vehicle distraction level."""
        vehicle.distraction_level = self._veh_distract_var.get()

    def _update_vehicle_reaction(self, vehicle: Vehicle):
        """Update vehicle reaction modifier."""
        vehicle.reaction_modifier = self._veh_react_var.get()

    def _update_vehicle_aggression(self, vehicle: Vehicle):
        """Update vehicle aggression level."""
        vehicle.aggression = self._veh_aggr_var.get()

    def _track_vehicle(self, vehicle: Vehicle):
        """Keep the selected vehicle highlighted."""
        self.selected_vehicle = vehicle
        self._draw_grid()

    def _remove_vehicle(self, vehicle: Vehicle):
        """Remove a vehicle from the simulation."""
        if vehicle in self.vehicles:
            self.vehicles.remove(vehicle)
            if self.selected_vehicle == vehicle:
                self.selected_vehicle = None
            if self.vehicle_info_window:
                self.vehicle_info_window.destroy()
            self._draw_grid()

    def _show_vehicle_properties_window(self, vehicle: Vehicle):
        """Show detailed properties window for a vehicle (right-click)."""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Vehicle #{vehicle.id} Properties")
        dialog.geometry("350x500")
        dialog.transient(self.root)

        # Type info
        info_frame = ttk.LabelFrame(dialog, text="Vehicle Info")
        info_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(info_frame, text=f"ID: {vehicle.id}").pack(anchor="w", padx=10)
        ttk.Label(info_frame, text=f"Type: {vehicle.vehicle_type.value}").pack(anchor="w", padx=10)
        ttk.Label(info_frame, text=f"Length: {vehicle.length:.1f} ft").pack(anchor="w", padx=10)
        ttk.Label(info_frame, text=f"Width: {vehicle.width:.1f} ft").pack(anchor="w", padx=10)

        # Performance
        perf_frame = ttk.LabelFrame(dialog, text="Performance Settings")
        perf_frame.pack(fill=tk.X, padx=10, pady=5)

        # Target speed
        speed_frame = ttk.Frame(perf_frame)
        speed_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(speed_frame, text="Target Speed (mph):").pack(side=tk.LEFT)
        speed_var = tk.DoubleVar(value=vehicle.target_speed)
        speed_scale = ttk.Scale(speed_frame, from_=15, to=55, variable=speed_var, orient=tk.HORIZONTAL)
        speed_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        speed_label = ttk.Label(speed_frame, text=f"{vehicle.target_speed:.0f}")
        speed_label.pack(side=tk.RIGHT)
        speed_var.trace("w", lambda *args: (setattr(vehicle, 'target_speed', speed_var.get()),
                                             speed_label.config(text=f"{speed_var.get():.0f}")))

        # Acceleration
        accel_frame = ttk.Frame(perf_frame)
        accel_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(accel_frame, text="Acceleration (ft/s²):").pack(side=tk.LEFT)
        accel_var = tk.DoubleVar(value=vehicle.acceleration)
        accel_scale = ttk.Scale(accel_frame, from_=2, to=15, variable=accel_var, orient=tk.HORIZONTAL)
        accel_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        accel_label = ttk.Label(accel_frame, text=f"{vehicle.acceleration:.1f}")
        accel_label.pack(side=tk.RIGHT)
        accel_var.trace("w", lambda *args: (setattr(vehicle, 'acceleration', accel_var.get()),
                                             accel_label.config(text=f"{accel_var.get():.1f}")))

        # Deceleration
        decel_frame = ttk.Frame(perf_frame)
        decel_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(decel_frame, text="Max Deceleration:").pack(side=tk.LEFT)
        decel_var = tk.DoubleVar(value=vehicle.max_deceleration)
        decel_scale = ttk.Scale(decel_frame, from_=5, to=20, variable=decel_var, orient=tk.HORIZONTAL)
        decel_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        decel_label = ttk.Label(decel_frame, text=f"{vehicle.max_deceleration:.1f}")
        decel_label.pack(side=tk.RIGHT)
        decel_var.trace("w", lambda *args: (setattr(vehicle, 'max_deceleration', decel_var.get()),
                                             decel_label.config(text=f"{decel_var.get():.1f}")))

        # Behavior
        behav_frame = ttk.LabelFrame(dialog, text="Behavior Settings")
        behav_frame.pack(fill=tk.X, padx=10, pady=5)

        # Distraction
        dist_frame = ttk.Frame(behav_frame)
        dist_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(dist_frame, text="Distraction Level:").pack(side=tk.LEFT)
        dist_var = tk.DoubleVar(value=vehicle.distraction_level)
        dist_scale = ttk.Scale(dist_frame, from_=0, to=1, variable=dist_var, orient=tk.HORIZONTAL)
        dist_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        dist_label = ttk.Label(dist_frame, text=f"{vehicle.distraction_level:.0%}")
        dist_label.pack(side=tk.RIGHT)
        dist_var.trace("w", lambda *args: (setattr(vehicle, 'distraction_level', dist_var.get()),
                                            dist_label.config(text=f"{dist_var.get():.0%}")))

        # Reaction
        react_frame = ttk.Frame(behav_frame)
        react_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(react_frame, text="Reaction Modifier:").pack(side=tk.LEFT)
        react_var = tk.DoubleVar(value=vehicle.reaction_modifier)
        react_scale = ttk.Scale(react_frame, from_=0.5, to=2.0, variable=react_var, orient=tk.HORIZONTAL)
        react_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        react_label = ttk.Label(react_frame, text=f"{vehicle.reaction_modifier:.2f}x")
        react_label.pack(side=tk.RIGHT)
        react_var.trace("w", lambda *args: (setattr(vehicle, 'reaction_modifier', react_var.get()),
                                             react_label.config(text=f"{react_var.get():.2f}x")))

        # Aggression
        aggr_frame = ttk.Frame(behav_frame)
        aggr_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(aggr_frame, text="Aggression:").pack(side=tk.LEFT)
        aggr_var = tk.DoubleVar(value=vehicle.aggression)
        aggr_scale = ttk.Scale(aggr_frame, from_=0, to=1, variable=aggr_var, orient=tk.HORIZONTAL)
        aggr_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        aggr_label = ttk.Label(aggr_frame, text=f"{vehicle.aggression:.0%}")
        aggr_label.pack(side=tk.RIGHT)
        aggr_var.trace("w", lambda *args: (setattr(vehicle, 'aggression', aggr_var.get()),
                                            aggr_label.config(text=f"{aggr_var.get():.0%}")))

        # Color picker
        color_frame = ttk.LabelFrame(dialog, text="Appearance")
        color_frame.pack(fill=tk.X, padx=10, pady=5)

        colors = ["#3498db", "#2ecc71", "#9b59b6", "#e74c3c", "#f39c12",
                  "#1abc9c", "#7f8c8d", "#95a5a6", "#e67e22", "#8e44ad"]

        color_btn_frame = ttk.Frame(color_frame)
        color_btn_frame.pack(pady=5)

        for i, color in enumerate(colors):
            btn = tk.Button(color_btn_frame, bg=color, width=2, height=1,
                           command=lambda c=color: self._set_vehicle_color(vehicle, c))
            btn.grid(row=0, column=i, padx=2)

        # Close button
        ttk.Button(dialog, text="Close", command=dialog.destroy).pack(pady=10)

    def _set_vehicle_color(self, vehicle: Vehicle, color: str):
        """Set vehicle color."""
        vehicle.color = color
        self._draw_grid()

    def _show_signal_editor(self, cell: GridCell):
        """Show dialog to edit individual signal timing."""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Edit Signal at ({cell.x}, {cell.y})")
        dialog.geometry("300x400")
        dialog.transient(self.root)

        signal = cell.signal

        ttk.Label(dialog, text=f"Signal Type: {signal.signal_type.value}").pack(pady=5)

        # Timing controls for traffic lights
        if signal.signal_type == SignalType.TRAFFIC_LIGHT:
            # Green NS
            frame = ttk.Frame(dialog)
            frame.pack(fill=tk.X, padx=10, pady=5)
            ttk.Label(frame, text="Green N/S (s):").pack(side=tk.LEFT)
            ns_var = tk.DoubleVar(value=signal.green_time_ns)
            ttk.Scale(frame, from_=10, to=120, variable=ns_var, orient=tk.HORIZONTAL).pack(side=tk.LEFT, fill=tk.X, expand=True)
            ns_label = ttk.Label(frame, text=f"{signal.green_time_ns:.0f}s")
            ns_label.pack(side=tk.RIGHT)
            ns_var.trace("w", lambda *args: ns_label.config(text=f"{ns_var.get():.0f}s"))

            # Green EW
            frame = ttk.Frame(dialog)
            frame.pack(fill=tk.X, padx=10, pady=5)
            ttk.Label(frame, text="Green E/W (s):").pack(side=tk.LEFT)
            ew_var = tk.DoubleVar(value=signal.green_time_ew)
            ttk.Scale(frame, from_=10, to=120, variable=ew_var, orient=tk.HORIZONTAL).pack(side=tk.LEFT, fill=tk.X, expand=True)
            ew_label = ttk.Label(frame, text=f"{signal.green_time_ew:.0f}s")
            ew_label.pack(side=tk.RIGHT)
            ew_var.trace("w", lambda *args: ew_label.config(text=f"{ew_var.get():.0f}s"))

            # Yellow
            frame = ttk.Frame(dialog)
            frame.pack(fill=tk.X, padx=10, pady=5)
            ttk.Label(frame, text="Yellow (s):").pack(side=tk.LEFT)
            yellow_var = tk.DoubleVar(value=signal.yellow_time)
            ttk.Scale(frame, from_=2, to=8, variable=yellow_var, orient=tk.HORIZONTAL).pack(side=tk.LEFT, fill=tk.X, expand=True)

            # All red
            frame = ttk.Frame(dialog)
            frame.pack(fill=tk.X, padx=10, pady=5)
            ttk.Label(frame, text="All-Red (s):").pack(side=tk.LEFT)
            red_var = tk.DoubleVar(value=signal.all_red_time)
            ttk.Scale(frame, from_=1, to=5, variable=red_var, orient=tk.HORIZONTAL).pack(side=tk.LEFT, fill=tk.X, expand=True)

            def apply():
                signal.green_time_ns = ns_var.get()
                signal.green_time_ew = ew_var.get()
                signal.yellow_time = yellow_var.get()
                signal.all_red_time = red_var.get()
                dialog.destroy()

            ttk.Button(dialog, text="Apply", command=apply).pack(pady=10)

        # Tourism area toggle
        tourism_var = tk.BooleanVar(value=cell.is_tourism_area)
        ttk.Checkbutton(dialog, text="Tourism Area (more pedestrians)",
                        variable=tourism_var).pack(pady=5)

        def save_tourism():
            cell.is_tourism_area = tourism_var.get()
            signal.is_tourism_area = tourism_var.get()

        tourism_var.trace("w", lambda *args: save_tourism())

        ttk.Button(dialog, text="Close", command=dialog.destroy).pack(pady=10)

    def _on_canvas_resize(self, event):
        """Handle canvas resize."""
        self._draw_grid()

    # ========================================================================
    # Simulation Logic
    # ========================================================================

    def _toggle_simulation(self):
        """Start or stop the simulation."""
        self.simulation_running = not self.simulation_running
        if self.simulation_running:
            self.start_btn.config(text="Pause")
            self.last_update_time = time.time()
        else:
            self.start_btn.config(text="Start")

    def _reset_simulation(self):
        """Reset the simulation to initial state."""
        self.simulation_running = False
        self.start_btn.config(text="Start")
        self.sim_time = 0.0
        self.vehicles.clear()
        self.current_stats = SimulationStats(name="Current")

        # Reset all signals
        for row in self.grid:
            for cell in row:
                if cell.signal:
                    cell.signal.phase_time = 0.0
                    cell.signal.current_phase = 0
                    for d in Direction:
                        cell.signal.states[d] = SignalState.RED

        self._draw_grid()
        self._update_stats_display()

    def _clear_vehicles(self):
        """Clear all vehicles but keep running."""
        self.vehicles.clear()
        self._draw_grid()

    def _update_loop(self):
        """Main simulation update loop."""
        if self.simulation_running:
            current_time = time.time()
            dt = (current_time - self.last_update_time) * self.simulation_speed
            self.last_update_time = current_time

            self.sim_time += dt

            # Update signals
            self._update_signals(dt)

            # Update vehicles
            self._update_vehicles(dt)

            # Spawn new vehicles
            self._spawn_vehicles(dt)

            # Update display
            self._draw_grid()
            self._update_stats_display()

            # Update time display
            minutes = int(self.sim_time) // 60
            seconds = int(self.sim_time) % 60
            self.time_label.config(text=f"Time: {minutes}:{seconds:02d}")

        # Schedule next update
        self.root.after(33, self._update_loop)  # ~30 FPS

    def _update_signals(self, dt):
        """Update all traffic signals."""
        for row in self.grid:
            for cell in row:
                if cell.signal and cell.signal.signal_type == SignalType.TRAFFIC_LIGHT:
                    self._update_traffic_light(cell.signal, dt)

    def _update_traffic_light(self, signal: TrafficSignal, dt):
        """Update a traffic light's phase."""
        signal.phase_time += dt

        # Phase timing: Green NS -> Yellow NS -> All Red -> Green EW -> Yellow EW -> All Red
        phases = [
            (signal.green_time_ns, {Direction.NORTH: SignalState.GREEN, Direction.SOUTH: SignalState.GREEN,
                                     Direction.EAST: SignalState.RED, Direction.WEST: SignalState.RED}),
            (signal.yellow_time, {Direction.NORTH: SignalState.YELLOW, Direction.SOUTH: SignalState.YELLOW,
                                   Direction.EAST: SignalState.RED, Direction.WEST: SignalState.RED}),
            (signal.all_red_time, {d: SignalState.RED for d in Direction}),
            (signal.green_time_ew, {Direction.NORTH: SignalState.RED, Direction.SOUTH: SignalState.RED,
                                     Direction.EAST: SignalState.GREEN, Direction.WEST: SignalState.GREEN}),
            (signal.yellow_time, {Direction.NORTH: SignalState.RED, Direction.SOUTH: SignalState.RED,
                                   Direction.EAST: SignalState.YELLOW, Direction.WEST: SignalState.YELLOW}),
            (signal.all_red_time, {d: SignalState.RED for d in Direction}),
        ]

        # Handle pedestrian phase in tourism areas
        if signal.is_tourism_area and self.ped_var.get():
            # Add pedestrian delay randomly
            if random.random() < 0.01 * self.tourism_var.get():
                signal.pedestrian_phase = True
                signal.pedestrian_time_remaining = TrafficDefaults.PEDESTRIAN_WALK_TIME + \
                                                   TrafficDefaults.PEDESTRIAN_CLEARANCE

        if signal.pedestrian_phase:
            signal.pedestrian_time_remaining -= dt
            if signal.pedestrian_time_remaining <= 0:
                signal.pedestrian_phase = False
            # All directions red during pedestrian phase
            for d in Direction:
                signal.states[d] = SignalState.RED
            return

        # Normal signal operation
        current_phase_duration = phases[signal.current_phase][0]

        if signal.phase_time >= current_phase_duration:
            signal.phase_time = 0
            signal.current_phase = (signal.current_phase + 1) % len(phases)

        signal.states.update(phases[signal.current_phase][1])

    def _get_condition_modifiers(self):
        """Calculate condition modifiers based on weather, time, distractions."""
        # Weather modifier
        weather_map = {
            WeatherType.CLEAR: (TrafficDefaults.WEATHER_CLEAR, 1.0),
            WeatherType.RAIN: (TrafficDefaults.WEATHER_RAIN, TrafficDefaults.SPEED_RAIN),
            WeatherType.HEAVY_RAIN: (TrafficDefaults.WEATHER_HEAVY_RAIN, TrafficDefaults.SPEED_HEAVY_RAIN),
            WeatherType.SNOW: (TrafficDefaults.WEATHER_SNOW, TrafficDefaults.SPEED_SNOW),
            WeatherType.FOG: (TrafficDefaults.WEATHER_FOG, TrafficDefaults.SPEED_FOG),
            WeatherType.ICE: (TrafficDefaults.WEATHER_ICE, TrafficDefaults.SPEED_ICE),
        }

        weather = WeatherType(self.weather_var.get())
        reaction_mod, speed_mod = weather_map.get(weather, (1.0, 1.0))

        # Time of day modifier
        time_map = {
            TimeOfDay.MORNING_RUSH: (TrafficDefaults.TIME_RUSH_HOUR, 0.9),
            TimeOfDay.MIDDAY: (TrafficDefaults.TIME_DAY, 1.0),
            TimeOfDay.EVENING_RUSH: (TrafficDefaults.TIME_RUSH_HOUR, 0.9),
            TimeOfDay.EVENING: (TrafficDefaults.TIME_DAY, 1.0),
            TimeOfDay.NIGHT: (TrafficDefaults.TIME_NIGHT, 0.95),
            TimeOfDay.LATE_NIGHT: (TrafficDefaults.TIME_LATE_NIGHT, 1.0),
        }

        time_of_day = TimeOfDay(self.time_var.get())
        time_reaction, time_speed = time_map.get(time_of_day, (1.0, 1.0))
        reaction_mod *= time_reaction
        speed_mod *= time_speed

        # Distraction modifier
        distraction = self.distraction_var.get()
        if distraction < 0.25:
            distraction_mod = TrafficDefaults.DISTRACTION_NONE
        elif distraction < 0.5:
            distraction_mod = TrafficDefaults.DISTRACTION_LIGHT
        elif distraction < 0.75:
            distraction_mod = TrafficDefaults.DISTRACTION_MODERATE
        else:
            distraction_mod = TrafficDefaults.DISTRACTION_HEAVY

        reaction_mod *= distraction_mod

        return reaction_mod, speed_mod

    def _update_vehicles(self, dt):
        """Update all vehicle positions and behaviors."""
        global_reaction_mod, speed_mod = self._get_condition_modifiers()

        vehicles_to_remove = []

        for vehicle in self.vehicles:
            # Calculate individual reaction modifier
            individual_distraction = 1.0 + vehicle.distraction_level * 0.75
            reaction_mod = global_reaction_mod * vehicle.reaction_modifier * individual_distraction

            # Get cell vehicle is in
            gx = int(vehicle.x)
            gy = int(vehicle.y)

            # Check if vehicle left the grid
            if not (0 <= gx < self.grid_size and 0 <= gy < self.grid_size):
                vehicles_to_remove.append(vehicle)
                self.current_stats.throughput += 1
                continue

            cell = self.grid[gy][gx]

            # Determine target speed based on conditions
            base_target = vehicle.target_speed * speed_mod

            # Check for signals
            should_stop = False
            if cell.signal:
                should_stop = self._should_vehicle_stop(vehicle, cell.signal)

            # Check for vehicles ahead
            vehicle_ahead = self._get_vehicle_ahead(vehicle)
            if vehicle_ahead:
                # Maintain safe following distance (reduced by aggression)
                dist = self._distance_to_vehicle(vehicle, vehicle_ahead)
                aggression_factor = 1.0 - (vehicle.aggression * 0.4)  # Aggressive = 0.6x distance
                safe_dist = (TrafficDefaults.MIN_FOLLOWING_DISTANCE + \
                           vehicle.speed * TrafficDefaults.FOLLOWING_TIME_GAP * reaction_mod) * aggression_factor
                if dist < safe_dist:
                    should_stop = True
                elif dist < safe_dist * 2:
                    base_target = min(base_target, vehicle_ahead.speed * 0.9)

            # Update speed
            if should_stop:
                # Decelerate
                decel = vehicle.max_deceleration / reaction_mod
                vehicle.speed = max(0, vehicle.speed - decel * dt)

                if vehicle.speed == 0:
                    if not vehicle.is_stopped:
                        vehicle.is_stopped = True
                        vehicle.stop_start_time = self.sim_time
                        vehicle.stops_count += 1
                    vehicle.waiting_time += dt
            else:
                # Accelerate toward target
                accel = vehicle.acceleration / reaction_mod
                if vehicle.speed < base_target:
                    vehicle.speed = min(base_target, vehicle.speed + accel * dt)
                else:
                    vehicle.speed = max(base_target, vehicle.speed - accel * dt)

                if vehicle.is_stopped:
                    vehicle.is_stopped = False
                    vehicle.total_stopped_time += self.sim_time - vehicle.stop_start_time

            # Update position (convert mph to grid units per second)
            # Assuming each cell is ~100 feet, 1 mph = 1.467 ft/s
            speed_grid = vehicle.speed * 1.467 / 100  # grid cells per second

            if vehicle.direction == Direction.NORTH:
                vehicle.y -= speed_grid * dt
            elif vehicle.direction == Direction.SOUTH:
                vehicle.y += speed_grid * dt
            elif vehicle.direction == Direction.EAST:
                vehicle.x += speed_grid * dt
            elif vehicle.direction == Direction.WEST:
                vehicle.x -= speed_grid * dt

            vehicle.distance_traveled += vehicle.speed * dt

        # Remove vehicles that left grid
        for v in vehicles_to_remove:
            self.vehicles.remove(v)
            self.current_stats.total_stopped_time += v.total_stopped_time
            self.current_stats.total_distance += v.distance_traveled

    def _should_vehicle_stop(self, vehicle: Vehicle, signal: TrafficSignal) -> bool:
        """Determine if vehicle should stop for a signal."""
        # Get vehicle's position within the cell
        cell_x = vehicle.x - int(vehicle.x)
        cell_y = vehicle.y - int(vehicle.y)

        # Determine if vehicle is approaching or in the intersection
        # Stop lines are at about 0.4 from edge
        stop_line_threshold = 0.4
        in_intersection = (0.3 < cell_x < 0.7 and 0.3 < cell_y < 0.7)

        # If already in intersection, don't stop (keep moving to clear)
        if in_intersection and vehicle.speed > 5:
            return False

        # Check if approaching stop line
        approaching_stop = False
        if vehicle.direction == Direction.NORTH:
            approaching_stop = cell_y > (1 - stop_line_threshold) and cell_y < 0.9
        elif vehicle.direction == Direction.SOUTH:
            approaching_stop = cell_y < stop_line_threshold and cell_y > 0.1
        elif vehicle.direction == Direction.EAST:
            approaching_stop = cell_x < stop_line_threshold and cell_x > 0.1
        elif vehicle.direction == Direction.WEST:
            approaching_stop = cell_x > (1 - stop_line_threshold) and cell_x < 0.9

        if signal.signal_type == SignalType.TRAFFIC_LIGHT:
            state = signal.states.get(vehicle.direction, SignalState.RED)
            if state == SignalState.RED:
                # Only stop if approaching, not if already past
                if approaching_stop or (not in_intersection and vehicle.speed < 5):
                    return True
            elif state == SignalState.YELLOW:
                # Stop if can't clear intersection safely
                time_to_clear = 0.5 / max(vehicle.speed * 1.467 / 100, 0.1)
                if time_to_clear > signal.yellow_time * 0.5 and approaching_stop:
                    return True

        elif signal.signal_type in (SignalType.STOP_SIGN, SignalType.FOUR_WAY_STOP, SignalType.FLASHING_RED):
            # Must stop briefly, then proceed
            if approaching_stop and vehicle.waiting_time < TrafficDefaults.STARTUP_LOST_TIME:
                return True

        elif signal.signal_type == SignalType.YIELD_SIGN:
            # Yield if cross traffic present
            pass

        elif signal.signal_type == SignalType.ROUNDABOUT:
            # Yield to traffic in roundabout
            pass

        # Pedestrian phase blocks all at stop line
        if signal.pedestrian_phase and approaching_stop:
            return True

        return False

    def _get_vehicle_ahead(self, vehicle: Vehicle) -> Optional[Vehicle]:
        """Find the nearest vehicle ahead in the same lane."""
        min_dist = float('inf')
        nearest = None

        # Lane tolerance for same-lane detection
        lane_tolerance = 0.25  # Must be in same lane (within tolerance)

        for other in self.vehicles:
            if other is vehicle:
                continue
            if other.direction != vehicle.direction:
                continue

            # Check if in same lane (similar lateral position)
            if vehicle.direction in (Direction.NORTH, Direction.SOUTH):
                # For N/S, check x position similarity
                if abs(other.x - vehicle.x) > lane_tolerance:
                    continue
            else:
                # For E/W, check y position similarity
                if abs(other.y - vehicle.y) > lane_tolerance:
                    continue

            # Check if ahead
            if vehicle.direction == Direction.NORTH and other.y < vehicle.y:
                dist = vehicle.y - other.y
            elif vehicle.direction == Direction.SOUTH and other.y > vehicle.y:
                dist = other.y - vehicle.y
            elif vehicle.direction == Direction.EAST and other.x > vehicle.x:
                dist = other.x - vehicle.x
            elif vehicle.direction == Direction.WEST and other.x < vehicle.x:
                dist = vehicle.x - other.x
            else:
                continue

            if dist < min_dist:
                min_dist = dist
                nearest = other

        return nearest

    def _check_vehicle_collision(self, vehicle: Vehicle) -> bool:
        """Check if vehicle would collide with any other vehicle."""
        # Vehicle bounding box (in grid units)
        v_length = vehicle.length / 100  # Convert to grid units
        v_width = vehicle.width / 100

        for other in self.vehicles:
            if other is vehicle:
                continue

            o_length = other.length / 100
            o_width = other.width / 100

            # Simple AABB collision with lane offset
            if vehicle.direction in (Direction.NORTH, Direction.SOUTH):
                v_x = vehicle.x + vehicle.lane_offset
                v_y = vehicle.y
            else:
                v_x = vehicle.x
                v_y = vehicle.y + vehicle.lane_offset

            if other.direction in (Direction.NORTH, Direction.SOUTH):
                o_x = other.x + other.lane_offset
                o_y = other.y
            else:
                o_x = other.x
                o_y = other.y + other.lane_offset

            # Check overlap
            dx = abs(v_x - o_x)
            dy = abs(v_y - o_y)

            min_dx = (v_width + o_width) / 2 + 0.05
            min_dy = (v_length + o_length) / 2 + 0.05

            if dx < min_dx and dy < min_dy:
                return True

        return False

    def _distance_to_vehicle(self, v1: Vehicle, v2: Vehicle) -> float:
        """Calculate distance between two vehicles in grid units."""
        return math.sqrt((v1.x - v2.x)**2 + (v1.y - v2.y)**2)

    def _spawn_vehicles(self, dt):
        """Spawn new vehicles at entry points."""
        # Find entry points (roads at grid edges)
        density = self.density_var.get()
        spawn_rate = density * 0.5  # vehicles per second per entry

        entry_points = []
        for y in range(self.grid_size):
            for x in range(self.grid_size):
                cell = self.grid[y][x]
                if cell.road_type == RoadType.NONE:
                    continue

                # Check if at edge
                if x == 0 and cell.road_type in (RoadType.STRAIGHT_EW, RoadType.INTERSECTION):
                    entry_points.append((x, y, Direction.EAST))
                if x == self.grid_size - 1 and cell.road_type in (RoadType.STRAIGHT_EW, RoadType.INTERSECTION):
                    entry_points.append((x, y, Direction.WEST))
                if y == 0 and cell.road_type in (RoadType.STRAIGHT_NS, RoadType.INTERSECTION):
                    entry_points.append((x, y, Direction.SOUTH))
                if y == self.grid_size - 1 and cell.road_type in (RoadType.STRAIGHT_NS, RoadType.INTERSECTION):
                    entry_points.append((x, y, Direction.NORTH))

        for x, y, direction in entry_points:
            if random.random() < spawn_rate * dt:
                # Determine vehicle type
                truck_ratio = self.truck_var.get()
                if random.random() < truck_ratio:
                    vtype = random.choice([VehicleType.TRUCK, VehicleType.SEMI])
                else:
                    vtype = VehicleType.CAR

                # Calculate spawn position with lane offset
                spawn_x = float(x) + 0.5
                spawn_y = float(y) + 0.5

                # Create temporary vehicle to get lane offset
                temp_vehicle = Vehicle(
                    id=0, vehicle_type=vtype, x=spawn_x, y=spawn_y, direction=direction
                )
                lane_offset = temp_vehicle.lane_offset

                # Apply lane offset to spawn position check
                if direction in (Direction.NORTH, Direction.SOUTH):
                    check_x = spawn_x + lane_offset
                    check_y = spawn_y
                else:
                    check_x = spawn_x
                    check_y = spawn_y + lane_offset

                # Check if spawn point is clear (with lane awareness)
                spawn_clear = True
                min_spawn_dist = 0.4  # Minimum distance between vehicles

                for v in self.vehicles:
                    # Only check vehicles in same lane (same direction)
                    if v.direction != direction:
                        continue

                    if direction in (Direction.NORTH, Direction.SOUTH):
                        v_lane_x = v.x + v.lane_offset
                        if abs(v_lane_x - check_x) < 0.3 and abs(v.y - spawn_y) < min_spawn_dist:
                            spawn_clear = False
                            break
                    else:
                        v_lane_y = v.y + v.lane_offset
                        if abs(v_lane_y - check_y) < 0.3 and abs(v.x - spawn_x) < min_spawn_dist:
                            spawn_clear = False
                            break

                if spawn_clear:
                    self.vehicle_id_counter += 1
                    vehicle = Vehicle(
                        id=self.vehicle_id_counter,
                        vehicle_type=vtype,
                        x=spawn_x,
                        y=spawn_y,
                        direction=direction
                    )
                    # Set individual modifiers with some randomness
                    vehicle.spawn_time = self.sim_time
                    vehicle.distraction_level = random.random() * self.distraction_var.get()
                    vehicle.reaction_modifier = random.uniform(0.8, 1.2)
                    vehicle.aggression = random.random()
                    self.vehicles.append(vehicle)
                    self.current_stats.total_vehicles += 1

    def _update_stats_display(self):
        """Update the statistics display."""
        active = len(self.vehicles)
        self.stats_labels["vehicles"].config(text=f"Active Vehicles: {active}")
        self.stats_labels["throughput"].config(text=f"Completed: {self.current_stats.throughput}")

        if active > 0:
            total_wait = sum(v.waiting_time for v in self.vehicles)
            avg_wait = total_wait / active
            max_wait = max(v.waiting_time for v in self.vehicles) if self.vehicles else 0
            avg_speed = sum(v.speed for v in self.vehicles) / active

            self.stats_labels["avg_wait"].config(text=f"Avg Wait: {avg_wait:.1f}s")
            self.stats_labels["max_wait"].config(text=f"Max Wait: {max_wait:.1f}s")
            self.stats_labels["avg_speed"].config(text=f"Avg Speed: {avg_speed:.1f} mph")
            self.stats_labels["total_stopped"].config(
                text=f"Total Stopped: {self.current_stats.total_stopped_time:.1f}s")

            # Efficiency = time moving / total time
            if self.sim_time > 0 and self.current_stats.total_vehicles > 0:
                efficiency = 100 * (1 - total_wait / (self.sim_time * active))
                self.stats_labels["efficiency"].config(text=f"Efficiency: {efficiency:.1f}%")

        # Update impact label
        reaction_mod, speed_mod = self._get_condition_modifiers()
        self.impact_label.config(
            text=f"Reaction modifier: {reaction_mod:.2f}x\nSpeed modifier: {speed_mod:.2f}x")

    # ========================================================================
    # Comparison & Analytics
    # ========================================================================

    def _save_simulation_snapshot(self):
        """Save current simulation stats for comparison."""
        if self.sim_time < 10:
            messagebox.showwarning("Warning", "Run simulation for at least 10 seconds before saving.")
            return

        # Get name for snapshot
        name = f"Sim {len(self.saved_simulations) + 1}"

        # Calculate final stats
        active = len(self.vehicles)
        total_wait = sum(v.waiting_time for v in self.vehicles) if self.vehicles else 0

        snapshot = SimulationStats(
            name=name,
            total_vehicles=self.current_stats.total_vehicles,
            total_stopped_time=self.current_stats.total_stopped_time + total_wait,
            total_travel_time=self.sim_time * active,
            total_distance=self.current_stats.total_distance,
            average_speed=sum(v.speed for v in self.vehicles) / active if active > 0 else 0,
            average_wait_time=total_wait / active if active > 0 else 0,
            max_wait_time=max(v.waiting_time for v in self.vehicles) if self.vehicles else 0,
            throughput=self.current_stats.throughput,
            timestamp=self.sim_time,
            config_snapshot={
                "weather": self.weather_var.get(),
                "time": self.time_var.get(),
                "distraction": self.distraction_var.get(),
                "density": self.density_var.get(),
                "truck_ratio": self.truck_var.get(),
                "green_ns": self.green_ns_var.get(),
                "green_ew": self.green_ew_var.get(),
                "yellow": self.yellow_var.get(),
                "all_red": self.all_red_var.get(),
            }
        )

        self.saved_simulations.append(snapshot)
        self.comparison_listbox.insert(tk.END, f"{name} - {self.sim_time:.0f}s")

        messagebox.showinfo("Saved", f"Simulation snapshot '{name}' saved for comparison.")

    def _show_comparison_details(self, event):
        """Show details of selected simulation."""
        selection = self.comparison_listbox.curselection()
        if not selection:
            return

        idx = selection[0]
        if idx < len(self.saved_simulations):
            sim = self.saved_simulations[idx]

            self.comparison_text.delete(1.0, tk.END)
            text = f"""Simulation: {sim.name}
Duration: {sim.timestamp:.1f}s
========================
Total Vehicles: {sim.total_vehicles}
Completed: {sim.throughput}
Avg Wait: {sim.average_wait_time:.2f}s
Max Wait: {sim.max_wait_time:.2f}s
Total Stopped: {sim.total_stopped_time:.1f}s
Avg Speed: {sim.average_speed:.1f} mph

Configuration:
- Weather: {sim.config_snapshot.get('weather', 'N/A')}
- Time: {sim.config_snapshot.get('time', 'N/A')}
- Green N/S: {sim.config_snapshot.get('green_ns', 0):.0f}s
- Green E/W: {sim.config_snapshot.get('green_ew', 0):.0f}s
- Density: {sim.config_snapshot.get('density', 0)*100:.0f}%
- Trucks: {sim.config_snapshot.get('truck_ratio', 0)*100:.0f}%
"""
            self.comparison_text.insert(1.0, text)

    def _compare_all_simulations(self):
        """Compare all saved simulations."""
        if len(self.saved_simulations) < 2:
            messagebox.showwarning("Warning", "Need at least 2 saved simulations to compare.")
            return

        # Sort by efficiency (lower avg wait = better)
        sorted_sims = sorted(self.saved_simulations, key=lambda s: s.average_wait_time)

        self.comparison_text.delete(1.0, tk.END)
        text = "COMPARISON RESULTS\n"
        text += "==================\n"
        text += "Ranked by Average Wait Time:\n\n"

        for i, sim in enumerate(sorted_sims, 1):
            efficiency = 100 * sim.throughput / max(sim.total_vehicles, 1)
            text += f"{i}. {sim.name}\n"
            text += f"   Avg Wait: {sim.average_wait_time:.2f}s\n"
            text += f"   Throughput: {efficiency:.1f}%\n"
            text += f"   Total Stopped: {sim.total_stopped_time:.1f}s\n\n"

        # Best configuration
        best = sorted_sims[0]
        text += f"\nBEST CONFIG: {best.name}\n"
        text += f"- Green N/S: {best.config_snapshot.get('green_ns', 0):.0f}s\n"
        text += f"- Green E/W: {best.config_snapshot.get('green_ew', 0):.0f}s\n"

        self.comparison_text.insert(1.0, text)

    def _delete_selected_comparison(self):
        """Delete selected simulation from comparison."""
        selection = self.comparison_listbox.curselection()
        if selection:
            idx = selection[0]
            self.comparison_listbox.delete(idx)
            if idx < len(self.saved_simulations):
                del self.saved_simulations[idx]

    def _export_comparison_csv(self):
        """Export comparison data to CSV."""
        if not self.saved_simulations:
            messagebox.showwarning("Warning", "No simulations to export.")
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )

        if filename:
            with open(filename, 'w') as f:
                f.write("Name,Duration,Total Vehicles,Throughput,Avg Wait,Max Wait,")
                f.write("Total Stopped,Avg Speed,Weather,Time,Green NS,Green EW,Density,Trucks\n")

                for sim in self.saved_simulations:
                    cfg = sim.config_snapshot
                    f.write(f"{sim.name},{sim.timestamp:.1f},{sim.total_vehicles},")
                    f.write(f"{sim.throughput},{sim.average_wait_time:.2f},{sim.max_wait_time:.2f},")
                    f.write(f"{sim.total_stopped_time:.1f},{sim.average_speed:.1f},")
                    f.write(f"{cfg.get('weather', '')},{cfg.get('time', '')},")
                    f.write(f"{cfg.get('green_ns', 0):.0f},{cfg.get('green_ew', 0):.0f},")
                    f.write(f"{cfg.get('density', 0):.2f},{cfg.get('truck_ratio', 0):.2f}\n")

            messagebox.showinfo("Exported", f"Data exported to {filename}")

    # ========================================================================
    # Build Tools
    # ========================================================================

    def _update_build_mode(self):
        """Update the current build mode."""
        self.build_mode = self.build_mode_var.get()

    def _apply_grid_size(self):
        """Apply new grid size, resetting the simulation."""
        new_size = self.grid_size_var.get()

        if new_size == self.grid_size:
            return

        # Confirm if simulation has data
        if self.vehicles or any(cell.road_type != RoadType.NONE
                                for row in self.grid for cell in row):
            if not messagebox.askyesno("Confirm",
                f"Changing grid size to {new_size}x{new_size} will clear the current layout.\nContinue?"):
                self.grid_size_var.set(self.grid_size)
                return

        # Update grid size
        old_size = self.grid_size
        self.grid_size = new_size

        # Clear and reinitialize
        self.vehicles.clear()
        self.selected_vehicle = None
        self.sim_time = 0.0
        self.current_stats = SimulationStats(name="Current")

        # Reinitialize grid
        self._init_grid()
        self._draw_grid()

        # Update label
        self.grid_size_label.config(text=f"({new_size}x{new_size})")
        self.status_label.config(text=f"Grid resized from {old_size}x{old_size} to {new_size}x{new_size}")

    def _generate_random_city(self):
        """Generate a random city grid layout."""
        self._clear_grid()

        # Create main roads (every 2-3 cells)
        main_roads_x = set()
        main_roads_y = set()

        x = random.randint(1, 2)
        while x < self.grid_size - 1:
            main_roads_x.add(x)
            x += random.randint(2, 3)

        y = random.randint(1, 2)
        while y < self.grid_size - 1:
            main_roads_y.add(y)
            y += random.randint(2, 3)

        # Place roads
        for y in range(self.grid_size):
            for x in range(self.grid_size):
                is_x_road = x in main_roads_x
                is_y_road = y in main_roads_y

                cell = self.grid[y][x]

                if is_x_road and is_y_road:
                    cell.road_type = RoadType.INTERSECTION
                    # Random signal type
                    signal_type = random.choice([
                        SignalType.TRAFFIC_LIGHT,
                        SignalType.TRAFFIC_LIGHT,
                        SignalType.FOUR_WAY_STOP,
                        SignalType.ROUNDABOUT,
                    ])
                    cell.signal = TrafficSignal(
                        signal_type=signal_type,
                        green_time_ns=self.green_ns_var.get(),
                        green_time_ew=self.green_ew_var.get()
                    )
                elif is_x_road:
                    cell.road_type = RoadType.STRAIGHT_NS
                elif is_y_road:
                    cell.road_type = RoadType.STRAIGHT_EW

                # Random tourism areas
                if cell.road_type != RoadType.NONE and random.random() < 0.1:
                    cell.is_tourism_area = True
                    if cell.signal:
                        cell.signal.is_tourism_area = True

        self._draw_grid()
        self.status_label.config(text="Generated random city grid")

    def _clear_grid(self):
        """Clear the entire grid."""
        for row in self.grid:
            for cell in row:
                cell.road_type = RoadType.NONE
                cell.signal = None
                cell.is_tourism_area = False
        self._draw_grid()

    def _save_layout(self):
        """Save current layout to file."""
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if filename:
            data = {
                "grid_size": self.grid_size,
                "cells": []
            }

            for row in self.grid:
                for cell in row:
                    if cell.road_type != RoadType.NONE:
                        cell_data = {
                            "x": cell.x,
                            "y": cell.y,
                            "road_type": cell.road_type.name,
                            "is_tourism": cell.is_tourism_area,
                        }
                        if cell.signal:
                            cell_data["signal"] = {
                                "type": cell.signal.signal_type.name,
                                "green_ns": cell.signal.green_time_ns,
                                "green_ew": cell.signal.green_time_ew,
                                "yellow": cell.signal.yellow_time,
                                "all_red": cell.signal.all_red_time,
                            }
                        data["cells"].append(cell_data)

            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)

            messagebox.showinfo("Saved", f"Layout saved to {filename}")

    def _load_layout(self):
        """Load layout from file."""
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if filename:
            try:
                with open(filename, 'r') as f:
                    data = json.load(f)

                self._clear_grid()

                for cell_data in data.get("cells", []):
                    x, y = cell_data["x"], cell_data["y"]
                    if 0 <= x < self.grid_size and 0 <= y < self.grid_size:
                        cell = self.grid[y][x]
                        cell.road_type = RoadType[cell_data["road_type"]]
                        cell.is_tourism_area = cell_data.get("is_tourism", False)

                        if "signal" in cell_data:
                            sig_data = cell_data["signal"]
                            cell.signal = TrafficSignal(
                                signal_type=SignalType[sig_data["type"]],
                                green_time_ns=sig_data.get("green_ns", 30),
                                green_time_ew=sig_data.get("green_ew", 30),
                                yellow_time=sig_data.get("yellow", 4),
                                all_red_time=sig_data.get("all_red", 2),
                                is_tourism_area=cell.is_tourism_area,
                            )

                self._draw_grid()
                messagebox.showinfo("Loaded", "Layout loaded successfully")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load layout: {e}")

    def _import_osm(self):
        """Import road data from OpenStreetMap."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Import from OpenStreetMap")
        dialog.geometry("450x280")
        dialog.transient(self.root)

        ttk.Label(dialog, text="Enter location name or coordinates:").pack(pady=10)

        location_var = tk.StringVar(value="New York, NY")
        entry = ttk.Entry(dialog, textvariable=location_var, width=40)
        entry.pack(pady=5)

        ttk.Label(dialog, text="Import Options:", font=("Arial", 10, "bold")).pack(pady=10)

        def do_quick_import():
            location = location_var.get()
            dialog.destroy()
            self._fetch_osm_data(location)

        def do_map_tracer():
            location = location_var.get()
            dialog.destroy()
            self._open_map_tracer(location)

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Quick Generate\n(Auto layout)",
                   command=do_quick_import).pack(side=tk.LEFT, padx=10, pady=5)

        ttk.Button(btn_frame, text="Map Tracer\n(Trace over map)",
                   command=do_map_tracer).pack(side=tk.LEFT, padx=10, pady=5)

        ttk.Label(dialog, text="Map Tracer: Opens satellite/map view to trace streets\n"
                              "Quick Generate: Creates grid based on location pattern",
                              font=("Arial", 8)).pack(pady=10)

        ttk.Button(dialog, text="Cancel", command=dialog.destroy).pack(pady=5)

    def _open_map_tracer(self, location: str):
        """Open the Map Tracer window for tracing streets over a map."""
        MapTracerWindow(self.root, self, location)

    def _fetch_osm_data(self, location: str):
        """Fetch and process real OSM street data for location."""
        self.status_label.config(text=f"Fetching data for {location}...")
        self.root.update()

        try:
            # Use Nominatim to geocode
            encoded_location = urllib.parse.quote(location)
            url = f"https://nominatim.openstreetmap.org/search?q={encoded_location}&format=json&limit=1"

            req = urllib.request.Request(url, headers={'User-Agent': 'TrafficSimulator/1.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())

            if data:
                lat = float(data[0]['lat'])
                lon = float(data[0]['lon'])

                # Try to fetch real street data from Overpass API
                self.status_label.config(text="Fetching street network from OpenStreetMap...")
                self.root.update()

                if self._fetch_real_streets(lat, lon):
                    self.status_label.config(text=f"Imported real streets from {location}")
                else:
                    # Fallback to generated grid
                    self._generate_city_from_coords(lat, lon)
                    self.status_label.config(text=f"Generated grid for {location}")
            else:
                messagebox.showwarning("Not Found", f"Location '{location}' not found.")
                self.status_label.config(text="Import failed - location not found")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch OSM data: {e}")
            self.status_label.config(text="Import failed")

    def _fetch_real_streets(self, lat: float, lon: float) -> bool:
        """Fetch real street network data from Overpass API."""
        try:
            # Calculate bounding box - scale with grid size
            # Base: 500m for 8x8 grid, scales proportionally
            # 1 degree latitude ≈ 111km, 1 degree longitude varies with latitude
            scale_factor = self.grid_size / 8.0
            base_delta = 0.005  # ~500m for 8x8
            lat_delta = base_delta * scale_factor
            lon_delta = lat_delta / math.cos(math.radians(lat))

            bbox = f"{lat - lat_delta},{lon - lon_delta},{lat + lat_delta},{lon + lon_delta}"

            # Overpass query for roads and traffic signals
            # Timeout scales with grid size
            timeout = min(60, int(25 * scale_factor))
            query = f"""
            [out:json][timeout:{timeout}];
            (
              way["highway"~"primary|secondary|tertiary|residential|trunk"]({bbox});
              node["highway"="traffic_signals"]({bbox});
              node["highway"="stop"]({bbox});
            );
            out body;
            >;
            out skel qt;
            """

            overpass_url = "https://overpass-api.de/api/interpreter"
            data = urllib.parse.urlencode({'data': query}).encode()

            req = urllib.request.Request(overpass_url, data=data,
                                         headers={'User-Agent': 'TrafficSimulator/1.0'})
            with urllib.request.urlopen(req, timeout=30) as response:
                osm_data = json.loads(response.read().decode())

            if 'elements' not in osm_data or len(osm_data['elements']) < 5:
                return False

            # Parse OSM data and create grid
            self._parse_osm_to_grid(osm_data, lat, lon, lat_delta, lon_delta)
            return True

        except Exception as e:
            print(f"Overpass API error: {e}")
            return False

    def _parse_osm_to_grid(self, osm_data: dict, center_lat: float, center_lon: float,
                           lat_delta: float, lon_delta: float):
        """Parse OSM data and populate the simulation grid."""
        self._clear_grid()

        # Build node lookup
        nodes = {}
        ways = []
        signals = []
        stop_signs = []

        for element in osm_data.get('elements', []):
            if element['type'] == 'node':
                nodes[element['id']] = (element['lat'], element['lon'])
                if element.get('tags', {}).get('highway') == 'traffic_signals':
                    signals.append((element['lat'], element['lon']))
                elif element.get('tags', {}).get('highway') == 'stop':
                    stop_signs.append((element['lat'], element['lon']))
            elif element['type'] == 'way':
                ways.append(element)

        if not ways:
            return

        # Calculate bounds for mapping to grid
        min_lat = center_lat - lat_delta
        max_lat = center_lat + lat_delta
        min_lon = center_lon - lon_delta
        max_lon = center_lon + lon_delta

        def latlon_to_grid(lat, lon):
            """Convert lat/lon to grid coordinates."""
            gx = int((lon - min_lon) / (max_lon - min_lon) * self.grid_size)
            gy = int((max_lat - lat) / (max_lat - min_lat) * self.grid_size)
            gx = max(0, min(self.grid_size - 1, gx))
            gy = max(0, min(self.grid_size - 1, gy))
            return gx, gy

        # Draw ways on grid
        for way in ways:
            if 'nodes' not in way:
                continue

            way_nodes = way['nodes']
            prev_gx, prev_gy = None, None

            for node_id in way_nodes:
                if node_id not in nodes:
                    continue

                lat, lon = nodes[node_id]
                gx, gy = latlon_to_grid(lat, lon)

                # Draw line from previous point to current
                if prev_gx is not None:
                    self._draw_road_line(prev_gx, prev_gy, gx, gy)

                prev_gx, prev_gy = gx, gy

        # Add traffic signals
        for lat, lon in signals:
            gx, gy = latlon_to_grid(lat, lon)
            cell = self.grid[gy][gx]
            if cell.road_type != RoadType.NONE:
                cell.road_type = RoadType.INTERSECTION
                cell.signal = TrafficSignal(
                    signal_type=SignalType.TRAFFIC_LIGHT,
                    green_time_ns=self.green_ns_var.get(),
                    green_time_ew=self.green_ew_var.get()
                )

        # Add stop signs
        for lat, lon in stop_signs:
            gx, gy = latlon_to_grid(lat, lon)
            cell = self.grid[gy][gx]
            if cell.road_type != RoadType.NONE and cell.signal is None:
                cell.signal = TrafficSignal(signal_type=SignalType.STOP_SIGN)

        # Find intersections (cells with roads from multiple directions)
        for y in range(self.grid_size):
            for x in range(self.grid_size):
                cell = self.grid[y][x]
                if cell.road_type == RoadType.NONE:
                    continue

                # Check neighbors
                neighbors = 0
                if x > 0 and self.grid[y][x-1].road_type != RoadType.NONE:
                    neighbors += 1
                if x < self.grid_size-1 and self.grid[y][x+1].road_type != RoadType.NONE:
                    neighbors += 1
                if y > 0 and self.grid[y-1][x].road_type != RoadType.NONE:
                    neighbors += 1
                if y < self.grid_size-1 and self.grid[y+1][x].road_type != RoadType.NONE:
                    neighbors += 1

                if neighbors >= 3 and cell.road_type != RoadType.INTERSECTION:
                    cell.road_type = RoadType.INTERSECTION
                    if cell.signal is None:
                        cell.signal = TrafficSignal(
                            signal_type=SignalType.TRAFFIC_LIGHT,
                            green_time_ns=self.green_ns_var.get(),
                            green_time_ew=self.green_ew_var.get()
                        )

        self._draw_grid()

    def _draw_road_line(self, x1: int, y1: int, x2: int, y2: int):
        """Draw a road line on the grid using Bresenham's algorithm."""
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy

        # Determine primary direction
        is_horizontal = dx > dy

        while True:
            if 0 <= x1 < self.grid_size and 0 <= y1 < self.grid_size:
                cell = self.grid[y1][x1]
                if cell.road_type == RoadType.NONE:
                    cell.road_type = RoadType.STRAIGHT_EW if is_horizontal else RoadType.STRAIGHT_NS
                elif ((cell.road_type == RoadType.STRAIGHT_NS and is_horizontal) or
                      (cell.road_type == RoadType.STRAIGHT_EW and not is_horizontal)):
                    cell.road_type = RoadType.INTERSECTION

            if x1 == x2 and y1 == y2:
                break

            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x1 += sx
            if e2 < dx:
                err += dx
                y1 += sy

    def _generate_city_from_coords(self, lat: float, lon: float):
        """Generate city grid based on coordinates (simplified approach)."""
        # Use coordinates to seed random generation for reproducibility
        random.seed(int((lat + lon) * 10000))

        self._clear_grid()

        # Different cities have different grid patterns
        # Use lat/lon to determine style
        if abs(lat) > 40:  # Northern cities tend to have more grid-like patterns
            spacing = 2
        else:
            spacing = random.randint(2, 3)

        # Generate roads
        for y in range(self.grid_size):
            for x in range(self.grid_size):
                is_x_road = x % spacing == 1
                is_y_road = y % spacing == 1

                cell = self.grid[y][x]

                if is_x_road and is_y_road:
                    cell.road_type = RoadType.INTERSECTION
                    cell.signal = TrafficSignal(
                        signal_type=SignalType.TRAFFIC_LIGHT,
                        green_time_ns=self.green_ns_var.get(),
                        green_time_ew=self.green_ew_var.get()
                    )
                elif is_x_road:
                    cell.road_type = RoadType.STRAIGHT_NS
                elif is_y_road:
                    cell.road_type = RoadType.STRAIGHT_EW

        random.seed()  # Reset random seed
        self._draw_grid()

    def _apply_signal_timing(self):
        """Apply current signal timing to all signals."""
        for row in self.grid:
            for cell in row:
                if cell.signal and cell.signal.signal_type == SignalType.TRAFFIC_LIGHT:
                    cell.signal.green_time_ns = self.green_ns_var.get()
                    cell.signal.green_time_ew = self.green_ew_var.get()
                    cell.signal.yellow_time = self.yellow_var.get()
                    cell.signal.all_red_time = self.all_red_var.get()

        self.status_label.config(text="Applied timing to all traffic lights")

    # ========================================================================
    # UI Update Callbacks
    # ========================================================================

    def _update_speed(self, val):
        self.simulation_speed = float(val)
        self.speed_label.config(text=f"{self.simulation_speed:.1f}x")

    def _update_weather(self, event):
        self.weather = WeatherType(self.weather_var.get())

    def _update_time_of_day(self, event):
        self.time_of_day = TimeOfDay(self.time_var.get())

    def _update_distraction_label(self, *args):
        val = self.distraction_var.get()
        if val < 0.25:
            text = "None"
        elif val < 0.5:
            text = "Light"
        elif val < 0.75:
            text = "Moderate"
        else:
            text = "Heavy"
        self.distraction_label.config(text=text)

    def _update_density_label(self, *args):
        self.density_label.config(text=f"{self.density_var.get()*100:.0f}%")

    def _update_truck_label(self, *args):
        self.truck_label.config(text=f"{self.truck_var.get()*100:.0f}%")

    def _update_tourism_label(self, *args):
        self.tourism_label.config(text=f"{self.tourism_var.get():.1f}x")

    def _update_green_ns_label(self, *args):
        self.green_ns_label.config(text=f"{self.green_ns_var.get():.0f}s")

    def _update_green_ew_label(self, *args):
        self.green_ew_label.config(text=f"{self.green_ew_var.get():.0f}s")

    def _update_yellow_label(self, *args):
        self.yellow_label.config(text=f"{self.yellow_var.get():.1f}s")

    def _update_red_label(self, *args):
        self.red_label.config(text=f"{self.red_var.get():.1f}s")


# ============================================================================
# MAP TRACER WINDOW
# ============================================================================

class MapTracerWindow:
    """
    Window for tracing streets over satellite/map imagery.
    Supports OpenStreetMap tiles (free) and optional Google Maps (requires API key).
    """

    def __init__(self, parent, simulator, location: str):
        self.parent = parent
        self.simulator = simulator
        self.location = location

        # Map state
        self.center_lat = 40.7128  # Default NYC
        self.center_lon = -74.0060
        self.zoom = 17  # Street-level zoom
        self.tile_size = 256
        self.map_tiles = {}  # Cache for downloaded tiles
        self.tile_images = {}  # PhotoImage cache

        # Drawing state
        self.drawing_mode = "road"  # road, intersection, signal
        self.traced_roads = []  # List of road segments
        self.current_road = []  # Current road being drawn

        # API settings
        self.google_api_key = ""
        self.use_google = False

        # Create window
        self.window = tk.Toplevel(parent)
        self.window.title(f"Map Tracer - {location}")
        self.window.geometry("1200x800")

        self._setup_ui()
        self._geocode_location(location)

    def _setup_ui(self):
        """Setup the map tracer UI."""
        # Top toolbar
        toolbar = ttk.Frame(self.window)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        # Map source selection
        ttk.Label(toolbar, text="Map Source:").pack(side=tk.LEFT, padx=5)
        self.source_var = tk.StringVar(value="osm")
        ttk.Radiobutton(toolbar, text="OpenStreetMap", variable=self.source_var,
                        value="osm", command=self._refresh_map).pack(side=tk.LEFT)
        ttk.Radiobutton(toolbar, text="Google Satellite", variable=self.source_var,
                        value="google", command=self._check_google_api).pack(side=tk.LEFT)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)

        # Drawing tools
        ttk.Label(toolbar, text="Draw:").pack(side=tk.LEFT, padx=5)
        self.draw_var = tk.StringVar(value="road")
        ttk.Radiobutton(toolbar, text="Road", variable=self.draw_var,
                        value="road").pack(side=tk.LEFT)
        ttk.Radiobutton(toolbar, text="Intersection", variable=self.draw_var,
                        value="intersection").pack(side=tk.LEFT)
        ttk.Radiobutton(toolbar, text="Signal", variable=self.draw_var,
                        value="signal").pack(side=tk.LEFT)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)

        # Zoom controls
        ttk.Button(toolbar, text="Zoom +", command=self._zoom_in).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Zoom -", command=self._zoom_out).pack(side=tk.LEFT, padx=2)
        self.zoom_label = ttk.Label(toolbar, text=f"Zoom: {self.zoom}")
        self.zoom_label.pack(side=tk.LEFT, padx=5)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)

        # Action buttons
        ttk.Button(toolbar, text="Clear Drawing", command=self._clear_drawing).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Undo", command=self._undo_last).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Apply to Grid", command=self._apply_to_grid).pack(side=tk.LEFT, padx=2)

        # Main content area
        content = ttk.Frame(self.window)
        content.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Map canvas
        self.canvas = tk.Canvas(content, bg="#e0e0e0", cursor="crosshair")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Bind events
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Button-3>", self._on_right_click)
        self.canvas.bind("<MouseWheel>", self._on_scroll)
        self.canvas.bind("<Configure>", self._on_resize)

        # Pan with middle mouse or shift+left
        self.canvas.bind("<Button-2>", self._start_pan)
        self.canvas.bind("<B2-Motion>", self._do_pan)
        self.canvas.bind("<Shift-Button-1>", self._start_pan)
        self.canvas.bind("<Shift-B1-Motion>", self._do_pan)

        # Status bar
        status = ttk.Frame(self.window)
        status.pack(fill=tk.X, padx=5, pady=2)

        self.status_label = ttk.Label(status, text="Loading map...")
        self.status_label.pack(side=tk.LEFT)

        self.coords_label = ttk.Label(status, text="")
        self.coords_label.pack(side=tk.RIGHT)

        # Track mouse for coordinates
        self.canvas.bind("<Motion>", self._update_coords)

        # Instructions panel
        instructions = ttk.LabelFrame(self.window, text="Instructions")
        instructions.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(instructions, text=
            "• Left-click and drag to draw roads\n"
            "• Right-click to place intersections/signals\n"
            "• Shift+drag or middle-mouse to pan the map\n"
            "• Mouse wheel to zoom\n"
            "• Click 'Apply to Grid' when done to transfer to simulator",
            justify=tk.LEFT).pack(padx=10, pady=5)

        # Pan state
        self.pan_start = None
        self.is_drawing = False

    def _geocode_location(self, location: str):
        """Geocode the location to get coordinates."""
        self.status_label.config(text=f"Geocoding {location}...")
        self.window.update()

        try:
            encoded_location = urllib.parse.quote(location)
            url = f"https://nominatim.openstreetmap.org/search?q={encoded_location}&format=json&limit=1"

            req = urllib.request.Request(url, headers={'User-Agent': 'TrafficSimulator/1.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())

            if data:
                self.center_lat = float(data[0]['lat'])
                self.center_lon = float(data[0]['lon'])
                self.status_label.config(text=f"Located: {location}")
                self._refresh_map()
            else:
                self.status_label.config(text=f"Location not found: {location}")

        except Exception as e:
            self.status_label.config(text=f"Geocoding error: {e}")

    def _check_google_api(self):
        """Check for Google API key when Google source is selected."""
        if self.source_var.get() == "google" and not self.google_api_key:
            # Prompt for API key
            dialog = tk.Toplevel(self.window)
            dialog.title("Google Maps API Key")
            dialog.geometry("400x150")
            dialog.transient(self.window)

            ttk.Label(dialog, text="Enter your Google Maps API key:").pack(pady=10)
            ttk.Label(dialog, text="(Get one at: console.cloud.google.com)",
                     font=("Arial", 8)).pack()

            key_var = tk.StringVar()
            entry = ttk.Entry(dialog, textvariable=key_var, width=50)
            entry.pack(pady=10)

            def save_key():
                self.google_api_key = key_var.get()
                if self.google_api_key:
                    self.use_google = True
                    dialog.destroy()
                    self._refresh_map()
                else:
                    self.source_var.set("osm")
                    dialog.destroy()

            def cancel():
                self.source_var.set("osm")
                dialog.destroy()

            btn_frame = ttk.Frame(dialog)
            btn_frame.pack(pady=10)
            ttk.Button(btn_frame, text="OK", command=save_key).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_frame, text="Cancel", command=cancel).pack(side=tk.LEFT, padx=5)
        else:
            self._refresh_map()

    def _lat_lon_to_tile(self, lat, lon, zoom):
        """Convert lat/lon to tile coordinates."""
        n = 2 ** zoom
        x = int((lon + 180) / 360 * n)
        lat_rad = math.radians(lat)
        y = int((1 - math.asinh(math.tan(lat_rad)) / math.pi) / 2 * n)
        return x, y

    def _tile_to_lat_lon(self, x, y, zoom):
        """Convert tile coordinates to lat/lon."""
        n = 2 ** zoom
        lon = x / n * 360 - 180
        lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
        lat = math.degrees(lat_rad)
        return lat, lon

    def _refresh_map(self):
        """Refresh the map display."""
        self.canvas.delete("map")

        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        if canvas_width < 10 or canvas_height < 10:
            self.window.after(100, self._refresh_map)
            return

        # Calculate tile range needed
        center_tile_x, center_tile_y = self._lat_lon_to_tile(
            self.center_lat, self.center_lon, self.zoom)

        tiles_x = (canvas_width // self.tile_size) + 2
        tiles_y = (canvas_height // self.tile_size) + 2

        # Calculate pixel offset for smooth scrolling
        n = 2 ** self.zoom
        center_pixel_x = (self.center_lon + 180) / 360 * n * self.tile_size
        center_pixel_y = (1 - math.asinh(math.tan(math.radians(self.center_lat))) / math.pi) / 2 * n * self.tile_size

        # Load and display tiles
        for dy in range(-tiles_y//2, tiles_y//2 + 1):
            for dx in range(-tiles_x//2, tiles_x//2 + 1):
                tile_x = center_tile_x + dx
                tile_y = center_tile_y + dy

                # Calculate position on canvas
                tile_pixel_x = tile_x * self.tile_size
                tile_pixel_y = tile_y * self.tile_size

                canvas_x = canvas_width/2 + (tile_pixel_x - center_pixel_x)
                canvas_y = canvas_height/2 + (tile_pixel_y - center_pixel_y)

                # Try to get tile image
                tile_key = (tile_x, tile_y, self.zoom, self.source_var.get())
                if tile_key not in self.tile_images:
                    self._load_tile(tile_x, tile_y)

                if tile_key in self.tile_images:
                    self.canvas.create_image(canvas_x, canvas_y,
                                            image=self.tile_images[tile_key],
                                            anchor=tk.NW, tags="map")

        # Draw traced roads on top
        self._redraw_traced_roads()
        self.canvas.tag_lower("map")

        self.zoom_label.config(text=f"Zoom: {self.zoom}")

    def _load_tile(self, x, y):
        """Load a map tile."""
        tile_key = (x, y, self.zoom, self.source_var.get())

        try:
            if self.source_var.get() == "osm":
                url = f"https://tile.openstreetmap.org/{self.zoom}/{x}/{y}.png"
            elif self.source_var.get() == "google" and self.google_api_key:
                # Google Static Maps API
                lat, lon = self._tile_to_lat_lon(x + 0.5, y + 0.5, self.zoom)
                url = (f"https://maps.googleapis.com/maps/api/staticmap?"
                      f"center={lat},{lon}&zoom={self.zoom}&size=256x256"
                      f"&maptype=satellite&key={self.google_api_key}")
            else:
                return

            req = urllib.request.Request(url, headers={
                'User-Agent': 'TrafficSimulator/1.0'
            })
            with urllib.request.urlopen(req, timeout=5) as response:
                image_data = response.read()

            # Create PhotoImage from data (requires PIL for PNG, but we'll use a placeholder)
            # For simplicity, we'll create a colored placeholder
            # In production, you'd use PIL/Pillow to load the actual tile

            # Create a simple colored tile as placeholder
            tile_img = tk.PhotoImage(width=256, height=256)
            # Create a simple pattern based on tile coords
            color = f"#{(x*17) % 256:02x}{(y*23) % 256:02x}{((x+y)*7) % 256:02x}"
            tile_img.put(color, to=(0, 0, 256, 256))

            self.tile_images[tile_key] = tile_img

        except Exception as e:
            # Create error tile
            pass

    def _redraw_traced_roads(self):
        """Redraw all traced roads."""
        self.canvas.delete("traced")

        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        for road in self.traced_roads:
            if len(road['points']) >= 2:
                # Convert lat/lon points to canvas coordinates
                canvas_points = []
                for lat, lon in road['points']:
                    cx, cy = self._latlon_to_canvas(lat, lon)
                    canvas_points.extend([cx, cy])

                color = "#e74c3c" if road['type'] == 'road' else "#f1c40f"
                self.canvas.create_line(canvas_points, fill=color, width=4,
                                        tags="traced", capstyle=tk.ROUND)

        # Draw intersections
        for road in self.traced_roads:
            if road['type'] == 'intersection':
                lat, lon = road['points'][0]
                cx, cy = self._latlon_to_canvas(lat, lon)
                self.canvas.create_oval(cx-8, cy-8, cx+8, cy+8,
                                       fill="#2ecc71", outline="white", width=2,
                                       tags="traced")

        # Draw current road being drawn
        if self.current_road and len(self.current_road) >= 2:
            canvas_points = []
            for lat, lon in self.current_road:
                cx, cy = self._latlon_to_canvas(lat, lon)
                canvas_points.extend([cx, cy])
            self.canvas.create_line(canvas_points, fill="#3498db", width=4,
                                   tags="traced", dash=(5, 5))

    def _latlon_to_canvas(self, lat, lon):
        """Convert lat/lon to canvas coordinates."""
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        n = 2 ** self.zoom

        # Center in pixels
        center_pixel_x = (self.center_lon + 180) / 360 * n * self.tile_size
        center_pixel_y = (1 - math.asinh(math.tan(math.radians(self.center_lat))) / math.pi) / 2 * n * self.tile_size

        # Point in pixels
        point_pixel_x = (lon + 180) / 360 * n * self.tile_size
        point_pixel_y = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n * self.tile_size

        canvas_x = canvas_width/2 + (point_pixel_x - center_pixel_x)
        canvas_y = canvas_height/2 + (point_pixel_y - center_pixel_y)

        return canvas_x, canvas_y

    def _canvas_to_latlon(self, cx, cy):
        """Convert canvas coordinates to lat/lon."""
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        n = 2 ** self.zoom

        # Center in pixels
        center_pixel_x = (self.center_lon + 180) / 360 * n * self.tile_size
        center_pixel_y = (1 - math.asinh(math.tan(math.radians(self.center_lat))) / math.pi) / 2 * n * self.tile_size

        # Point in pixels
        point_pixel_x = center_pixel_x + (cx - canvas_width/2)
        point_pixel_y = center_pixel_y + (cy - canvas_height/2)

        # Convert to lat/lon
        lon = point_pixel_x / (n * self.tile_size) * 360 - 180
        lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * point_pixel_y / (n * self.tile_size)))))

        return lat, lon

    def _on_click(self, event):
        """Handle click to start drawing."""
        if event.state & 0x1:  # Shift key held - pan mode
            return

        self.is_drawing = True
        lat, lon = self._canvas_to_latlon(event.x, event.y)
        self.current_road = [(lat, lon)]

    def _on_drag(self, event):
        """Handle drag to continue drawing."""
        if not self.is_drawing:
            return

        lat, lon = self._canvas_to_latlon(event.x, event.y)
        self.current_road.append((lat, lon))
        self._redraw_traced_roads()

    def _on_release(self, event):
        """Handle release to finish drawing."""
        if not self.is_drawing:
            return

        self.is_drawing = False
        if len(self.current_road) >= 2:
            self.traced_roads.append({
                'type': self.draw_var.get(),
                'points': self.current_road.copy()
            })
        self.current_road = []
        self._redraw_traced_roads()

    def _on_right_click(self, event):
        """Handle right-click to place intersection/signal."""
        lat, lon = self._canvas_to_latlon(event.x, event.y)
        self.traced_roads.append({
            'type': 'intersection',
            'points': [(lat, lon)]
        })
        self._redraw_traced_roads()

    def _start_pan(self, event):
        """Start panning the map."""
        self.pan_start = (event.x, event.y)

    def _do_pan(self, event):
        """Pan the map."""
        if self.pan_start:
            dx = event.x - self.pan_start[0]
            dy = event.y - self.pan_start[1]

            # Convert pixel movement to lat/lon change
            n = 2 ** self.zoom
            lon_per_pixel = 360 / (n * self.tile_size)
            lat_per_pixel = 180 / (n * self.tile_size)  # Approximate

            self.center_lon -= dx * lon_per_pixel
            self.center_lat += dy * lat_per_pixel

            self.pan_start = (event.x, event.y)
            self._refresh_map()

    def _on_scroll(self, event):
        """Handle scroll to zoom."""
        if event.delta > 0:
            self._zoom_in()
        else:
            self._zoom_out()

    def _zoom_in(self):
        """Zoom in."""
        if self.zoom < 19:
            self.zoom += 1
            self._refresh_map()

    def _zoom_out(self):
        """Zoom out."""
        if self.zoom > 10:
            self.zoom -= 1
            self._refresh_map()

    def _on_resize(self, event):
        """Handle window resize."""
        self._refresh_map()

    def _update_coords(self, event):
        """Update coordinate display."""
        lat, lon = self._canvas_to_latlon(event.x, event.y)
        self.coords_label.config(text=f"Lat: {lat:.6f}, Lon: {lon:.6f}")

    def _clear_drawing(self):
        """Clear all traced roads."""
        self.traced_roads = []
        self.current_road = []
        self._redraw_traced_roads()

    def _undo_last(self):
        """Undo last traced element."""
        if self.traced_roads:
            self.traced_roads.pop()
            self._redraw_traced_roads()

    def _apply_to_grid(self):
        """Apply traced roads to the simulator grid."""
        if not self.traced_roads:
            messagebox.showwarning("No Roads", "Please trace some roads first.")
            return

        # Find bounding box of traced roads
        all_lats = []
        all_lons = []
        for road in self.traced_roads:
            for lat, lon in road['points']:
                all_lats.append(lat)
                all_lons.append(lon)

        if not all_lats:
            return

        min_lat, max_lat = min(all_lats), max(all_lats)
        min_lon, max_lon = min(all_lons), max(all_lons)

        # Map to grid
        grid_size = self.simulator.grid_size
        self.simulator._clear_grid()

        for road in self.traced_roads:
            if road['type'] == 'intersection':
                # Place intersection
                lat, lon = road['points'][0]
                gx = int((lon - min_lon) / (max_lon - min_lon + 0.0001) * (grid_size - 1))
                gy = int((max_lat - lat) / (max_lat - min_lat + 0.0001) * (grid_size - 1))

                gx = max(0, min(grid_size-1, gx))
                gy = max(0, min(grid_size-1, gy))

                cell = self.simulator.grid[gy][gx]
                cell.road_type = RoadType.INTERSECTION
                cell.signal = TrafficSignal(signal_type=SignalType.TRAFFIC_LIGHT)

            elif road['type'] == 'road':
                # Trace road through grid
                for i in range(len(road['points']) - 1):
                    lat1, lon1 = road['points'][i]
                    lat2, lon2 = road['points'][i + 1]

                    gx1 = int((lon1 - min_lon) / (max_lon - min_lon + 0.0001) * (grid_size - 1))
                    gy1 = int((max_lat - lat1) / (max_lat - min_lat + 0.0001) * (grid_size - 1))
                    gx2 = int((lon2 - min_lon) / (max_lon - min_lon + 0.0001) * (grid_size - 1))
                    gy2 = int((max_lat - lat2) / (max_lat - min_lat + 0.0001) * (grid_size - 1))

                    # Draw line using Bresenham's algorithm
                    self._draw_line_on_grid(gx1, gy1, gx2, gy2)

        self.simulator._draw_grid()
        messagebox.showinfo("Applied", "Road layout applied to simulator grid.")
        self.window.destroy()

    def _draw_line_on_grid(self, x1, y1, x2, y2):
        """Draw a line on the grid using Bresenham's algorithm."""
        grid_size = self.simulator.grid_size

        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy

        # Determine road type based on direction
        if dx > dy:
            road_type = RoadType.STRAIGHT_EW
        else:
            road_type = RoadType.STRAIGHT_NS

        while True:
            if 0 <= x1 < grid_size and 0 <= y1 < grid_size:
                cell = self.simulator.grid[y1][x1]
                if cell.road_type == RoadType.NONE:
                    cell.road_type = road_type
                elif cell.road_type != road_type and cell.road_type != RoadType.INTERSECTION:
                    # Roads crossing = intersection
                    cell.road_type = RoadType.INTERSECTION
                    cell.signal = TrafficSignal(signal_type=SignalType.TRAFFIC_LIGHT)

            if x1 == x2 and y1 == y2:
                break

            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x1 += sx
            if e2 < dx:
                err += dx
                y1 += sy


# ============================================================================
# MAIN
# ============================================================================

def main():
    root = tk.Tk()
    app = TrafficSimulator(root)
    root.mainloop()


if __name__ == "__main__":
    main()
