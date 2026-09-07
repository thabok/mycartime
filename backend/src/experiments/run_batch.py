"""
Run the algorithm many times against a single captured input, each trial in
its own subprocess (fresh PYTHONHASHSEED, matching a real backend restart),
to reproduce the "same input, sometimes worse plan" variance.

Usage: python run_batch.py <capture.json> <output_dir> [num_trials]
"""
import subprocess
import sys
import time
from pathlib import Path

REPLAY_SCRIPT = Path(__file__).parent / 'replay_capture.py'


def main():
    if len(sys.argv) < 3:
        print("Usage: python run_batch.py <capture.json> <output_dir> [num_trials]")
        sys.exit(1)

    capture_path = Path(sys.argv[1]).resolve()
    output_dir = Path(sys.argv[2]).resolve()
    num_trials = int(sys.argv[3]) if len(sys.argv) > 3 else 50

    output_dir.mkdir(parents=True, exist_ok=True)

    failures = 0
    for i in range(num_trials):
        output_path = output_dir / f"plan-{i:03d}.json"
        start = time.time()
        result = subprocess.run(
            [sys.executable, str(REPLAY_SCRIPT), str(capture_path), str(output_path)],
            capture_output=True,
            text=True,
        )
        elapsed = time.time() - start
        if result.returncode != 0:
            failures += 1
            print(f"[{i:03d}] FAILED ({elapsed:.1f}s): {result.stderr.strip().splitlines()[-1] if result.stderr else 'unknown error'}")
        else:
            print(f"[{i:03d}] ok ({elapsed:.1f}s)")

    print(f"\n{num_trials - failures}/{num_trials} trials succeeded, output in {output_dir}")


if __name__ == '__main__':
    main()
