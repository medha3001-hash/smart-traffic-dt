import random

# ============================================================
# TRAFFIC FLOW MODULE
#
# This file handles two new realistic features:
# 1. Connected junctions — vehicles flow from one to another
# 2. Direction-based traffic — N, S, E, W per junction
#
# WHY THIS IS IMPORTANT:
# In real life, junctions are not independent. If J1 is congested,
# vehicles spill over to J2. This is called "spillback" in traffic
# engineering. This module simulates that behavior simply.
# ============================================================

# ---- Junction connection map ----
# This defines which junction feeds into which.
# Think of it like a road network:
# J1 (ITO) → feeds into J2 (Connaught Place) — 30% of vehicles move
# J2 (CP)  → feeds into J3 (Lajpat Nagar)   — 20% of vehicles move
# J3 (LN)  → feeds into J4 (NH-48)           — 25% of vehicles move
# J4 (NH)  → feeds back into J1 (ITO)        — 15% (circular flow)

JUNCTION_CONNECTIONS = {
    'junction_1': {'feeds_into': 'junction_2', 'flow_rate': 0.30},
    'junction_2': {'feeds_into': 'junction_3', 'flow_rate': 0.20},
    'junction_3': {'feeds_into': 'junction_4', 'flow_rate': 0.25},
    'junction_4': {'feeds_into': 'junction_1', 'flow_rate': 0.15},
}

# ---- Direction split percentages ----
# At each junction, traffic comes from 4 directions.
# These percentages define how traffic is distributed.
# Based on real Delhi road geometry:
# ITO        → heavy North-South (main road axis)
# CP         → equal all sides (circular road)
# Lajpat Nagar → heavy East-West (market road)
# NH-48      → heavy North-South (highway direction)

DIRECTION_SPLITS = {
    'junction_1': {'N': 0.35, 'S': 0.35, 'E': 0.15, 'W': 0.15},
    'junction_2': {'N': 0.25, 'S': 0.25, 'E': 0.25, 'W': 0.25},
    'junction_3': {'N': 0.20, 'S': 0.20, 'E': 0.30, 'W': 0.30},
    'junction_4': {'N': 0.40, 'S': 0.40, 'E': 0.10, 'W': 0.10},
}

def apply_junction_flow(vehicle_counts):
    """
    Simulates traffic flowing between connected junctions.

    HOW IT WORKS:
    - Takes current vehicle counts at all 4 junctions
    - For each junction, a percentage of its vehicles
      "move" to the next junction
    - This increases the downstream junction's count
    - Simulates real-world spillback effect

    EXAMPLE:
    - J1 has 100 vehicles
    - 30% flow rate → 30 vehicles move to J2
    - J2's count increases by 30
    - J1's count decreases by 30

    INPUT:  dict with junction counts
    OUTPUT: dict with updated counts after flow
    """
    # Make a copy so we don't change the original
    updated = dict(vehicle_counts)

    for junction_key, connection in JUNCTION_CONNECTIONS.items():
        downstream = connection['feeds_into']
        flow_rate  = connection['flow_rate']

        # How many vehicles move to next junction?
        vehicles_moving = int(updated[junction_key] * flow_rate)

        # Remove from current junction, add to next
        updated[junction_key] -= vehicles_moving
        updated[downstream]   += vehicles_moving

        # Make sure counts don't go negative or exceed max
        updated[junction_key] = max(0, updated[junction_key])
        updated[downstream]   = min(180, updated[downstream])

    return updated

def split_by_direction(junction_key, total_vehicles):
    """
    Splits total vehicle count into N, S, E, W directions.

    HOW IT WORKS:
    - Takes the total vehicle count at a junction
    - Splits it according to that junction's direction percentages
    - Adds small random variation (+/- 5%) to feel realistic

    EXAMPLE:
    - J1 total = 100 vehicles
    - N split = 35% → 35 vehicles from North
    - S split = 35% → 35 vehicles from South
    - E split = 15% → 15 vehicles from East
    - W split = 15% → 15 vehicles from West

    INPUT:  junction key + total vehicles
    OUTPUT: dict with N, S, E, W counts
    """
    splits = DIRECTION_SPLITS[junction_key]
    directions = {}

    for direction, percentage in splits.items():
        # Base count for this direction
        base = total_vehicles * percentage
        # Add small random variation (+/- 5%)
        variation = random.uniform(0.95, 1.05)
        count = max(1, int(base * variation))
        directions[direction] = count

    return directions

def optimize_signals_by_direction(direction_counts, total_cycle_time):
    """
    Allocates green time PER DIRECTION based on vehicle load.

    HOW IT WORKS:
    - Instead of giving equal time to all directions,
      the direction with more vehicles gets more green time
    - This is proportional allocation per direction

    EXAMPLE:
    - N=40, S=30, E=20, W=10 (total=100)
    - Total cycle = 120s
    - N gets: (40/100) × 120 = 48s green
    - S gets: (30/100) × 120 = 36s green
    - E gets: (20/100) × 120 = 24s green
    - W gets: (10/100) × 120 = 12s green

    WHY THIS IS REALISTIC:
    Real traffic signals use "Webster's formula" which
    also gives more time to busier directions. This is
    a simplified version of that approach.

    INPUT:  dict of direction counts + total cycle time
    OUTPUT: dict of direction green times
    """
    total_vehicles = sum(direction_counts.values())
    MIN_GREEN = 8    # Minimum 8 seconds per direction
    MAX_GREEN = 60   # Maximum 60 seconds per direction

    green_times = {}

    if total_vehicles == 0:
        # Edge case — no vehicles, split equally
        for direction in direction_counts:
            green_times[direction] = total_cycle_time // 4
    else:
        for direction, count in direction_counts.items():
            proportion  = count / total_vehicles
            raw_green   = proportion * total_cycle_time
            green = max(MIN_GREEN, min(MAX_GREEN, round(raw_green)))
            green_times[direction] = green

    return green_times

def get_current_green_direction(green_times):
    """
    Returns which direction currently has the green light.
    Simply returns the direction with the most green time
    (the busiest one gets priority).
    """
    return max(green_times, key=green_times.get)

def get_flow_explanation(original_counts, updated_counts):
    """
    Generates a human-readable explanation of the traffic flow.
    This is shown in the dashboard so users understand
    how junctions affected each other.
    """
    junction_names = {
        'junction_1': 'ITO',
        'junction_2': 'Connaught Place',
        'junction_3': 'Lajpat Nagar',
        'junction_4': 'NH-48'
    }

    explanations = []
    for key in original_counts:
        orig = original_counts[key]
        upd  = updated_counts[key]
        diff = upd - orig
        name = junction_names[key]

        if diff > 0:
            explanations.append(
                f"**{name}** received +{diff} vehicles "
                f"from upstream junction ({orig} → {upd})"
            )
        elif diff < 0:
            explanations.append(
                f"**{name}** sent {abs(diff)} vehicles "
                f"downstream ({orig} → {upd})"
            )

    return explanations