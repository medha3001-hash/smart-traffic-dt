# ============================================================
# SIGNAL OPTIMIZATION LOGIC
#
# This file contains the core signal optimization algorithm.
# It combines:
# 1. ML congestion prediction (from Random Forest model)
# 2. Dynamic cycle time (based on total vehicle count)
# 3. Proportional green time (based on each junction's share)
# ============================================================

def get_dynamic_cycle_time(total_vehicles):
    """
    Decides total cycle time based on how many vehicles
    are at all junctions combined.

    Think of it like a meeting room booking:
    - More people → need more time
    - Fewer people → shorter meeting needed

    Returns cycle time in seconds and a label.
    """
    if total_vehicles > 300:
        return 160, "EXTENDED"    # Very heavy traffic
    elif total_vehicles > 200:
        return 120, "NORMAL"      # Moderate traffic
    elif total_vehicles > 100:
        return 100, "MODERATE"    # Light-moderate
    else:
        return 80, "REDUCED"      # Light traffic

def optimize_signals(vehicle_counts, congestion_proba):
    """
    Main optimization function.

    INPUTS:
    - vehicle_counts: list of [j1, j2, j3, j4] vehicle counts
    - congestion_proba: ML model's congestion probability (0 to 1)

    HOW IT WORKS:
    Step 1: Calculate total vehicles across all junctions
    Step 2: Use total to set dynamic cycle time
    Step 3: Give each junction green time proportional to its traffic
    Step 4: Apply ML adjustment — if ML says high congestion,
            add 10% extra to the busiest junction

    RETURNS:
    Dictionary with green times and explanation
    """

    j1, j2, j3, j4 = vehicle_counts
    total_vehicles  = sum(vehicle_counts)

    # ---- Step 1: Dynamic cycle time ----
    # More total traffic = longer total cycle
    cycle_time, cycle_label = get_dynamic_cycle_time(total_vehicles)

    # ---- Step 2: Proportional green time ----
    # Each junction gets green time proportional to its vehicle count
    # Formula: green_time = (my_vehicles / total_vehicles) * cycle_time
    # Example: If J1 has 150 out of 300 total → gets 50% of cycle time
    MIN_GREEN = 10   # Minimum 10 seconds (safety requirement)
    MAX_GREEN = 60   # Maximum 60 seconds

    if total_vehicles == 0:
        # Edge case — no vehicles anywhere
        green_times = [cycle_time // 4] * 4
    else:
        green_times = []
        for count in vehicle_counts:
            proportion = count / total_vehicles
            raw_green  = proportion * cycle_time
            # Keep within safe bounds
            green = max(MIN_GREEN, min(MAX_GREEN, round(raw_green)))
            green_times.append(green)

    # ---- Step 3: ML adjustment ----
    # If ML model is highly confident about congestion (>70%),
    # give the busiest junction 10% extra green time
    ml_adjustment_applied = False
    if congestion_proba > 0.7:
        busiest_idx = vehicle_counts.index(max(vehicle_counts))
        bonus = round(green_times[busiest_idx] * 0.10)
        green_times[busiest_idx] = min(MAX_GREEN,
                                       green_times[busiest_idx] + bonus)
        ml_adjustment_applied = True

    # ---- Step 4: Congestion level per junction ----
    def get_level(count):
        if count > 80:    return 'HIGH'
        elif count >= 40: return 'MEDIUM'
        else:             return 'LOW'

    levels = [get_level(c) for c in vehicle_counts]

    # ---- Build explanation ----
    # This is shown in the dashboard so users understand decisions
    explanation = []
    explanation.append(
        f"Total vehicles: {total_vehicles} → "
        f"cycle time set to **{cycle_time}s** [{cycle_label}]"
    )
    for i, (count, gt) in enumerate(zip(vehicle_counts, green_times)):
        if total_vehicles > 0:
            pct = round(count / total_vehicles * 100)
        else:
            pct = 25
        explanation.append(
            f"Junction {i+1}: {count} vehicles "
            f"({pct}% of total) → **{gt}s** green"
        )
    if ml_adjustment_applied:
        explanation.append(
            "🤖 ML detected high congestion probability — "
            "bonus green time given to busiest junction"
        )

    return {
        'green_times':          green_times,
        'levels':               levels,
        'cycle_time':           cycle_time,
        'cycle_label':          cycle_label,
        'total_vehicles':       total_vehicles,
        'ml_adjustment':        ml_adjustment_applied,
        'explanation':          explanation
    }