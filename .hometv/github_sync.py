"""GitHub Actions entry point: propose updates, never auto-merge or deploy."""
import json
import os
from pathlib import Path
import subprocess
import sys

from maintain import ROOT, git, sync, write_json


def main():
    report_dir = ROOT / 'dist/sync'
    report = sync(report_dir)
    print(json.dumps(report))
    if report['status'] == 'current':
        return
    if report['status'] == 'existing':
        print('Update branch already exists; retaining all maintainer changes.')
        return
    branch = report['branch']
    if report['status'] == 'candidate':
        try:
            git('switch', branch)
            result = subprocess.run([sys.executable, '.hometv/maintain.py', 'build'], cwd=ROOT)
            report['build'] = 'passed' if result.returncode == 0 else 'failed'
        finally:
            git('switch', 'home-tv')
        git('push', 'origin', 'upstream-stable:upstream-stable')
    git('push', 'origin', branch + ':' + branch)
    write_json(report_dir / 'report.json', report)
    body = report_dir / 'pull-request.md'
    with body.open('a', encoding='utf-8') as stream:
        stream.write('\nCandidate build: ' + report.get('build', 'blocked by conflicts') + '.\n')
    # A draft proposal is part of the configured update workflow. It never
    # merges a change or posts a message outside this repository.
    result = subprocess.run(['gh', 'pr', 'create', '--base', 'home-tv', '--head', branch,
                    '--draft', '--title', 'Update Arctic Fuse to ' + report['version'],
                    '--body-file', str(body)], cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        # Some repositories forbid PR creation with GITHUB_TOKEN. Keep the
        # proposal and provide a comparison instead of widening permissions.
        report['pull_request'] = 'not_created'
        report['comparison'] = ('https://github.com/' + os.environ['GH_REPO']
                                + '/compare/home-tv...' + branch + '?expand=1')
        print('Update branch is ready. Open the comparison to review it: ' + report['comparison'])
    else:
        report['pull_request'] = result.stdout.strip()
        print(result.stdout.strip())
    write_json(report_dir / 'report.json', report)
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary, 'a', encoding='utf-8') as stream:
            stream.write('## Arctic update proposal\n\n' + body.read_text(encoding='utf-8')
                         + '\n' + report.get('comparison', report['pull_request']) + '\n')


if __name__ == '__main__':
    main()
