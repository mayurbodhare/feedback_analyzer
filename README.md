# Feedback Analyzer

A feedback analysis application built with FastAPI, Celery, and Redis.

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.8+**
- **Docker** (for Redis)
- **Git**

## Installation & Setup

### Linux / macOS

#### 1. Clone the Repository

```bash
git clone https://github.com/mayurbodhare/feedback_analyzer.git
cd feedback_analyzer
```

#### 2. Install Poetry

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

Add Poetry to your PATH (if needed):
```bash
export PATH="$HOME/.local/bin:$PATH"
```

#### 3. Install Project Dependencies

```bash
poetry install
```

#### 4. Activate Virtual Environment

```bash
source $(poetry env info --path)/bin/activate
```

#### 5. Start Redis with Docker

```bash
docker run -d --name redis-stack -p 6379:6379 -p 8001:8001 redis/redis-stack:latest
```

Verify Redis is running:
```bash
docker ps
```

#### 6. Start Celery Worker

Open a new terminal, activate the virtual environment, and run:

```bash
source $(poetry env info --path)/bin/activate
celery -A celery_worker.celery_app worker --pool=solo --loglevel=info
```

#### 7. Start the FastAPI Application

Open another terminal, activate the virtual environment, and run:

```bash
source $(poetry env info --path)/bin/activate
uvicorn main:app --reload
```

The application will be available at: `http://localhost:8000`

---

### Windows

#### 1. Clone the Repository

```powershell
git clone https://github.com/mayurbodhare/feedback_analyzer.git
cd feedback_analyzer
```

#### 2. Install Poetry

```powershell
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
```

Add Poetry to your PATH:
- Press `Win + X` and select "System"
- Click "Advanced system settings"
- Click "Environment Variables"
- Add `%APPDATA%\Python\Scripts` to your PATH

Restart your terminal after updating PATH.

#### 3. Install Project Dependencies

```powershell
poetry install
```

#### 4. Activate Virtual Environment

```powershell
poetry shell
```

#### 5. Start Redis with Docker

```powershell
docker run -d --name redis-stack -p 6379:6379 -p 8001:8001 redis/redis-stack:latest
```

Verify Redis is running:
```powershell
docker ps
```

#### 6. Start Celery Worker

Open a new terminal (PowerShell or Command Prompt), activate the virtual environment, and run:

```powershell
poetry shell
celery -A celery_worker.celery_app worker --pool=solo --loglevel=info
```

**Note:** On Windows, you may need to use the `--pool=solo` flag as shown above.

#### 7. Start the FastAPI Application

Open another terminal, activate the virtual environment, and run:

```powershell
poetry shell
uvicorn main:app --reload
```

The application will be available at: `http://localhost:8000`

---

## Accessing the Application

- **API Docs (Swagger UI):** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
- **Redis Insight:** `http://localhost:8001` (for monitoring Redis)

## Stopping the Application

### Stop FastAPI and Celery
Press `Ctrl + C` in the respective terminal windows.

### Stop Redis Container

```bash
docker stop redis-stack
```

### Remove Redis Container (optional)

```bash
docker rm redis-stack
```

## Troubleshooting

### Poetry not found after installation
Make sure Poetry is added to your PATH. Restart your terminal or add the Poetry bin directory to your PATH manually.

### Docker connection issues
Ensure Docker Desktop is running (Windows/Mac) or Docker daemon is active (Linux).

### Port already in use
If port 8000, 6379, or 8001 is already in use, you can:
- Stop the application using that port
- Modify the port in the run commands (e.g., `uvicorn main:app --reload --port 8080`)

### Celery worker issues on Windows
Windows has limited support for Celery. Always use `--pool=solo` flag. For production on Windows, consider using WSL2 (Windows Subsystem for Linux).

## Development

To add new dependencies:

```bash
poetry add package-name
```

To add development dependencies:

```bash
poetry add --group dev package-name
```

## License

MIT License

## Contributing

Follow the best practices for code readability and scalability.
## Contact

For issues and questions, please open an issue on the [GitHub repository](https://github.com/mayurbodhare/feedback_analyzer/issues).