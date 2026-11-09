"""Local shutdown guard for one explicitly identified Thunder generation instance.

Stops that instance after all expected traces are saved, 20 minutes without
progress, or six hours total. Never deletes an instance with a different name.
Run under caffeinate on macOS; internet and the SSH tunnel must stay available.
"""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.build_specs import all_specs
from src.scenarios import load_scenarios


class InstanceIdentityError(ValueError):
    pass


def matching_instance(instances, instance_id, expected_name):
    matches = [x for x in instances if str(x['id']) == str(instance_id)]
    if not matches:
        return None
    instance = matches[0]
    if instance.get('name') != expected_name or instance.get('uuid') != expected_name:
        raise InstanceIdentityError('Instance identity changed; refusing to delete it')
    return instance


def stop_reason(saved, expected, elapsed, idle, max_seconds, stall_seconds):
    if saved == expected:
        return 'all_expected_files_saved'
    if elapsed >= max_seconds:
        return 'runtime_limit'
    if idle >= stall_seconds:
        return 'no_file_progress'
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', required=True)
    ap.add_argument('--instance-id', required=True)
    ap.add_argument('--instance-name', required=True)
    ap.add_argument('--tnr', required=True)
    ap.add_argument('--tnr-home', required=True)
    ap.add_argument('--max-hours', type=float, default=6)
    ap.add_argument('--stall-minutes', type=float, default=20)
    args = ap.parse_args()
    out = Path(args.out)
    expected = {s.conv_id for s in all_specs(load_scenarios())}
    manifest = json.loads((out / 'manifest.json').read_text())
    started = dt.datetime.fromisoformat(manifest['started_at']).timestamp()
    env = dict(os.environ, TNR_HOME=args.tnr_home)
    status_path = out / 'shutdown_status.json'
    last_count = -1
    last_progress = time.time()
    print('Shutdown guard active for', args.instance_name, flush=True)

    def status(**values):
        state = dict(instance_name=args.instance_name,
                     checked_at=dt.datetime.now(ZoneInfo('America/New_York')).isoformat(), **values)
        temporary = status_path.with_suffix('.tmp')
        temporary.write_text(json.dumps(state, indent=2) + '\n')
        temporary.replace(status_path)

    def cli(*params):
        result = subprocess.run([args.tnr, *params], env=env, capture_output=True,
                                text=True, timeout=45)
        if result.returncode:
            raise RuntimeError(f'Thunder command failed (exit {result.returncode})')
        return json.loads(result.stdout)

    while True:
        now = time.time()
        paths = [out / f'{cid}.jsonl' for cid in expected]
        present = [p for p in paths if p.exists()]
        count = len(present)
        if count != last_count:
            last_progress = now
            last_count = count
        latest = max((p.stat().st_mtime for p in present), default=last_progress)
        idle = now - max(last_progress, latest)
        reason = stop_reason(count, len(expected), now - started, idle,
                             args.max_hours * 3600, args.stall_minutes * 60)
        if reason == 'all_expected_files_saved':
            # Avoid racing the generator while its last file is being written.
            try:
                for p in present:
                    records = [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
                    if len(records) < 2 or records[0].get('conv_id') != p.stem:
                        raise ValueError('Incomplete trace')
            except (ValueError, OSError):
                reason = None
        status(state='monitoring', saved_conversations=count, expected_conversations=len(expected),
               idle_seconds=round(idle), runtime_seconds=round(now - started))
        if reason:
            try:
                instances = cli('status', '--no-wait', '--json')
                instance = matching_instance(instances, args.instance_id, args.instance_name)
                if instance is not None:
                    result = cli('delete', args.instance_id, '--yes', '--json')
                    if not result.get('success'):
                        raise RuntimeError('Thunder did not confirm deletion')
                status(state='instance_deleted' if instance else 'instance_already_absent',
                       reason=reason, saved_conversations=count, expected_conversations=len(expected))
                print('Shutdown complete:', reason, f'({count}/{len(expected)} saved)', flush=True)
                return
            except InstanceIdentityError as exc:
                status(state='identity_mismatch', reason=str(exc), saved_conversations=count)
                print('Identity mismatch; no instance was deleted.', flush=True)
                return
            except (RuntimeError, subprocess.TimeoutExpired, OSError, json.JSONDecodeError):
                status(state='shutdown_retry_pending', reason=reason, saved_conversations=count)
                print('Shutdown request unavailable; retrying in 30 seconds.', flush=True)
        time.sleep(30)


if __name__ == '__main__':
    main()
