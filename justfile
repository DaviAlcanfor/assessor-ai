set windows-shell := ["powershell.exe", "-NoLogo", "-NoProfile", "-Command"]
cmd := "assessor-ai"
python := if os() == "windows" { ".venv/Scripts/python" } else { ".venv/bin/python" }

venv:
    @echo "Preparing python environment"
    python -m venv .venv

dev mode="tui":
    @echo "Getting environment variables / infisical"
    infisical run -- {{cmd}} {{mode}}

run mode="tui":
    @echo "Running the application"
    {{cmd}} {{mode}}

api:
    @echo "Running the API locally (localhost:8000, auth por API key desligada — pareia com just web)"
    $env:API_KEY_AUTH_ENABLED = "false"; just run api

front:
    @echo "Running the frontend dev server (proxy pra API em localhost:8000)"
    cd web; npm run dev

web:
    @echo "Abrindo 'just api' e 'just front' em janelas separadas"
    Start-Process powershell -ArgumentList '-NoExit','-Command','just api' -WorkingDirectory '{{justfile_directory()}}'
    Start-Process powershell -ArgumentList '-NoExit','-Command','just front' -WorkingDirectory '{{justfile_directory()}}'

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