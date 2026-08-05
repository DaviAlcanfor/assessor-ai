set windows-shell := ["powershell.exe", "-NoLogo", "-NoProfile", "-Command"]
cmd := "assessor-ai"
python := if os() == "windows" { ".venv/Scripts/python" } else { ".venv/bin/python" }

venv:
    @echo "Preparing python environment"
    python -m venv .venv

dev mode="terminal":
    @echo "Getting environment variables / infisical"
    infisical run -- {{cmd}} {{mode}}

run mode="terminal":
    @echo "Running the application"
    {{cmd}} {{mode}}

check:
    @echo "Running pre-commit checks"
    ruff check

fix:
    @echo "Running pre-commit fixes"
    ruff check --fix

test:
    @echo "Running tests"
    {{python}} -m pytest