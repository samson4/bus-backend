# BUS Backend

Postgres & MySql Database introspection and query tool.

## Prerequisites

- Python 3.8 or higher
- PostgreSQL or MySQL
- UV (Python package installer)

## Installation

1. Clone the repository:

```bash
git clone https://github.com/samson4/bus-backend.git
cd bus-backend
```

2. Install `uv`:

```bash
pip install uv

# Create a virtual environment
uv venv

# Activate the virtual environment
source venv/bin/activate
```

## Environment Setup

Create a `.env` file in the root directory and add the following environment variables:

1. **Authentication Configuration**:

```
SECRET_KEY="secretkey"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

2. **Database Configuration**:

You no longer need to add the database connection string in the `.env` file. Instead, when creating a new project, you will provide the database type (PostgreSQL or MySQL) from a dropdown and then input the connection string directly in the project creation form.

## Running the Application

Start the FastAPI server:

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at [http://localhost:8000](http://localhost:8000).

## Available Endpoints

### Authentication
1. **Login**: `POST /token`  
   - Authenticate and retrieve an access token.

2. **Register**: `POST /register`  
   - Register a new user.

### Projects
3. **Get User Projects**: `GET /projects`  
   - Retrieve all projects for the current user.

4. **Create New Project**: `POST /project/new`  
   - Create a new project by providing the database type and connection string.

5. **Select Project**: `GET /project/select/{project_id}`  
   - Select a project and set the database connection to the selected project's database.

### Database Metadata
6. **Get Schemas**: `GET /schemas/`  
   - Retrieve schemas for the selected project.

7. **Get Tables**: `GET /tables/`  
   - Retrieve tables for a specific schema.

8. **Get Columns**: `GET /columns/`  
   - Retrieve columns for a specific table.

9. **Get Data**: `GET /data/`  
   - Retrieve data from a specific table in a schema.

### Documentation
10. **Swagger UI**: [http://localhost:8000/docs/](http://localhost:8000/docs/)  
11. **ReDoc**: [http://localhost:8000/redoc/](http://localhost:8000/redoc/)

## Code Quality

We use Ruff for code formatting and linting. To format your code:

```bash
# Fix formatting issues
uv run ruff check --fix

# Format code
uv run ruff format
```

## Contributing

1. Fork the repository.
2. Create your feature branch (`git checkout -b feature/NewFeature`).
3. Commit your changes (`git commit -m 'Add some New Feature'`).
4. Push to the branch (`git push origin feature/NewFeature`).
5. Open a Pull Request.

## License

This project is licensed under the MIT License - see the `LICENSE.md` file for details.
