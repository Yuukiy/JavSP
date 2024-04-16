#!/usr/bin/env bash 

set -x

layout_poetry() {
  if [[ ! -f pyproject.toml ]]; then
    echo 'No pyproject.toml found. Use `poetry new` or `poetry init` to create one first.'
    exit 2
  fi

  local VENV=$(poetry env info --path)
  if [[ -z $VENV || ! -d $VENV/bin ]]; then
    echo 'No poetry virtual environment found. Use `poetry install` to create one first.'
    exit 2
  fi

  export VIRTUAL_ENV=$VENV
  export POETRY_ACTIVE=1
  PATH_add "$VENV/bin"
}

layout_poetry

echo "JavSP version: "
python ./make/gen_ver_hook.py ver_hook.py
pyinstaller --clean ./make/build.spec
rm ver_hook.py
rm dist/config.ini 2> /dev/null
cp -r ./data ./dist
