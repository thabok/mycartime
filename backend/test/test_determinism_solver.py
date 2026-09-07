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

   Proving optimality on a real capture takes minutes, so this test uses a
   bounded budget and relies on the optimum being *found* (not proven) within a
   couple of seconds - see SOLVE_BUDGET_SECONDS. Truncating the search after
   the optimum is already the incumbent still yields the same plan, so the
   comparison is meaningful without a multi-minute test.

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

# Comfortably longer than the ~3s the solver needs to *find* the optimum on
# these captures, and far shorter than the ~3min it needs to prove it.
SOLVE_BUDGET_SECONDS = '10'

# Arbitrary, deliberately different hash seeds - the point is that they differ.
HASH_SEEDS = ['1', '424242', '7']


def replay(capture: Path, seed: str, output_path: Path) -> None:
    # The no-improvement stall timeout (config.SOLVER_STOP_AFTER_NO_IMPROVEMENT_SECONDS)
    # is itself wall-clock-based, so leaving it enabled here would make this test
    # flaky under machine load - it could stop the search at a different incumbent
    # on different runs even with byte-identical model building. Disabling it makes
    # SOLVE_BUDGET_SECONDS the only (still wall-clock-based, but far more generous)
    # cutoff, which is what actually gives this test its "finds the same optimum
    # every time" guarantee.
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
