import sys
import platform
import subprocess

run = subprocess.run(['git', 'describe', '--tags', '--long'], capture_output=True, encoding='utf-8')
if run.returncode == 0:
    desc = run.stdout.strip()
    tag_name, minor, _ = desc.split('-')
    if int(minor) == 0: # means current commit exactly matches the tag
        auto_ver = tag_name
    else:
        if tag_name.count('.') == 1:
            auto_ver = tag_name + '.0.' + minor
        else:
            auto_ver = tag_name + '.' + minor
else:
    auto_ver = "v0.unknown"

print(auto_ver)

# Generate powershell script to create zip file
if platform.system() == 'Windows':
    with open('make\\archive.ps1', 'wt', encoding='utf-8') as f:
        zip_file = 'dist\\JavSP-' + auto_ver + '-Windows-amd64.zip'
        command = 'Compress-Archive -Path dist\\JavSP.exe -Force -DestinationPath ' + zip_file
        f.write(command)

if len(sys.argv) > 1:
    hook_file = sys.argv[1]
    with open(hook_file, 'wt', encoding='utf-8') as f:
        f.write('import sys\n')
        f.write("setattr(sys, 'javsp_version', '" + auto_ver + "')\n")
