from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Body
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import List, Optional
import jwt

# Custom modules
from database import SimpleDatabase
from file_manager import FileManager
from models import UserCreate, UserLogin, Token, FileMetadata, SyncRequest

# --- Configuration ---
SECRET_KEY = "your-super-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# --- App Initialization ---
app = FastAPI(title="Cloud Drive API", description="A shared file storage API")
db = SimpleDatabase()
fm = FileManager()

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for simplicity
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Authentication ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    user = db.get_user(username)
    if user is None:
        raise credentials_exception
    return user['username']


# --- API Endpoints ---

@app.post("/auth/signup", response_model=Token)
async def signup(user: UserCreate):
    if len(user.username.strip()) < 3 or len(user.password) < 6:
        raise HTTPException(status_code=400, detail="Username must be > 3 chars and password > 6 chars.")
    if not db.create_user(user.username, user.password):
        raise HTTPException(status_code=409, detail="Username already exists")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/auth/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    if not db.authenticate_user(form_data.username, form_data.password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": form_data.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/files", response_model=List[FileMetadata])
async def get_files(current_user: str = Depends(get_current_user)):
    return fm.list_files()

@app.post("/files/upload")
async def upload_file(current_user: str = Depends(get_current_user), file: UploadFile = File(...)):
    contents = await file.read()
    if not fm.save_file(current_user, contents, file.filename):
        raise HTTPException(status_code=500, detail="Could not save file.")
    return {"filename": file.filename, "uploader": current_user, "status": "success"}

@app.get("/files/download/{filename}")
async def download_file(filename: str, current_user: str = Depends(get_current_user)):
    file_path = fm.get_file_path(filename)
    if file_path and file_path.exists():
        return FileResponse(path=file_path, filename=filename, media_type='application/octet-stream')
    raise HTTPException(status_code=404, detail="File not found")

@app.delete("/files/delete/{filename}")
async def delete_file(filename: str, current_user: str = Depends(get_current_user)):
    if not fm.delete_file(filename):
        raise HTTPException(status_code=404, detail="File not found or could not be deleted.")
    return {"filename": filename, "status": "deleted"}

@app.post("/files/sync")
async def sync_folder(sync_request: SyncRequest, current_user: str = Depends(get_current_user)):
    result = fm.sync_folder(current_user, sync_request.local_folder_path)
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    return result

@app.get("/user/me")
async def read_users_me(current_user: str = Depends(get_current_user)):
    return {"username": current_user}



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)