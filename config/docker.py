import subprocess

from config.logging import get_logger

logger = get_logger("docker")

def _compose(command: list[str]) -> None:
    subprocess.run(["docker", "compose"] + command, check=True)

def garantir_ambiente() -> None:
    """
    Sobe todos os serviços definidos no docker-compose.yml
    caso ainda não estejam rodando.
    """
    try:
        result = subprocess.run(
            ["docker", "compose", "ps", "--format", "{{.Name}}"],
            capture_output=True,
            text=True,
            check=False,
        )
        running = result.stdout.strip().splitlines()

        if all(
            name in running
            for name in [
                "assessor-postgres",
                "assessor-mongo",
                "assessor-redis",
                "assessor-qdrant",
            ]
        ):
            logger.info("Ambiente Docker ja esta rodando.")
            return

    except FileNotFoundError:
        logger.error("Docker nao encontrado.")
        raise

    logger.info("Subindo ambiente Docker...")
    _compose(["up", "-d", "--wait"])


def encerrar_ambiente() -> None:
    logger.info("Encerrando ambiente Docker...")
    _compose(["down"])