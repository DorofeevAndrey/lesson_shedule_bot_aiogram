from dotenv import load_dotenv
import os

load_dotenv()

TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
USER = os.getenv("POSTGRES_USER")
PASSWORD = os.getenv("POSTGRES_PASSWORD")
HOST = os.getenv("POSTGRES_HOST")
PORT = os.getenv("POSTGRES_PORT")
DB = os.getenv("POSTGRES_DB")
DB_URL = f"postgresql://{USER}:{PASSWORD}@{HOST}:{PORT}/{DB}"
