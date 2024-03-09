#!/usr/bin/env bash 

set -x

python -m venv venv
source ./venv/bin/activate
pip install -r ./requirements.txt
pip install pyinstaller

echo "JavSP version: "
python ./make/gen_ver_hook.py ver_hook.py
pyinstaller --clean ./make/linux.spec
rm ver_hook.py
rm dist/config.ini 2> /dev/null
cp -r ./data ./dist
