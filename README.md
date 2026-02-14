# Over-Bet Cash Game Tracker

The app lets you track your cash game stats and share them with your team.

## Quick Start (Docker - Recommended)

The easiest way to run the application is using Docker:

```bash
# 1. Configure environment
cp .env.docker.template .env.docker
# Edit .env.docker with your credentials

# 2. Start everything
docker-compose up -d

# 3. Access the app
# Visit http://localhost:8000 (or port 80 for production deployment)
```

The Docker setup includes:
- PostgreSQL 15 database (isolated, with persistent storage)
- FastAPI application with Gunicorn
- Automatic database initialization

## Local Development

### Prerequisites
- Python 3.10+
- Poetry
- PostgreSQL 15+ (for local development only)

### Setup

1. **Configure Database**
   
   The app uses a PostgreSQL database. For local development, you can either:
   
   **Option A: Use Docker database (recommended)**
   ```bash
   # Start just the database
   docker-compose up -d db
   
   # Database will be available at localhost:5434
   ```
   
   **Option B: Install PostgreSQL locally**
   - Install PostgreSQL 15+
   - Create a database and user
   - Update `.env` with your credentials

2. **Configure Email** (Optional)
   
   Create a [Resend](https://resend.com) account and get an API key for email verification.

3. **Update Environment Variables**
   
   ```bash
   # Copy template
   cp .env_template .env
   
   # Edit .env with your settings:
   # - Database credentials
   # - Email API key (optional)
   # - JWT secret key
   ```

4. **Install Dependencies**
   
   ```bash
   poetry install
   ```

5. **Initialize Database**
   
   ```bash
   # Create database schema
   poetry run python backend/db/tools/reset_db.py create
   ```

### Running Locally

**Windows:**
```bash
just start_local
```

**Linux:**
```bash
make start_local
```

The app will be available at `http://localhost:8000`

## Production Deployment

### Docker Deployment (Recommended)

```bash
# 1. Update configuration
cp .env.docker.template .env.docker
# Edit .env.docker with production settings

# 2. Deploy
docker-compose up -d

# 3. View logs
docker-compose logs -f
```

### Manual Deployment

Update your production `.env` with the appropriate database host and credentials, then:

```bash
make start
```

## Configuration

### Environment Variables

Key environment variables in `.env`:

```bash
# Database
POSTGRES_USER=admin
POSTGRES_PASSWORD=your_password
POSTGRES_SERVER=localhost  # or 'db' when running in Docker
POSTGRES_PORT=5434         # 5434 for Docker, 5432 for local PostgreSQL
POSTGRES_DB=cashgame_tracker

# JWT Security
SECRET_KEY=your_secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=600

# Email (Optional - for user verification)
MAIL_USERNAME=resend
MAIL_PASSWORD=your_resend_api_key
MAIL_FROM=noreply@your-domain.com
MAIL_SERVER=smtp.resend.com
MAIL_PORT=587

# Google OAuth (Optional)
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
GOOGLE_REDIRECT_URI=https://your-domain.com/auth/google/callback
```

## Database Management

Reset the database (WARNING: Deletes all data):
```bash
poetry run python backend/db/tools/reset_db.py reset
```

Create tables only:
```bash
poetry run python backend/db/tools/reset_db.py create
```

## Project Structure

```
cash_game_tracker/
├── backend/
│   ├── core/           # Configuration
│   ├── db/             # Database models and session
│   ├── templates/      # HTML templates
│   ├── webapps/        # Route handlers
│   └── public/         # Static files
├── scripts/            # Utility scripts
├── docs/               # Documentation
├── docker-compose.yml  # Docker configuration
├── Dockerfile          # Application container
└── main.py             # Application entry point
```

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy
- **Database**: PostgreSQL 15
- **Frontend**: Jinja2 templates, HTMX
- **Deployment**: Docker, Gunicorn + Uvicorn workers

## License

MIT