"""
Compute quality metrics for a batch of replayed plans (see run_batch.py) and
summarize/compare them.

Usage: python analyze_plans.py <output_dir>

Quality criteria (per user request):
  - how many people drive more than 4 / 5 / 6 times
  - how many times people drive in total
  - how "tight" parties are: fewer, fuller parties beat many half-full ones
    for the same group of people, even at equal total driving times
"""
import json
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean, pstdev


def _cluster_key(members_by_initials, driver, time_):
    """Bucket a party's time into 30-min-tolerance clusters per (day, direction) for pool-level tightness."""
    return round(time_ / 100 * 2) / 2  # coarse half-hour bucket, good enough for grouping


def analyze_plan(plan: dict) -> dict:
    drive_days = defaultdict(set)  # initials -> set of unique day numbers driven
    parties_flat = []  # (day, direction, driver, seats_used, capacity)

    seats_by_initials = {}

    for day_key, day_plan in plan['dayPlans'].items():
        day_num = int(day_key)
        for party in day_plan['parties']:
            driver = party['driver']
            drive_days[driver].add(day_num)
            occupancy = 1 + len(party['passengers'])
            direction = 'schoolbound' if party['schoolbound'] else 'homebound'
            parties_flat.append({
                'day': day_num,
                'direction': direction,
                'driver': driver,
                'time': party['time'],
                'occupancy': occupancy,
            })

    drive_counts = {initials: len(days) for initials, days in drive_days.items()}
    total_drives = sum(drive_counts.values())
    num_gt4 = sum(1 for c in drive_counts.values() if c > 4)
    num_gt5 = sum(1 for c in drive_counts.values() if c > 5)
    num_gt6 = sum(1 for c in drive_counts.values() if c > 6)

    # Pool-level tightness: group same (day, direction, rough time bucket) parties
    # together and see how many distinct cars were used to move that group, and
    # how full those cars ended up (as a fraction of the *group's* head count).
    pools = defaultdict(list)
    for p in parties_flat:
        bucket = round(p['time'] / 100 * 2) / 2
        pools[(p['day'], p['direction'], bucket)].append(p)

    pool_car_counts = [len(members) for members in pools.values()]
    total_people_moved = sum(p['occupancy'] for p in parties_flat)
    occupancies = [p['occupancy'] for p in parties_flat]

    return {
        'driveCounts': drive_counts,
        'totalDrives': total_drives,
        'numDrivingMoreThan4': num_gt4,
        'numDrivingMoreThan5': num_gt5,
        'numDrivingMoreThan6': num_gt6,
        'maxDrives': max(drive_counts.values()) if drive_counts else 0,
        'totalParties': len(parties_flat),
        'totalPools': len(pools),
        'avgCarsPerPool': mean(pool_car_counts) if pool_car_counts else 0,
        'avgOccupancy': mean(occupancies) if occupancies else 0,
        'totalPeopleMoved': total_people_moved,
    }


def main():
    if len(sys.argv) != 2:
        print("Usage: python analyze_plans.py <output_dir>")
        sys.exit(1)

    output_dir = Path(sys.argv[1])
    plan_files = sorted(output_dir.glob('plan-*.json'))

    if not plan_files:
        print(f"No plan-*.json files found in {output_dir}")
        sys.exit(1)

    results = []
    for plan_file in plan_files:
        with open(plan_file) as f:
            plan = json.load(f)
        metrics = analyze_plan(plan)
        metrics['file'] = plan_file.name
        results.append(metrics)

    print(f"Analyzed {len(results)} plans from {output_dir}\n")

    # Per-run table
    print(f"{'run':<16} {'totalDrives':>11} {'>4':>4} {'>5':>4} {'>6':>4} {'maxDrv':>7} {'parties':>8} {'pools':>6} {'carsPerPool':>12} {'avgOcc':>7}")
    for m in results:
        print(f"{m['file']:<16} {m['totalDrives']:>11} {m['numDrivingMoreThan4']:>4} {m['numDrivingMoreThan5']:>4} "
              f"{m['numDrivingMoreThan6']:>4} {m['maxDrives']:>7} {m['totalParties']:>8} {m['totalPools']:>6} "
              f"{m['avgCarsPerPool']:>12.2f} {m['avgOccupancy']:>7.2f}")

    def col(name):
        return [m[name] for m in results]

    print("\n=== Summary across runs ===")
    for name, label in [
        ('totalDrives', 'Total drives'),
        ('numDrivingMoreThan4', '# driving >4x'),
        ('numDrivingMoreThan5', '# driving >5x'),
        ('numDrivingMoreThan6', '# driving >6x'),
        ('maxDrives', 'Max drives (any one person)'),
        ('totalParties', 'Total parties'),
        ('totalPools', 'Total pools'),
        ('avgCarsPerPool', 'Avg cars/pool (lower = tighter)'),
        ('avgOccupancy', 'Avg occupancy per party'),
    ]:
        values = col(name)
        print(f"{label:<32} min={min(values):>7.2f}  max={max(values):>7.2f}  "
              f"mean={mean(values):>7.2f}  stdev={pstdev(values):>6.2f}")

    # Identify best/worst runs by a simple composite: fewer high-frequency
    # drivers, then fewer total drives, then tighter pooling.
    def score(m):
        return (m['numDrivingMoreThan6'], m['numDrivingMoreThan5'], m['numDrivingMoreThan4'],
                m['totalDrives'], m['avgCarsPerPool'], -m['avgOccupancy'])

    best = min(results, key=score)
    worst = max(results, key=score)
    print(f"\nBest run:  {best['file']}  ({best})")
    print(f"Worst run: {worst['file']}  ({worst})")

    identical = len({json.dumps(m['driveCounts'], sort_keys=True) for m in results}) == 1
    print(f"\nAll runs produced identical per-member drive counts: {identical}")


if __name__ == '__main__':
    main()
