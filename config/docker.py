import subprocess
import atexit

from config.logging import get_logger


logger = get_logger("docker")

CONTAINER_NAME = "PostGreSQL"


def _encerrar_banco():
    
    logger.info("Encerrando container %s...", CONTAINER_NAME)
    subprocess.run(["docker", "stop", CONTAINER_NAME], check=True)
    logger.info("Container %s encerrado.", CONTAINER_NAME)


def garantir_banco() -> None:

    resultado = subprocess.run(
        ["docker", "ps", "--filter", f"name={CONTAINER_NAME}", "--format", "{{.Names}}"],
        capture_output=True,
        text=True
    )

    if CONTAINER_NAME in resultado.stdout:
        logger.info("Container %s já está rodando.", CONTAINER_NAME)
        return

    logger.info("Subindo container %s...", CONTAINER_NAME)
    subprocess.run(["docker", "start", CONTAINER_NAME], check=True)
    logger.info("Container %s pronto.", CONTAINER_NAME)
    
    # quando o app fecha, desliga o container
    atexit.register(_encerrar_banco)
