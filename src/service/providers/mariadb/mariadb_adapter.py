from sqlalchemy import create_engine as create_engine
from .mariadb_seed import Seed
class MariaDBAdapter:
    def __init__(self):
        self.connection = None
        self.host = None
        self.database = None
        self.user = None
        self.password = None
        self.port = None
        self.extras = 'charset=utf8mb4&collation=utfmb4_general_ci'
        self.dialect = "mariadb"
        self.database_url = None
        self.connector = "mariadbconnector"

        

    def set_connection(self, database_url):
        # Logic to set the MARIADB connection using the provided URL
        # self.database_url = database_url.
        # database_url is Dict format {
        #     "host": self.host,
        #     "database": self.database,
        #     "user": self.user,
        #     "password": self.password,
        #     "port": self.port,
        #     "extras": self.extras,
        #     "dialect": self.dialect,
        #     "database_url": self.database_url
        # }
        # example connection string for mariadb: "mariadb+mariadbconnector://<user>:<password>@<host>[:<port>]/<dbname>?charset=utf8mb4&collation=utfmb4_general_ci"
        self.database = database_url.get("database")
        self.host = database_url.get("host")
        self.user = database_url.get("user")
        self.password = database_url.get("password")
        self.port = database_url.get("port", 3306)  # Default MARIADB port is 3306
        self.extras = database_url.get("extras")
        self.dialect = database_url.get("dialect", "mariadb")
        
        

    def get_connection_string(self):
        if not self.database or not self.host or not self.user or not self.password:
            raise ValueError("Database connection parameters are not set.")
        
        return f"{self.dialect}+{self.connector}://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}?{self.extras}"   


    def create_connection(self):
        try:
            # from src.models import  SchemaMetadata, ColumnMetadata, TableMetadata
            # Logic to create a MARIADB connection
            self.connection = create_engine(self.get_connection_string())
            print("mysql connection", self.connection)
        
            
            # SchemaMetadata.metadata.create_all(bind=self.connection)
            # ColumnMetadata.metadata.create_all(bind=self.connection)
            # TableMetadata.metadata.create_all(bind=self.connection)
        except Exception as e:
            print("Error creating tables:", e)
            raise e

    def initialize_metadata(self, project_id):
       
        # Logic to initialize metadata for the project
        seed_data = Seed(project_id=project_id, adapter=self.connection)
        seed_data.insert_metadata()
            

    def close_connection(self):
        # Logic to close the MySQL connection
        if self.connection:
            self.connection.dispose()
            self.connection = None
        else:
            raise ValueError("No active connection to close.")
        
        


mariadb_adapter = MariaDBAdapter()   