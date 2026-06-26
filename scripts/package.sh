#!/bin/sh
set -eu

cd "$(dirname "$0")/.."
mkdir -p dist
rm -f dist/fkill.alfredworkflow

chmod +x fkill.py
/usr/bin/zip -qr dist/fkill.alfredworkflow info.plist fkill.py
echo "Wrote dist/fkill.alfredworkflow"
