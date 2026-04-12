# Setup DynaPyt

A GitHub Actions composite action that installs [DynaPyt](https://github.com/sola-st/DynaPyt), instruments a Python project, and configures the session for dynamic call-graph analysis in CI — just like `setup-cintent`.

## Quick Start

```yaml
steps:
  - uses: actions/checkout@v4

  - uses: actions/setup-python@v4
    with:
      python-version: "3.10"

  - name: Install project
    run: pip install .

  - uses: clonedSemicolon/setup-dynapyt@main
    with:
      directory: my_package/

  - name: Run tests
    run: pytest tests/

  - uses: actions/upload-artifact@v4
    if: always()
    with:
      name: dynapyt-callgraph
      path: dynapyt.json
```

## Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `directory` | yes | | Directory to instrument (relative to workspace) |
| `analysis` | no | `dynapyt.analyses.CallGraph.CallGraph` | DynaPyt analysis class |
| `dynapyt_path` | no | `git+https://github.com/sola-st/DynaPyt.git` | Git URL or local path to install DynaPyt from |

## How it works

1. Installs DynaPyt (+ libcst)
2. Patches `CallGraph` logging (`force=True`) so it works after pytest configures logging
3. Instruments the target directory (`dynapyt.run_instrumentation`)
4. Configures the DynaPyt session (`DYNAPYT_SESSION_ID` + analyses temp file)

After setup, just run your tests normally. The instrumented code auto-activates `RuntimeEngine`, which loads the configured analysis. On process exit, `end_execution()` writes `dynapyt.json` to the working directory.
