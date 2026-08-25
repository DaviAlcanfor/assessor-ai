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

api:
    @echo "Running the API locally (localhost:8000)"
    just run api

web:
    @echo "Running the frontend dev server (proxy pra API em localhost:8000)"
    cd web; npm run dev

check:
    @echo "Running pre-commit checks"
    ruff check

fix:
    @echo "Running pre-commit fixes"
    ruff check --fix

test:
    @echo "Running tests"
    {{python}} -m pytest

deploy:
    @echo "Deploying the application"
    fastapi deploy