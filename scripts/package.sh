#!/bin/sh
set -eu

cd "$(dirname "$0")/.."
mkdir -p dist
rm -f dist/fkill.alfredworkflow

chmod +x fkill.py run_fkill.sh
/usr/bin/zip -qr dist/fkill.alfredworkflow info.plist fkill.py run_fkill.sh icon.png
echo "Wrote dist/fkill.alfredworkflow"
