set positional-arguments := true
cmd := "assessor-ai"

dev mode="terminal":
    infisical run -- {{cmd}} {{mode}}
    @echo "Getting environment variables / infisical"

run mode="terminal":
    {{cmd}} {{mode}}
    @echo "Running the application"