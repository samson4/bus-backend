from decouple import config as decouple_config
from urllib.parse import urlparse
from ..service.providers import mysql_adapter, postgresql_adapter, postgres, mariadb, mysql
from sqlalchemy import create_engine


SUPPORTED_DATABASES = {
    "postgresql": {
        "adapter": postgres.postgresql_adapter.postgresql_adapter,
        "seed": postgres.postgresql_seed
    },
    "mysql": {
        "adapter": mysql.mysql_adapter.mysql_adapter,
        "seed": mysql.mysql_seed
    },
    "mariadb": {
        "adapter": mariadb.mariadb_adapter.mariadb_adapter,
        "seed": mariadb.mariadb_seed
    }
}
class Config:
    def __init__(self):
        self.host = None
        self.database = None
        self.user = None
        self.password = None
        self.port = None
        self.extras = None
        self.dialect = "postgresql"
        self.database_url = None
        self.adapter = None

    def validate_connection(self):
        pass

    def set_config(self, database_url: str, database_dialect: str = "postgresql"):
        """
        Set the database configuration from a database URL.

        Args:
            database_url (str): The database URL in the format
                                'dialect://user:password@host:port/database'.
        """
        parsed_url = urlparse(database_url)
        
        self.host = parsed_url.hostname
        self.database = parsed_url.path.lstrip('/')
        self.user = parsed_url.username
        self.password = parsed_url.password
        self.port = parsed_url.port if parsed_url.port else (5432 if database_dialect == "postgresql" else (3306 if database_dialect == "mysql" or database_dialect == "mariadb" else None))
        self.extras = parsed_url.query
        self.dialect = database_dialect
        self.database_url = self.get_config()
        self.adapter = None
        
        database_info = SUPPORTED_DATABASES.get(self.dialect)
        if database_info:
            self.adapter = database_info["adapter"]
            print("set connection", self.adapter)
            self.adapter.set_connection(self.get_config())
        else:
            raise ValueError(f"Unsupported database dialect: {self.dialect}")
            
        
    def get_config(self):
        """
        Get the current database configuration.

        Returns:
            Dict: A dictionary containing the database configuration.
        """
        return {
            "host": self.host,
            "database": self.database,
            "user": self.user,
            "password": self.password,
            "port": self.port,
            "extras": self.extras,
            "dialect": self.dialect,
            "database_url": self.database_url
        }    
        

host = decouple_config("DB_HOST", "localhost")
database = decouple_config("DATABASE", "postgres")
user = decouple_config("DB_USER", "postgres")
password = decouple_config("DB_PASSWORD", "postgres")
port = decouple_config("DB_PORT", "5432")
POSTGRES_DB=decouple_config("POSTGRES_DB", "bus_metadata")
POSTGRES_USER=decouple_config("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD=decouple_config("POSTGRES_PASSWORD", "postgres")
POSTGRES_HOST=decouple_config("POSTGRES_HOST", "localhost")
POSTGRES_PORT=decouple_config("POSTGRES_PORT", "5432")
DATABASE_URL = decouple_config(
    "DATABASE_URL", f"postgresql+psycopg2://{user}:{password}@{host}/{database}"
)
METADATA_DATABASE_URL = f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{port}/{POSTGRES_DB}"
engine = create_engine(DATABASE_URL)
metadata_engine = create_engine(METADATA_DATABASE_URL)
config = Config()
