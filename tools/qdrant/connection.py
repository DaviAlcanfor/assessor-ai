from qdrant_client import AsyncQdrantClient
from config.settings import settings


async def get_qdrant_client():
    client = AsyncQdrantClient(
        url=settings.QDRANT_CLUSTER_ENDPOINT,
        api_key=settings.QDRANT_API_KEY
    )

    try:
        yield client 
    finally:
        await client.close()