import sys
import platform
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

# Generate powershell script to create zip file
if platform.system() == 'Windows':
    with open('make\\archive.ps1', 'wt', encoding='utf-8') as f:
        zip_file = 'dist\\JavSP-' + auto_ver + '-Windows-amd64.zip'
        command = 'Compress-Archive -Path dist\\JavSP.exe -Force -DestinationPath ' + zip_file
        f.write(command)

hook_file = sys.argv[1]
with open(hook_file, 'wt') as f:
    f.write('import sys\n')
    f.write("setattr(sys, 'javsp_version', '" + auto_ver + "')\n")
