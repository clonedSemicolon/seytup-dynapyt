# Setup DynaPyt — GitHub Action

A composite GitHub Action that instruments Python code with [DynaPyt](https://github.com/sola-st/DynaPyt) and configures a session so that **any subsequent test step** automatically triggers dynamic analysis.

## How it works

```
┌─────────────────────┐     ┌──────────────────────┐     ┌──────────────────┐
│  1. Setup DynaPyt   │ ──▶ │  2. Run your tests   │ ──▶ │  3. Collect      │
│  (this action)      │     │  (pytest/tox/etc.)   │     │  results         │
│                     │     │                      │     │                  │
│  • Install DynaPyt  │     │  Tests import the    │     │  • post_run      │
│  • Instrument code  │     │  instrumented code → │     │  • upload-       │
│  • Set session env  │     │  hooks fire → traces │     │    artifact      │
└─────────────────────┘     └──────────────────────┘     └──────────────────┘
```

DynaPyt **rewrites your source files** with instrumentation hooks. When any Python process imports that code, DynaPyt's `RuntimeEngine` detects the `DYNAPYT_SESSION_ID` env var, loads the configured analysis, and starts tracing. This means your existing test commands work unchanged.

## Usage

### Basic example (instrument a directory)

```yaml
steps:
  - uses: actions/checkout@v4
  - uses: actions/setup-python@v5
    with:
      python-version: "3.10"

  - name: Install deps
    run: pip install -e .

  - name: Setup DynaPyt
    uses: clonedSemicolon/seytup-dynapyt@master
    with:
      directory: "src/mypackage"
      analysis: "dynapyt.analyses.CallGraph.CallGraph"

  - name: Run tests
    run: pytest tests/

  - name: Collect results
    if: always()
    run: python -m dynapyt.post_run --output_dir=dynapyt-output || true

  - uses: actions/upload-artifact@v4
    if: always()
    with:
      name: dynapyt-results
      path: dynapyt-output/
```

### Instrument an installed package by name

```yaml
  - name: Setup DynaPyt
    uses: clonedSemicolon/seytup-dynapyt@master
    with:
      package: "grab"
      analysis: "dynapyt.analyses.TraceAll.TraceAll"
```

### Using with grab

```yaml
  - name: Install grab
    run: |
      pip install -r requirements_dev.txt
      pip install -e .

  - name: Setup DynaPyt
    uses: clonedSemicolon/seytup-dynapyt@master
    with:
      directory: "grab"
      analysis: "dynapyt.analyses.CallGraph.CallGraph"

  - name: Run tests
    run: pytest --timeout=60 --import-mode=importlib tests/ || true

  - name: Merge & upload
    if: always()
    run: python -m dynapyt.post_run --output_dir=dynapyt-output || true

  - uses: actions/upload-artifact@v4
    if: always()
    with:
      name: dynapyt-callgraph
      path: dynapyt-output/
```

## Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `directory` | no | `""` | Directory to instrument (relative to workspace). **Takes precedence over `package`.** |
| `package` | no | `""` | Installed Python package name to instrument (e.g. `grab`). Resolves path automatically. |
| `analysis` | no | `dynapyt.analyses.CallGraph.CallGraph` | DynaPyt analysis class (full dotted path) |
| `output` | no | `dynapyt-output` | Directory for DynaPyt output files |
| `dynapyt_path` | no | `""` | Custom DynaPyt install source (git URL or local path) |

> **Note:** Either `directory` or `package` must be provided.

## Outputs

| Output | Description |
|--------|-------------|
| `session-id` | The DynaPyt session UUID |
| `output-dir` | Absolute path to the output directory |

### Using outputs

```yaml
  - name: Setup DynaPyt
    id: dynapyt
    uses: clonedSemicolon/seytup-dynapyt@master
    with:
      directory: "src"

  - name: Show session
    run: echo "Session ID: ${{ steps.dynapyt.outputs.session-id }}"
```

## Available analyses

| Analysis | Dotted path | Description |
|----------|-------------|-------------|
| CallGraph | `dynapyt.analyses.CallGraph.CallGraph` | Dynamic call graph |
| TraceAll | `dynapyt.analyses.TraceAll.TraceAll` | Full execution trace |

See the [DynaPyt analyses folder](https://github.com/sola-st/DynaPyt/tree/main/src/dynapyt/analyses) for all built-in analyses, or implement your own.

## How to add to an existing CI workflow

Add these steps **after** your dependency installation and **before** your test step:

```yaml
  # Add this BEFORE your test step
  - name: Setup DynaPyt
    uses: clonedSemicolon/seytup-dynapyt@master
    with:
      directory: "your_package"

  # Your existing test step (unchanged)
  - name: Run tests
    run: pytest tests/

  # Add this AFTER your test step
  - name: Collect DynaPyt output
    if: always()
    run: python -m dynapyt.post_run --output_dir=dynapyt-output || true

  - uses: actions/upload-artifact@v4
    if: always()
    with:
      name: dynapyt-results
      path: dynapyt-output/
```

That's it — your existing test command stays the same.

## Workflow Generator for DyPyBench Projects

The included `generate_dynapyt_workflow.py` script can generate ready-to-use DynaPyt workflows for any of the 58 projects in [DyPyBench](https://github.com/sola-st/DyPyBench).

### List all projects

```bash
python generate_dynapyt_workflow.py --list
```

### Generate a workflow file

```bash
# Generate workflow for project #1 (grab)
python generate_dynapyt_workflow.py --project 1

# Save to a specific file
python generate_dynapyt_workflow.py --project 1 -o dynapyt.yml
```

### Fork, inject workflow, and push

```bash
# Automatically fork the repo, add the workflow, and push
python generate_dynapyt_workflow.py --project 1 --clone --push
```

This will:
1. Fork the project on GitHub (via `gh repo fork`)
2. Clone your fork locally
3. Add `.github/workflows/dynapyt.yml` with the correct source dirs, test dirs, and dependencies
4. Commit and push

Then go to **Actions** in your fork and run the workflow.
