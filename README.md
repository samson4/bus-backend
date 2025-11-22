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

## Makefile Commands

The `Makefile` provides the following commands:

- **Setup:**

  - `make install`: Install dependencies.
  - `make build`: Build Docker images.

- **Development:**

  - `make dev`: Start the development environment.
  - `make up`: Start services.
  - `make down`: Stop services.
  - `make restart`: Restart services.
  - `make logs`: Show logs.
  - `make shell`: Open a shell in the API container.

- **Cleanup:**
  - `make clean`: Remove containers and volumes.

---

## Docker Setup

The project uses Docker for containerization. The `docker-compose.yml` file defines the services:

- **PostgreSQL**: Database service.
- **API**: FastAPI backend.

To start the services, run:

```bash
docker-compose up -d
```

---

## Environment Variables

The `.env.local` file contains the environment variables for the project.

```
POSTGRES_DB=bus_metadata
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=postgres_metadata
SECRET_KEY="secretkey"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=360
```

## Running the Application

Using Make file

```bash

Make up
```

Using docker-compose

```bash
docker compose -f docker-compose.yml up

```

Or running the application using uvicorn\

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

## Demo Video

Watch the demo video to see the application in action:

<video controls>
  <source src="./demo/db explore demo.webm" type="video/webm">
  Your browser does not support the video tag.
</video>

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
