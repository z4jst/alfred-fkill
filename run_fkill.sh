#!/bin/sh
set -eu

for python in /usr/bin/python3 /opt/homebrew/bin/python3 /usr/local/bin/python3 python3; do
	if command -v "$python" >/dev/null 2>&1; then
		exec "$python" ./fkill.py "$@"
	fi
done

if [ "${1:-}" = "filter" ]; then
	/usr/bin/printf '{"items":[{"title":"Python 3 not found","subtitle":"Install Python 3 or Xcode Command Line Tools, then try fkill again.","valid":false}]}\n'
else
	/usr/bin/printf 'Python 3 not found\n' >&2
fi

exit 1
