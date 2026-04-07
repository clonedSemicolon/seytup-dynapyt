"""
generate_dynapyt_workflow.py — Generate a DynaPyt CI workflow for any DyPyBench project.

Usage:
    python generate_dynapyt_workflow.py --project 1
    python generate_dynapyt_workflow.py --project 1 --clone --push
    python generate_dynapyt_workflow.py --list

What it does:
    1. Looks up the project by number in the built-in DyPyBench registry
    2. Generates a .github/workflows/dynapyt.yml tailored to that project
    3. Optionally: forks, clones the repo, adds the workflow, commits, and pushes
"""

import argparse
import os
import subprocess
import sys

# ─────────────────────────────────────────────────────────────────────────────
# DyPyBench project registry
# Format: (url, flags, requirements_file_or_None, test_dir)
# flags: "rt" = requirements + test, "t" = test only, "r" = requirements only
# ─────────────────────────────────────────────────────────────────────────────
PROJECTS = [
    ("https://github.com/lorien/grab.git",           "rt", "requirements_dev.txt",              "tests"),
    ("https://github.com/AtsushiSakai/PythonRobotics.git", "rt", "requirements/requirements.txt", "tests"),
    ("https://github.com/flask-api/flask-api.git",   "t",  None,                                "flask_api/tests"),
    ("https://github.com/dbader/schedule.git",        "rt", "requirements-dev.txt",              "test_schedule.py"),
    ("https://github.com/python-pillow/Pillow.git",   "t",  None,                                "Tests"),
    ("https://github.com/Supervisor/supervisor.git",   "t",  None,                                "supervisor/tests"),
    ("https://github.com/Parsely/streamparse.git",    "rt", "test-requirements.txt",             "test"),
    ("https://github.com/spotify/dh-virtualenv.git",   "rt", "dev-requirements.txt",              "test"),
    ("https://github.com/mitmproxy/pdoc.git",         "rt", "requirements-dev.txt",              "test"),
    ("https://github.com/pallets/click.git",           "rt", "requirements/tests.txt",            "tests"),
    ("https://github.com/amitt001/delegator.py.git",   "t",  None,                                "tests"),
    ("https://github.com/faif/python-patterns.git",    "rt", "requirements-dev.txt",              "tests"),
    ("https://github.com/encode/uvicorn.git",          "rt", "requirements.txt",                  "tests"),
    ("https://github.com/jiaaro/pydub.git",            "t",  None,                                "test/test.py"),
    ("https://github.com/jpadilla/pyjwt.git",          "t",  None,                                "tests"),
    ("https://github.com/pyeve/cerberus.git",          "t",  None,                                "cerberus/tests"),
    ("https://github.com/grantjenks/python-diskcache.git", "rt", "requirements.txt",             "tests"),
    ("https://github.com/errbotio/errbot.git",         "rt", "requirements.txt",                  "tests"),
    ("https://github.com/psf/black.git",               "rt", "test_requirements.txt",             "tests"),
    ("https://github.com/nvbn/thefuck.git",            "rt", "requirements.txt",                  "tests"),
    ("https://github.com/PythonCharmers/python-future.git", "t", None,                            "tests"),
    ("https://github.com/HBNetwork/python-decouple.git", "rt", "requirements.txt",               "tests"),
    ("https://github.com/arrow-py/arrow.git",          "rt", "requirements/requirements-tests.txt", "tests"),
    ("https://github.com/inducer/pudb.git",            "rt", "requirements.dev.txt",              "test"),
    ("https://github.com/akfamily/akshare.git",        "rt", "requirements-dev.txt",              "tests"),
    ("https://github.com/mwaskom/seaborn.git",         "t",  None,                                "tests"),
    ("https://github.com/PyFilesystem/pyfilesystem2.git", "t", None,                              "tests"),
    ("https://github.com/wtforms/wtforms.git",         "t",  None,                                "tests"),
    ("https://github.com/Suor/funcy.git",              "rt", "test_requirements.txt",             "tests"),
    ("https://github.com/graphql-python/graphene.git", "t",  None,                                "graphene/tests"),
    ("https://github.com/geopy/geopy.git",             "t",  None,                                "test"),
    ("https://github.com/gawel/pyquery.git",           "t",  None,                                "tests"),
    ("https://github.com/psf/requests.git",            "rt", "requirements-dev.txt",              "tests"),
    ("https://github.com/scikit-learn/scikit-learn.git", "rt", None,                              "tests"),
    ("https://github.com/pallets-eco/blinker.git",     "t",  None,                                "tests"),
    ("https://github.com/0rpc/zerorpc-python.git",     "t",  None,                                "tests"),
    ("https://github.com/elastic/elasticsearch-dsl-py.git", "t", None,                            "tests"),
    ("https://github.com/marshmallow-code/marshmallow.git", "t", None,                            "tests"),
    ("https://github.com/py-pdf/pypdf.git",            "rt", "requirements/dev.txt",              "tests"),
    ("https://github.com/lektor/lektor.git",           "t",  None,                                "tests"),
    ("https://github.com/celery/celery.git",           "rt", "requirements/test.txt",             "t"),
    ("https://github.com/pallets/jinja.git",           "t",  None,                                "tests"),
    ("https://github.com/pytest-dev/pytest.git",       "t",  None,                                "testing"),
    ("https://github.com/rspeer/python-ftfy.git",      "t",  None,                                "tests"),
    ("https://github.com/gruns/furl.git",              "t",  None,                                "tests"),
    ("https://github.com/Zulko/moviepy.git",           "t",  None,                                "tests"),
    ("https://github.com/miracle2k/webassets.git",     "rt", "requirements-dev.pip",              "tests"),
    ("https://github.com/Alir3z4/html2text.git",       "t",  None,                                "test"),
    ("https://github.com/aaugustin/websockets.git",    "t",  None,                                "tests"),
    ("https://github.com/benoitc/gunicorn.git",        "rt", "requirements_dev.txt",              "tests"),
    ("https://github.com/django/channels.git",         "t",  None,                                "tests"),
    ("https://github.com/stephenmcd/mezzanine.git",    "t",  None,                                "tests"),
    ("https://github.com/scottrogowski/code2flow.git", "t",  None,                                "tests"),
    ("https://github.com/paramiko/paramiko.git",       "t",  None,                                "tests"),
    ("https://github.com/Pylons/colander.git",         "t",  None,                                "tests"),
    ("https://github.com/patx/pickledb.git",           "t",  None,                                "./tests.py"),
    ("https://github.com/libvips/pyvips.git",          "t",  None,                                "tests"),
    ("https://github.com/hynek/structlog.git",         "t",  None,                                "tests"),
]

# Source directories to instrument (from dynapyt_instrument_src.txt)
# Maps project_name -> list of (flag, path) where flag is "d" (directory) or "f" (file)
SOURCE_DIRS = {
    "grab":              [("d", "./grab")],
    "PythonRobotics":    [("d", "./AerialNavigation"), ("d", "./ArmNavigation"), ("d", "./Bipedal"), ("d", "./Control"), ("d", "./Localization"), ("d", "./Mapping"), ("d", "./PathPlanning"), ("d", "./PathTracking"), ("d", "./SLAM"), ("d", "./utils")],
    "flask-api":         [("d", "./flask_api/static"), ("d", "./flask_api/templates"), ("f", "./flask_api/app.py"), ("f", "./flask_api/compat.py"), ("f", "./flask_api/decorators.py"), ("f", "./flask_api/exceptions.py"), ("f", "./flask_api/mediatypes.py"), ("f", "./flask_api/negotiation.py"), ("f", "./flask_api/parsers.py"), ("f", "./flask_api/renderers.py"), ("f", "./flask_api/request.py"), ("f", "./flask_api/response.py"), ("f", "./flask_api/settings.py"), ("f", "./flask_api/status.py")],
    "schedule":          [("d", "./schedule")],
    "Pillow":            [("d", "./src")],
    "supervisor":        [("d", "./supervisor")],
    "streamparse":       [("d", "./streamparse")],
    "dh-virtualenv":     [("d", "./dh_virtualenv")],
    "pdoc":              [("d", "./pdoc")],
    "click":             [("d", "./src")],
    "delegator.py":      [("f", "./delegator.py")],
    "python-patterns":   [("d", "./patterns")],
    "uvicorn":           [("d", "./uvicorn")],
    "pydub":             [("d", "./pydub")],
    "pyjwt":             [("d", "./jwt")],
    "cerberus":          [("d", "./cerberus")],
    "python-diskcache":  [("d", "./diskcache")],
    "errbot":            [("d", "./errbot"), ("d", "./tools")],
    "black":             [("d", "./src")],
    "thefuck":           [("d", "./thefuck")],
    "python-future":     [("d", "./src")],
    "python-decouple":   [("f", "./decouple.py")],
    "arrow":             [("d", "./arrow")],
    "pudb":              [("d", "./pudb")],
    "akshare":           [("d", "./akshare")],
    "seaborn":           [("d", "./seaborn")],
    "pyfilesystem2":     [("d", "./fs")],
    "wtforms":           [("d", "./src/wtforms")],
    "funcy":             [("d", "./funcy")],
    "graphene":          [("d", "./graphene")],
    "geopy":             [("d", "./geopy")],
    "pyquery":           [("d", "./pyquery")],
    "requests":          [("d", "./requests")],
    "scikit-learn":      [("d", "./sklearn")],
    "blinker":           [("d", "./blinker")],
    "zerorpc-python":    [("d", "./zerorpc")],
    "elasticsearch-dsl-py": [("d", "./elasticsearch_dsl")],
    "marshmallow":       [("d", "./src/marshmallow")],
    "pypdf":             [("d", "./pypdf")],
    "lektor":            [("d", "./lektor")],
    "celery":            [("d", "./celery")],
    "jinja":             [("d", "./src/jinja2")],
    "pytest":            [("d", "./src")],
    "python-ftfy":       [("d", "./ftfy")],
    "furl":              [("d", "./furl")],
    "moviepy":           [("d", "./moviepy")],
    "webassets":         [("d", "./src/webassets")],
    "html2text":         [("d", "./html2text")],
    "websockets":        [("d", "./src/websockets")],
    "gunicorn":          [("d", "./gunicorn")],
    "channels":          [("d", "./channels")],
    "mezzanine":         [("d", "./mezzanine")],
    "code2flow":         [("d", "./code2flow")],
    "paramiko":          [("d", "./paramiko")],
    "colander":          [("d", "./src/colander")],
    "pickledb":          [("f", "./pickledb.py")],
    "pyvips":            [("d", "./pyvips")],
    "structlog":         [("d", "./src/structlog")],
}


def get_project_name(url):
    return url.rstrip("/").split("/")[-1].replace(".git", "")


def get_source_directories(name):
    """Get only the directory-type source paths for instrumentation."""
    entries = SOURCE_DIRS.get(name, [])
    dirs = [path.lstrip("./") for flag, path in entries if flag == "d"]
    if not dirs:
        # Fall back: use the package-style name (lowercase, dash->underscore)
        dirs = [name.lower().replace("-", "_")]
    return dirs


def generate_workflow(project_no):
    idx = project_no - 1
    if idx < 0 or idx >= len(PROJECTS):
        print(f"Error: project number must be between 1 and {len(PROJECTS)}")
        sys.exit(1)

    url, flags, req_file, test_dir = PROJECTS[idx]
    name = get_project_name(url)
    src_dirs = get_source_directories(name)

    # Build install block lines (each will be indented at 14 spaces in YAML)
    indent = "          "  # 10 spaces for YAML run block
    install_cmds = ["pip install --upgrade pip"]
    if req_file:
        install_cmds.append(f'[ -f "{req_file}" ] && pip install -r "{req_file}" || true')
    install_cmds.extend([
        'if [ -f pyproject.toml ] || [ -f setup.py ] || [ -f setup.cfg ]; then',
        '  pip install -e ".[dev,test,tests]" 2>/dev/null || pip install -e "." 2>/dev/null || true',
        'fi',
    ])
    install_block = ("\n" + indent).join(install_cmds)

    workflow = f"""\
# Auto-generated DynaPyt workflow for {name} (DyPyBench #{project_no})
# Source: {url}
#
# Drop this file into .github/workflows/dynapyt.yml in your fork.
# Then push and go to Actions -> "DynaPyt Analysis" -> "Run workflow".

name: DynaPyt Analysis

on:
  push:
    branches: [main, master]
  pull_request:
  workflow_dispatch:
    inputs:
      analysis:
        description: "DynaPyt analysis class"
        default: "dynapyt.analyses.CallGraph.CallGraph"
        type: string

jobs:
  dynapyt:
    runs-on: ubuntu-latest
    timeout-minutes: 60

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.10"

      - name: Install project dependencies
        run: |
          {install_block}

      - name: Setup DynaPyt
        uses: clonedSemicolon/seytup-dynapyt@master
        with:
          directory: "{src_dirs[0]}"
          analysis: ${{{{ inputs.analysis || 'dynapyt.analyses.CallGraph.CallGraph' }}}}

      - name: Run tests
        run: |
          pytest --timeout=120 --import-mode=importlib {test_dir} || true

      - name: Collect DynaPyt output
        if: always()
        run: |
          python -m dynapyt.post_run --output_dir=dynapyt-output 2>/dev/null || true
          echo "=== DynaPyt output files ==="
          find dynapyt-output/ -type f 2>/dev/null | head -50 || echo "No output files"

      - name: Upload DynaPyt artifacts
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: dynapyt-{name}
          path: dynapyt-output/
          retention-days: 30
"""
    return workflow, name, url


def list_projects():
    print(f"{'#':<4} {'Project':<25} {'Source Dirs':<30} {'Test Dir':<20} URL")
    print("-" * 120)
    for i, (url, flags, req, test_dir) in enumerate(PROJECTS, 1):
        name = get_project_name(url)
        src = ",".join(get_source_directories(name))
        print(f"{i:<4} {name:<25} {src:<30} {test_dir:<20} {url}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate a DynaPyt CI workflow for any DyPyBench project."
    )
    parser.add_argument("--project", "-p", type=int, help="DyPyBench project number (1-58)")
    parser.add_argument("--list", "-l", action="store_true", help="List all projects")
    parser.add_argument("--output", "-o", type=str, help="Output file path (default: print to stdout)")
    parser.add_argument("--clone", action="store_true", help="Clone the repo, add workflow, and commit")
    parser.add_argument("--push", action="store_true", help="Push after committing (implies --clone)")
    parser.add_argument("--fork-org", type=str, default=None, help="GitHub org/user to fork to (uses gh cli)")
    parser.add_argument("--workdir", type=str, default=".", help="Directory to clone repos into")

    args = parser.parse_args()

    if args.list:
        list_projects()
        return

    if not args.project:
        parser.print_help()
        return

    workflow, name, url = generate_workflow(args.project)

    if args.clone or args.push:
        repo_dir = os.path.join(args.workdir, name)

        # Fork if requested
        if args.fork_org:
            print(f"Forking {url} to {args.fork_org}...")
            subprocess.run(["gh", "repo", "fork", url, "--org", args.fork_org, "--clone=false"], check=True)

        # Clone
        if not os.path.isdir(repo_dir):
            print(f"Cloning {url} into {repo_dir}...")
            subprocess.run(["git", "clone", "--depth", "1", url, repo_dir], check=True)
        else:
            print(f"Using existing clone at {repo_dir}")

        # Write workflow
        wf_dir = os.path.join(repo_dir, ".github", "workflows")
        os.makedirs(wf_dir, exist_ok=True)
        wf_path = os.path.join(wf_dir, "dynapyt.yml")
        with open(wf_path, "w", newline="\n", encoding="utf-8") as f:
            f.write(workflow)
        print(f"Wrote {wf_path}")

        # Commit
        subprocess.run(["git", "add", ".github/workflows/dynapyt.yml"], cwd=repo_dir, check=True)
        subprocess.run(
            ["git", "commit", "-m", f"ci: add DynaPyt dynamic analysis workflow (DyPyBench #{args.project})"],
            cwd=repo_dir, check=True
        )
        print("Committed.")

        # Push
        if args.push:
            subprocess.run(["git", "push"], cwd=repo_dir, check=True)
            print("Pushed.")
        else:
            print(f"Ready to push. Run: cd {repo_dir} && git push")

    elif args.output:
        with open(args.output, "w", newline="\n", encoding="utf-8") as f:
            f.write(workflow)
        print(f"Wrote workflow to {args.output}")
    else:
        print(workflow)


if __name__ == "__main__":
    main()
