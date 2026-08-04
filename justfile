set positional-arguments := true
cmd := "assessor-ai"

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