from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from starlette.status import HTTP_303_SEE_OTHER
from fastapi.templating import Jinja2Templates
from passlib.context import CryptContext
from app.models import User
from app.database import get_db

# Initialize Jinja2 templates
templates = Jinja2Templates(directory="app/templates")

# Initialize FastAPI router and password hashing context
router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Login page (GET request to display login form)
@router.get("/login")
async def login_page(request: Request):
    """
    Render the login page where users can enter their credentials.
    """
    return templates.TemplateResponse("login.html", {"request": request})

# Login handler (POST request to authenticate user)
@router.post("/login")
async def login(
    db: Session = Depends(get_db),
    username: str = Form(...),
    password: str = Form(...),
):
    """
    Handle user login by validating credentials.
    """
    # Check if the user exists
    user = db.query(User).filter(User.username == username).first()
    if not user or not pwd_context.verify(password, user.password):
        raise HTTPException(status_code=400, detail="Invalid username or password.")

    # Redirect to dashboard and set user_id cookie
    response = RedirectResponse(url="/dashboard", status_code=HTTP_303_SEE_OTHER)
    response.set_cookie(key="user_id", value=user.id, httponly=True)
    return response

# Signup page (GET request to display signup form)
@router.get("/signup")
async def signup_page(request: Request):
    """
    Render the signup page where users can create an account.
    """
    return templates.TemplateResponse("signup.html", {"request": request})

# Signup handler (POST request to register a new user)
@router.post("/signup")
async def signup(
    db: Session = Depends(get_db),
    username: str = Form(...),
    password: str = Form(...),
):
    """
    Handle user registration by creating a new user in the database.
    """
    # Check if the username already exists
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="Username already exists. Please choose another.")

    # Hash the password and create a new user
    hashed_password = pwd_context.hash(password)
    new_user = User(username=username, password=hashed_password)
    db.add(new_user)
    db.commit()

    # Redirect to login page after successful signup
    return RedirectResponse(url="/login", status_code=HTTP_303_SEE_OTHER)

# Logout handler (GET request to log out user)
@router.get("/logout")
async def logout():
    """
    Log the user out by clearing the user_id cookie and redirecting to the login page.
    """
    response = RedirectResponse(url="/login", status_code=HTTP_303_SEE_OTHER)
    response.delete_cookie("user_id")
    return response
