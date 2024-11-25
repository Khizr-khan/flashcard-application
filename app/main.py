from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.database import Base, engine
from app.routes import auth, flashcards

# Create tables when the application starts
Base.metadata.create_all(bind=engine)

# Initialize the FastAPI application
app = FastAPI(title="FlashCard App", description="Manage flashcards with user authentication", version="1.0")

# Mount the static files directory (for CSS, JS, images, etc.)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Set up Jinja2 templates
templates = Jinja2Templates(directory="app/templates")

# Include the authentication and flashcard management routers
app.include_router(auth.router, tags=["Authentication"])
app.include_router(flashcards.router, tags=["Flashcards"])

# Root endpoint: Redirect to login page or dashboard
@app.get("/")
async def root(request: Request):
    user_id = request.cookies.get("user_id")
    if user_id:
        # Redirect to dashboard if user is already logged in
        return RedirectResponse(url="/dashboard")
    # Otherwise, show the login page
    return templates.TemplateResponse("login.html", {"request": request})
