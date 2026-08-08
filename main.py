import os
from fastapi import FastAPI, Header, HTTPException, Depends
from pydantic import BaseModel
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY in .env")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title="Auth API", description="Secure API with Supabase Auth")

# ----- Pydantic models for request bodies -----
class SignUpRequest(BaseModel):
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

# ----- Root endpoint (optional) -----
@app.get("/")
def read_root():
    return {"message": "Welcome to the Auth API"}

# ----- Signup endpoint (required) -----
@app.post("/auth/signup", status_code=201)
def signup(user_data: SignUpRequest):
    # Validate input
    if not user_data.email or not user_data.password:
        raise HTTPException(status_code=400, detail="Email and password are required")
    
    try:
        response = supabase.auth.sign_up({
            "email": user_data.email,
            "password": user_data.password
        })
    except Exception as e:
        # Supabase may raise exceptions for duplicate email, etc.
        raise HTTPException(status_code=400, detail=str(e))
    
    # Check if user creation succeeded
    if response.user is None:
        # Sometimes Supabase returns an error in response
        raise HTTPException(status_code=400, detail="Signup failed")
    
    return {"user": response.user.model_dump()}

# ----- Login endpoint (required) -----
@app.post("/auth/login")
def login(user_data: LoginRequest):
    if not user_data.email or not user_data.password:
        raise HTTPException(status_code=400, detail="Email and password are required")

# ----- Public endpoint (required) -----
@app.get("/public/info")
def public_info():
    return {"message": "Welcome stranger! This info is public."}

# ----- Protected endpoint (required) -----
@app.get("/protected/profile")
def protected_profile(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Access token required")
    
    # Expecting "Bearer <token>"
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid Authorization header format")
    
    token = parts[1]
    if not token:
        raise HTTPException(status_code=401, detail="Access token required")
    
    # For now, just return a placeholder (we'll verify in Stage 3)
    return {"message": "You have a token, but I haven't verified it yet", "token": token}

    try:
        response = supabase.auth.sign_in_with_password({
            "email": user_data.email,
            "password": user_data.password
        })
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid login credentials")
    
    if response.user is None:
        raise HTTPException(status_code=401, detail="Invalid login credentials")
    
    # Return access token and refresh token
    return {
        "access_token": response.session.access_token,
        "refresh_token": response.session.refresh_token,
        "user": response.user.model_dump()
    }