"""
Regression test for the driving-plan algorithm's determinism.

Background: Python randomizes string-hash order per process by default
(PYTHONHASHSEED), and the algorithm used to iterate over set-typed
collections of member initials at a few points that affected real
decisions (not just cosmetic ones) - so the same input could silently
produce a different, sometimes worse, plan depending on which process
happened to run it. See algorithm-improvement-plan.md for the full
investigation.

This test replays a real captured input (see app._capture_plan_input)
under two different PYTHONHASHSEED values, each in its own subprocess,
and asserts the resulting plans are byte-identical - so this class of
bug can't silently regress.

Usage: python test_determinism.py
"""
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
REPLAY_SCRIPT = REPO_ROOT / 'backend' / 'src' / 'experiments' / 'replay_capture.py'
CAPTURE_FILE = REPO_ROOT / 'backend' / 'src' / 'captures' / 'drivingplan-20260907-195113-598833.json'

# Arbitrary, deliberately different hash seeds - the point is that they differ.
HASH_SEEDS = ['1', '424242']


def replay_with_seed(seed: str, output_path: Path) -> None:
    env = {'PYTHONHASHSEED': seed, 'PATH': __import__('os').environ.get('PATH', '')}
    result = subprocess.run(
        [sys.executable, str(REPLAY_SCRIPT), str(CAPTURE_FILE), str(output_path)],
        capture_output=True, text=True, env=env,
    )
    if result.returncode != 0:
        print(f"Replay with PYTHONHASHSEED={seed} failed:\n{result.stderr}")
        sys.exit(1)


def main():
    if not CAPTURE_FILE.exists():
        print(f"Capture file not found: {CAPTURE_FILE}")
        sys.exit(1)

    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        plans = []
        for seed in HASH_SEEDS:
            output_path = tmpdir / f'plan-seed-{seed}.json'
            replay_with_seed(seed, output_path)
            with open(output_path) as f:
                plans.append(json.load(f))

    first = plans[0]
    for seed, plan in zip(HASH_SEEDS[1:], plans[1:]):
        if plan != first:
            print(
                f"❌ FAILED: plan replayed under PYTHONHASHSEED={HASH_SEEDS[0]} differs from "
                f"PYTHONHASHSEED={seed} for the same input. The algorithm is not deterministic."
            )
            sys.exit(1)

    print(f"✅ Plan is identical across PYTHONHASHSEED values {HASH_SEEDS}")


if __name__ == '__main__':
    main()
