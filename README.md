# BUS Backend

Postgres Database introspection and query tool.

## Prerequisites/

- Python 3.8 or higher
- PostgreSQL
- UV (Python package installer)

## Installation

1. Clone the repository

```bash
git clone https://github.com/samson4/bus-backend.git
cd bus-backend
```

2. intsall uv

```bash
pip install uv

#create vitrual environment
uv venv

#activate virtual environment
source venv/bin/activate
```

# Environment Setup

Create a .env file in the root directory
Add the following environment variables:

1. Database Configuration

```
DB_HOST=localhost
DATABASE=postgres
DB_USER=postgres
DB_PASSWORD=postgres
DB_PORT=5432
```

2. Authentication

```
SECRET_KEY="secretkey"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

# Running the Application

Start the FastAPI server:

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at http://localhost:8000

# Available endpoints

1. http://localhost:8000/docs/
2. http://localhost:8000/redoc/
3. http://localhost:8000/schemas/
4. http://localhost:8000/tables/?schema=yourschemaname
5. http://localhost:8000/columns/?table=yourtablename
6. http://localhost:8000/data/?schema=yourschemaname&table=yourtablename

# Code Quality

We use Ruff for code formatting and linting. To format your code:

```bash
#Fix formatting issues
uv run ruff check --fix

# Format code
uv run ruff format
```

# Contributing

1. Fork the repository
2. Create your feature branch (git checkout -b feature/NewFeature)
3. Commit your changes (git commit -m 'Add some New Feature')
4. Push to the branch (git push origin feature/NewFeature)
5. Open a Pull Request

# License

This project is licensed under the MIT - see the LICENSE.md file for details
