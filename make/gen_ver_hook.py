import sys
import subprocess

run = subprocess.run(['git', 'describe', '--tags'], capture_output=True, encoding='utf-8')
if run.returncode == 0:
    desc = run.stdout.strip()
    if '-' in desc:
        major, minor, _ = desc.split('-')
        auto_ver = major + '.' + minor
    else:   # means current commit exactly matches the tag
        auto_ver = desc
else:
    auto_ver = "v0.unknown"

print('JavSP version: ' + auto_ver)

hook_file = sys.argv[1]
with open(hook_file, 'wt') as f:
    f.write('import sys\n')
    f.write("setattr(sys, 'javsp_version', '" + auto_ver + "')\n")
