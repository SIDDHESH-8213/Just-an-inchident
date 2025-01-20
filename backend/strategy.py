from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import itertools
import heapq


# Function to calculate lap time based on degradation
def calculate_lap_time(baseline_lap_time, degradation_rate, laps_since_last_pit):
    return baseline_lap_time + (degradation_rate * laps_since_last_pit)


# Function to optimize strategy and calculate the best options
def optimize_strategy(total_laps, tire_data, pit_stop_time):
    all_strategies = {}
    tire_compounds = ["S", "M", "H"]

    for num_stops in range(1, 3):  # 1 or 2 stops
        for progression in itertools.product(tire_compounds, repeat=num_stops + 1):
            progression = list(progression)
            possible_pit_stop_laps = []

            if num_stops == 1:  # One-stop strategies
                possible_pit_stop_laps = [[lap] for lap in range(1, min(tire_data[progression[0]]["life"], total_laps))]
            elif num_stops == 2:  # Two-stop strategies
                max_lap1 = min(tire_data[progression[0]]["life"], total_laps - 1)
                for lap1 in range(1, max_lap1):
                    max_lap2 = min(lap1 + tire_data[progression[1]]["life"], total_laps)
                    for lap2 in range(lap1 + 1, max_lap2):
                        possible_pit_stop_laps.append([lap1, lap2])

            for pit_stop_laps in possible_pit_stop_laps:
                current_race_time = 0
                current_tire = progression[0]
                laps_since_last_pit = 0
                valid_strategy = True
                current_lap = 1
                pit_stop_index = 0

                while current_lap <= total_laps:
                    laps_since_last_pit += 1
                    current_lap_time = calculate_lap_time(
                        tire_data[current_tire]["baseline"],
                        tire_data[current_tire]["degradation"],
                        laps_since_last_pit
                    )
                    current_race_time += current_lap_time

                    if laps_since_last_pit > tire_data[current_tire]["life"]:
                        valid_strategy = False
                        break

                    if pit_stop_index < len(pit_stop_laps) and current_lap == pit_stop_laps[pit_stop_index]:
                        current_race_time += pit_stop_time
                        current_tire = progression[pit_stop_index + 1]
                        laps_since_last_pit = 0
                        pit_stop_index += 1

                    current_lap += 1

                if valid_strategy:
                    strategy_key = f"{'-'.join(progression)} - {pit_stop_laps}"
                    all_strategies[strategy_key] = current_race_time

    # Separate strategies into one-stop and two-stop groups
    one_stop_strategies = {}
    two_stop_strategies = {}

    for strategy, time in all_strategies.items():
        if len(strategy.split(" - ")[0].split("-")) == 2:  # One-stop strategy
            one_stop_strategies[strategy] = time
        elif len(strategy.split(" - ")[0].split("-")) == 3:  # Two-stop strategy
            two_stop_strategies[strategy] = time

    # Get top 3 strategies for each
    top_one_stop = heapq.nsmallest(3, one_stop_strategies.items(), key=lambda item: item[1]) if one_stop_strategies else []
    top_two_stop = heapq.nsmallest(3, two_stop_strategies.items(), key=lambda item: item[1]) if two_stop_strategies else []

    return top_one_stop, top_two_stop


# Django API endpoint
@csrf_exempt
def optimize_strategy_view(request):
    if request.method == 'POST':
        try:
            # Parse JSON input
            data = json.loads(request.body)
            total_laps = int(data['total_laps'])
            pit_stop_time = int(data['pit_stop_time'])

            # Tire data input
            tire_data = {
                "S": {
                    "baseline": float(data['s_fastest_lap']),
                    "degradation": float(data['s_degradation']),
                    "life": int(data['s_life'])
                },
                "M": {
                    "baseline": float(data['m_fastest_lap']),
                    "degradation": float(data['m_degradation']),
                    "life": int(data['m_life'])
                },
                "H": {
                    "baseline": float(data['h_fastest_lap']),
                    "degradation": float(data['h_degradation']),
                    "life": int(data['h_life'])
                }
            }

            # Calculate top strategies
            top_one_stop, top_two_stop = optimize_strategy(total_laps, tire_data, pit_stop_time)

            # Format the strategies into a JSON response
            def format_strategies(strategies):
                formatted = []
                for strategy, time in strategies:
                    tire_progression, pit_stops_str = strategy.split(" - ")
                    pit_stops = eval(pit_stops_str)
                    formatted.append({
                        "time": time,
                        "tires": tire_progression.split("-"),
                        "pit_stops": pit_stops
                    })
                return formatted

            response = {
                "one_stop_strategies": format_strategies(top_one_stop),
                "two_stop_strategies": format_strategies(top_two_stop)
            }
            return JsonResponse(response)

        except (KeyError, ValueError, TypeError) as e:
            return JsonResponse({"error": f"Invalid input: {str(e)}"}, status=400)
        except Exception as e:
            return JsonResponse({"error": f"An unexpected error occurred: {str(e)}"}, status=500)
    else:
        return JsonResponse({"error": "Only POST requests are allowed"}, status=405)
