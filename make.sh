#!/usr/bin/env bash 

set +x

if [[ "$VIRTUAL_ENV" == "" ]]
then
  source venv/bin/activate
fi

echo "JavSP version: "
python ./make/gen_ver_hook.py ver_hook.py
pyinstaller --clean ./make/linux.spec
rm ver_hook.py
rm dist/config.ini 2> null
cp -r ./data ./build
