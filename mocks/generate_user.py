from faker import Faker

fake = Faker()

def generate_user() -> dict:
    return {
        "name": fake.name(),
        "email": fake.email()
    }