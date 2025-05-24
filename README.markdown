Chat App

A simple chat application built with FastAPI, WebSocket, and PostgreSQL.

Prerequisites

- Docker
- Docker Compose

Setup and Running

1. Clone the repository:

   git clone &lt;repository_url&gt;\
   cd chat_app
2. Create a `.env` file based on `.env.example`:

   cp .env.example .env
3. Build and run the application:

   docker-compose up --build
4. Access the API at `http://localhost:8000` and Swagger UI at `http://localhost:8000/docs`.

API Examples

- **Root endpoint**: `GET /`

  curl http://localhost:8000

  Response: `{"message": "Chat App is running"}`

Creating Test Data

(TBD: Will be added after implementing database seeding)

Project Structure

- `app/` - Main application code
- `app/models/` - SQLAlchemy models
- `app/routers/` - API and WebSocket routes
- `app/services/` - Business logic
- `app/repositories/` - Database operations