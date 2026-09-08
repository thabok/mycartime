"""
Regression test for the CP-SAT plan engine's determinism.

Two things could make the solver's output vary run to run, and this test
guards both:

1. Python-side model building. CP-SAT itself doesn't care about
   PYTHONHASHSEED, but the code that *builds* the model does - a prior
   greedy-heuristic engine (see doc/ALGORITHM_EVOLUTION.md; retired) had
   three separate places where iterating a `set` of member initials silently
   changed real decisions. So the solver builds its model from sorted lists
   only, and this test replays a real capture under different hash seeds to
   prove it stays that way.

2. The solve itself. CP-SAT is deterministic for a fixed model, a fixed
   version, `num_search_workers = 1` and a fixed `random_seed` - as long as the
   search isn't cut short. A solve that stops early (the Stop button, the
   no-improvement stall timeout, or the wall-clock safety net) returns
   whatever the incumbent happened to be at that instant, which does depend
   on machine speed and load.

   This test cuts the search short on purpose, so what it relies on is weaker
   than "the search runs to completion": improving solutions get sparse long
   before SOLVE_BUDGET_SECONDS expires, so every run is still sitting on the
   same incumbent when the budget cuts it off, even though the cutoff lands on a
   slightly different search node each time. That makes the plan comparison
   meaningful without a multi-minute test, but it is a property of the search
   flattening out - not a guarantee.

   Practical consequence: point 1 is what this test really pins down. If it ever
   starts reporting a difference, first raise SOLVE_BUDGET_SECONDS and re-run
   before concluding that model building regressed - a genuine model-building bug
   will differ at *any* budget, whereas an incumbent that hadn't yet settled will
   stop differing once the budget grows.

Usage: python test_determinism_solver.py
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
REPLAY_SCRIPT = REPO_ROOT / 'backend' / 'src' / 'experiments' / 'replay_capture.py'
CAPTURES_DIR = REPO_ROOT / 'backend' / 'src' / 'captures'

# Deliberately far shorter than the search needs: on the largest of these
# captures the optimum is *found* around 20s in and proven around 40s, so this
# budget stops the solve while it is still grinding, on an incumbent that has
# been stable for a while (see point 2 above). Sizing the budget to actually
# reach the optimum would put the suite past 40 minutes for 18 captures x 3
# seeds, which is too slow to run routinely.
#
# This value was picked back when the objective had no week A/B similarity tier
# and the optimum turned up within ~3s, i.e. when the budget really did outlast
# the search. That tier enlarged the search considerably, so read the number as
# "long enough for the incumbent to settle", not "long enough to finish".
SOLVE_BUDGET_SECONDS = '10'

# Arbitrary, deliberately different hash seeds - the point is that they differ.
HASH_SEEDS = ['1', '424242', '7']


def replay(capture: Path, seed: str, output_path: Path) -> None:
    # The no-improvement stall timeout (config.SOLVER_STOP_AFTER_NO_IMPROVEMENT_SECONDS)
    # is itself wall-clock-based, so leaving it enabled would add a second
    # load-sensitive cutoff on top of SOLVE_BUDGET_SECONDS - two chances to stop at
    # a different incumbent instead of one. Passing `none` disables it outright,
    # leaving the budget as the only cutoff.
    #
    # Note this only started taking effect once SolverService stopped treating
    # `None` as "use the config default"; before that, `none` silently fell back to
    # the configured stall and this test ran with both cutoffs active.
    result = subprocess.run(
        [sys.executable, str(REPLAY_SCRIPT), str(capture), str(output_path),
         '--max-seconds', SOLVE_BUDGET_SECONDS, '--no-improvement-seconds', 'none'],
        capture_output=True, text=True,
        env={'PYTHONHASHSEED': seed, 'PATH': os.environ.get('PATH', '')},
    )
    if result.returncode != 0:
        print(f"Replay of {capture.name} with PYTHONHASHSEED={seed} failed:\n{result.stderr}")
        sys.exit(1)


def main():
    captures = sorted(CAPTURES_DIR.glob('drivingplan-*.json'))
    if not captures:
        print(f"No captures found in {CAPTURES_DIR}")
        sys.exit(1)

    failed = False
    with tempfile.TemporaryDirectory() as tmpdir:
        for capture in captures:
            plans = []
            for seed in HASH_SEEDS:
                output_path = Path(tmpdir) / f'{capture.stem}-seed-{seed}.json'
                replay(capture, seed, output_path)
                with open(output_path) as f:
                    plans.append(json.load(f))

            mismatched = [seed for seed, plan in zip(HASH_SEEDS[1:], plans[1:]) if plan != plans[0]]
            if mismatched:
                failed = True
                print(
                    f"❌ {capture.name}: plan under PYTHONHASHSEED={HASH_SEEDS[0]} differs from "
                    f"seed(s) {mismatched} for the same input. The solver is not deterministic."
                )
            else:
                print(f"✅ {capture.name}: identical across PYTHONHASHSEED values {HASH_SEEDS}")

    if failed:
        sys.exit(1)
    print(f"\n✅ All {len(captures)} captures replayed identically across "
          f"{len(HASH_SEEDS)} hash seeds")


if __name__ == '__main__':
    main()
