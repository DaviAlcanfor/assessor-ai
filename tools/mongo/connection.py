from pymongo import MongoClient
from pymongo.database import Database


def _conectar() -> Database:
    
    # mongodb é lazy por natureza        
    cliente = MongoClient("mongodb://localhost:27017")
    return cliente["assessor_ai"]


banco = _conectar()

