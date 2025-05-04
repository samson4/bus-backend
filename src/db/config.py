from decouple import config as decouple_config


host = decouple_config("DB_HOST", "localhost")
database = decouple_config("DATABASE", "postgres")
user = decouple_config("DB_USER", "postgres")
password = decouple_config("DB_PASSWORD", "postgres")
port = decouple_config("DB_PORT", "5432")
DATABASE_URL = f"postgresql+psycopg2://{user}:{password}@{host}/{database}"
