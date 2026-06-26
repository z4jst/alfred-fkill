# fkill Alfred Workflow

Type `fkill` in Alfred to list running processes.

Examples:

- `fkill` lists current processes.
- `fkill chrome` shows Chrome-related processes.
- Press Return on the first result to force kill every matching process.
- Press Return on an individual result to force kill only that PID.

The workflow uses `SIGKILL`, equivalent to `kill -9`.

## Build

```sh
./scripts/package.sh
```

The importable workflow is written to `dist/fkill.alfredworkflow`.
