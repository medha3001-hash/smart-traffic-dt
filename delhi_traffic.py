import random

# ============================================================
# DELHI JUNCTION DEFINITIONS
#
# Each junction has a name, type, and traffic multipliers.
# Multiplier > 1 means busier than average.
# This simulates real Delhi traffic behavior.
# ============================================================

JUNCTIONS = {
    'junction_1': {
        'name': 'ITO',
        'type': 'commercial',
        'description': 'Major intersection — high morning & evening rush',
        'morning_multiplier': 2.5,   # Very busy 8-10am
        'evening_multiplier': 2.8,   # Even busier 5-8pm
        'base_vehicles': 60
    },
    'junction_2': {
        'name': 'Connaught Place',
        'type': 'commercial',
        'description': 'Central business district — busy throughout day',
        'morning_multiplier': 2.0,
        'evening_multiplier': 2.2,
        'base_vehicles': 50
    },
    'junction_3': {
        'name': 'Lajpat Nagar',
        'type': 'residential',
        'description': 'Residential area — moderate peaks',
        'morning_multiplier': 1.8,   # People leaving for work
        'evening_multiplier': 1.9,   # People returning home
        'base_vehicles': 35
    },
    'junction_4': {
        'name': 'NH-48',
        'type': 'highway',
        'description': 'National highway — consistent heavy flow',
        'morning_multiplier': 1.5,   # Steady highway traffic
        'evening_multiplier': 1.6,
        'base_vehicles': 45
    }
}

def get_traffic_label(hour):
    """
    Returns a label based on time of day.
    This tells us what kind of traffic period we are in.
    """
    if 8 <= hour <= 10:
        return "🌅 Morning Rush Hour"
    elif 17 <= hour <= 20:
        return "🌆 Evening Peak Hour"
    elif 12 <= hour <= 14:
        return "🍱 Lunch Hour"
    elif 0 <= hour <= 5:
        return "🌙 Late Night — Very Low Traffic"
    else:
        return "🙂 Normal Traffic Hours"

def generate_traffic(hour, day_of_week):
    """
    Generates realistic vehicle counts for all 4 Delhi junctions
    based on time of day and day of week.

    How it works:
    - Each junction has a base vehicle count
    - During rush hours, a multiplier increases the count
    - Random variation (+/- 10%) makes it feel realistic
    - Weekends have lower traffic overall
    """
    is_weekend = day_of_week >= 5
    weekend_factor = 0.65 if is_weekend else 1.0

    results = {}

    for key, junction in JUNCTIONS.items():
        base = junction['base_vehicles']

        # Choose multiplier based on time of day
        if 8 <= hour <= 10:
            multiplier = junction['morning_multiplier']
        elif 17 <= hour <= 20:
            multiplier = junction['evening_multiplier']
        elif 12 <= hour <= 14:
            multiplier = 1.4   # Lunch hour moderate increase
        elif 0 <= hour <= 5:
            multiplier = 0.15  # Very late night
        elif 6 <= hour <= 7:
            multiplier = 0.8   # Early morning
        else:
            multiplier = 1.0   # Normal daytime

        # Calculate vehicle count with random variation
        raw_count = base * multiplier * weekend_factor
        variation = random.uniform(0.90, 1.10)  # +/- 10%
        final_count = max(1, int(raw_count * variation))

        # Cap at realistic maximum
        final_count = min(final_count, 180)

        results[key] = {
            'count': final_count,
            'name': junction['name'],
            'type': junction['type'],
            'description': junction['description']
        }

    return results

def get_junction_info():
    """Returns junction info for display in dashboard"""
    return JUNCTIONS