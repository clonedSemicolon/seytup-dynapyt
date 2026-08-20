# Setup DynaPyt — GitHub Action

A composite GitHub Action that instruments Python code with [DynaPyt](https://github.com/sola-st/DynaPyt) and configures a session so that **any subsequent test step** automatically triggers dynamic analysis. Used a second time with `mode: collect`, it gathers the traces and uploads them as a workflow artifact.

## How it works

```
┌─────────────────────┐     ┌──────────────────────┐     ┌──────────────────────┐
│  1. Setup DynaPyt   │ ──▶ │  2. Run your tests   │ ──▶ │  3. Collect DynaPyt  │
│  (mode: setup)      │     │  (pytest/tox/etc.)   │     │  (mode: collect)     │
│                     │     │                      │     │                      │
│  • Install DynaPyt  │     │  Tests import the    │     │  • merge traces      │
│  • Instrument code  │     │  instrumented code → │     │  • upload artifact   │
│  • Set session env  │     │  hooks fire → traces │     │                      │
└─────────────────────┘     └──────────────────────┘     └──────────────────────┘
```

DynaPyt **rewrites your source files** with instrumentation hooks. When any Python process imports that code, DynaPyt's `RuntimeEngine` detects the `DYNAPYT_SESSION_ID` env var, loads the configured analysis, and starts tracing. This means your existing test commands work unchanged.

The setup mode writes the session's analyses file with `output_dir` pointing at `$GITHUB_WORKSPACE/dynapyt-output` (exposed as `$DYNAPYT_OUTPUT_DIR`), and patches the built-in `CallGraph`/`TraceAll` analyses so their trace files (`dynapyt.json`, `output.log`) land in that directory instead of the test process's working directory. The collect mode merges any per-process `output-*.json` files and uploads the whole directory as an artifact.

## Usage

### Which input do I use: `directory` or `package`?

The only rule that matters, for **any** project: instrument the copy of the code your tests will *import*.

| How the project is set up before tests | What to use |
|-----------------------------------------|-------------|
| `pip install -e .` (editable) or imported straight from the repo | `directory: "path/to/source"` |
| `pip install .` or a built wheel/sdist (code copied to site-packages) | `package: "import_name"` |
| Not sure | `package: "import_name"` — it always resolves to whatever `import` would load |

Everything else (analysis choice, collection, artifact upload) is identical regardless of project.

### Trace several Python steps with two workflow changes

Start one session before the Python steps you care about and collect once at
the end of the job. The `targets` input accepts multiple source types under
the same session:

```yaml
steps:
  - uses: actions/checkout@v4
  - uses: actions/setup-python@v5
    with:
      python-version: "3.11"

  # Added step 1: instrument every Python target needed by later steps.
  - name: Start job-wide DynaPyt trace
    uses: clonedSemicolon/seytup-dynapyt@master
    with:
      targets: |
        package:pip
        directory:src
        file:scripts/release_check.py
      analysis: dynapyt.analyses.CallGraph.CallGraph

  # Existing workflow steps remain unchanged.
  - name: Install dependencies
    run: python -m pip install -r requirements.txt

  - name: Run tests
    run: python -m pytest

  - name: Release check
    run: python scripts/release_check.py

  # Added step 2: merge and upload one artifact for this job.
  - name: Collect DynaPyt traces
    if: always()
    uses: clonedSemicolon/seytup-dynapyt@master
    with:
      mode: collect
      artifact-name: dynapyt-${{ github.run_id }}-${{ github.job }}
```

Target prefixes have precise meanings:

- `directory:<path>` recursively instruments Python files in a source directory.
- `package:<name>` instruments the source resolved by that Python import name.
- `file:<path>` instruments one Python file.

`package:pip` traces Python calls inside the dependency-installation step.
`directory:src` traces calls from an editable/source-tree application during
later tests. DynaPyt observes only instrumented Python code; it does not trace
shell commands, JavaScript actions, or GitHub's runner orchestration.


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

  - name: Collect & upload DynaPyt traces
    if: always()
    uses: clonedSemicolon/seytup-dynapyt@master
    with:
      mode: collect
      artifact-name: dynapyt-results
```

### Example: project installed as a wheel before testing

Some CI workflows build and install the package (e.g. `make build` + `pip install dist/*.whl`, or plain `pip install .`) instead of using an editable install. Tests then import the copy in **site-packages**, so instrumenting the source tree in the workspace produces empty traces. Use `package` and the action resolves the installed location automatically:

```yaml
  - name: Build wheel and install
    run: |
      python -m build
      pip install dist/*.whl

  - name: Setup DynaPyt
    uses: clonedSemicolon/seytup-dynapyt@master
    with:
      package: "mypackage"    # the name you `import`, not the PyPI name
      analysis: "dynapyt.analyses.CallGraph.CallGraph"

  - name: Run tests
    run: pytest tests/

  - name: Collect & upload DynaPyt traces
    if: always()
    uses: clonedSemicolon/seytup-dynapyt@master
    with:
      mode: collect
      artifact-name: dynapyt-callgraph
```

## Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `mode` | no | `setup` | `setup` installs/instruments/configures before Python steps; `collect` gathers traces and uploads one job artifact |
| `targets` | no* | `""` | Newline-separated `directory:`, `package:`, or `file:` targets. Takes precedence over the legacy single-target inputs |
| `directory` | no* | `""` | Legacy single directory target (relative to workspace) |
| `package` | no* | `""` | Legacy single installed-package target using its Python import name |
| `analysis` | no | `dynapyt.analyses.CallGraph.CallGraph` | DynaPyt analysis class (full dotted path) |
| `dynapyt_path` | no | DynaPyt git repo | Custom DynaPyt install source (git URL or local path). Empty = PyPI |
| `artifact-name` | no | `dynapyt-results` | Artifact name (collect mode only) |
| `fail-on-empty` | no | `true` | Fail setup if none of the selected targets produced instrumented files |

\* Setup mode requires `targets`, `directory`, or `package`.

## Outputs

| Output | Description |
|--------|-------------|
| `session-id` | The DynaPyt session UUID (setup mode) |
| `output-dir` | Absolute path to the trace output directory |

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

The setup mode also exports `DYNAPYT_SESSION_ID` and `DYNAPYT_OUTPUT_DIR` to the job environment, so later steps can use them directly.

## Available analyses

| Analysis | Dotted path | Trace file |
|----------|-------------|------------|
| CallGraph | `dynapyt.analyses.CallGraph.CallGraph` | `dynapyt.json` |
| TraceAll | `dynapyt.analyses.TraceAll.TraceAll` | `output.log` |

See the [DynaPyt analyses folder](https://github.com/sola-st/DynaPyt/tree/main/src/dynapyt/analyses) for all built-in analyses, or implement your own. Custom analyses receive `output_dir` (pointing at `$DYNAPYT_OUTPUT_DIR`) via their constructor; any `output-*.json` they write there is merged into `output.json` by the collect mode.

## How to add to an existing CI workflow

Add one step **after** your dependency installation and **before** your test step, and one step **after** your test step:

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
  - name: Collect & upload DynaPyt traces
    if: always()
    uses: clonedSemicolon/seytup-dynapyt@master
    with:
      mode: collect
```

That's it — your existing test command stays the same.

## Combine traces from multiple jobs

GitHub jobs run on isolated runners, so start/collect once in every Python job
and give each artifact a unique name such as
`dynapyt-${{ github.run_id }}-${{ github.job }}`. A final job can bundle them:

```yaml
  dynapyt-bundle:
    if: ${{ always() }}
    needs: [test, integration]
    runs-on: ubuntu-latest
    steps:
      - name: Download job traces
        uses: actions/download-artifact@v4
        with:
          pattern: dynapyt-${{ github.run_id }}-*
          path: dynapyt-all
          merge-multiple: false

      - name: Upload one workflow trace bundle
        uses: actions/upload-artifact@v4
        with:
          name: dynapyt-workflow-${{ github.run_id }}
          path: dynapyt-all/
```

List every traced job in `needs`. The downloaded artifact directories remain
separate, preventing identically named files such as `dynapyt.json` from
overwriting one another.


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
