Run the project with
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload

Run Ruff formatter(linter)
uv run ruff check --fix
uv run ruff format

Example .env file

DB_HOST=localhost
DATABASE=postgres
DB_USER=postgres
DB_PASSWORD=postgres
DB_PORT=5432

SECRET_KEY = "90ded69acb971f4f6f9a6913428503503eac012275cd9f2b13c37a0ba43f35c6"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
