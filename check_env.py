import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Read variables
print("SECRET_KEY =", os.getenv("220838d7b8826c175083b8a1d69f801fa936bda827d8c2acb569809c088d5396"))
print("DB_HOST =", os.getenv("DB_HOST"))
print("DB_USER =", os.getenv("DB_USER"))
print("DB_PASSWORD =", os.getenv("DB_PASSWORD"))
print("DB_NAME =", os.getenv("DB_NAME"))
