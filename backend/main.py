"""
Assosa Ledger — backend API

A small, deliberately simple shared backend so the site-operations tool
can be used from a phone and a PC (or by more than one person) and
everyone sees the same data, instead of the local-only version.

Design choice: rather than one database table per module (equipment,
crews, extraction, etc.), every entry is stored in a single `entries`
table as {module, data(json)}. This keeps the backend small and means
adding a new field to a module later is a frontend-only change -- no
migration needed. For a small internal tool like this, that trade-off
is worth it; a bigger team/product would normally want a table per
module with real columns.

Deploy this the same way as your other project: a Render web service,
pointed at a Postgres database (Supabase's Postgres works fine -- you
can reuse your existing Supabase project with a new DATABASE_URL, or
create a fresh one). See README.md in this folder for exact steps.
"""
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, Session

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./assosa_ledger.db")
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
ACCESS_TOKEN_EXPIRE_HOURS = int(os.environ.get("ACCESS_TOKEN_EXPIRE_HOURS", "12"))
ALGORITHM = "HS256"

# Render/Supabase Postgres URLs sometimes come as postgres:// -- SQLAlchemy
# with psycopg2 wants postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

VALID_MODULES = {
    "equipment", "crews", "extraction", "custody",
    "compliance", "security", "budget", "compensation",
}
VALID_ROLES = {"owner", "gm", "geologist", "viewer"}


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    role = Column(String, nullable=False, default="viewer")
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Entry(Base):
    __tablename__ = "entries"
    id = Column(Integer, primary_key=True)
    module = Column(String, nullable=False, index=True)
    data = Column(JSON, nullable=False, default=dict)
    created_by = Column(String, ForeignKey("users.username"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


Base.metadata.create_all(bind=engine)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    name: str
    role: str


class EntryIn(BaseModel):
    module: str
    data: dict


class EntryOut(BaseModel):
    id: int
    module: str
    data: dict
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    username: str
    name: str
    role: str = "viewer"
    password: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    return jwt.encode({"sub": username, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    unauthorized = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise unauthorized
    except JWTError:
        raise unauthorized
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise unauthorized
    return user


def require_role(*roles):
    def _check(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles and user.role != "owner":
            raise HTTPException(status_code=403, detail="Not permitted for your role")
        return user
    return _check


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title="Assosa Ledger API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/auth/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form.username).first()
    if not user or not pwd_context.verify(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    return Token(access_token=create_token(user.username), username=user.username, name=user.name, role=user.role)


@app.get("/auth/me")
def me(user: User = Depends(get_current_user)):
    return {"username": user.username, "name": user.name, "role": user.role}


@app.post("/auth/users")
def create_user(payload: UserCreate, db: Session = Depends(get_db), user: User = Depends(require_role("owner"))):
    """Only an existing 'owner' can create new logins -- e.g. you creating
    an account for a geologist or your friend."""
    if payload.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"role must be one of {sorted(VALID_ROLES)}")
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="That username already exists")
    new_user = User(
        username=payload.username,
        name=payload.name,
        role=payload.role,
        password_hash=pwd_context.hash(payload.password),
    )
    db.add(new_user)
    db.commit()
    return {"status": "created", "username": new_user.username}


@app.get("/auth/users")
def list_users(db: Session = Depends(get_db), user: User = Depends(require_role("owner"))):
    users = db.query(User).order_by(User.username).all()
    return [{"username": u.username, "name": u.name, "role": u.role} for u in users]


@app.delete("/auth/users/{username}")
def delete_user(username: str, db: Session = Depends(get_db), user: User = Depends(require_role("owner"))):
    if username == user.username:
        raise HTTPException(status_code=400, detail="You can't delete your own account while signed in as it")
    target = db.query(User).filter(User.username == username).first()
    if not target:
        raise HTTPException(status_code=404, detail="No such user")
    db.delete(target)
    db.commit()
    return {"status": "deleted", "username": username}


@app.get("/entries", response_model=list[EntryOut])
def list_entries(module: Optional[str] = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = db.query(Entry)
    if module:
        if module not in VALID_MODULES:
            raise HTTPException(status_code=400, detail="Unknown module")
        q = q.filter(Entry.module == module)
    return q.order_by(Entry.created_at.asc()).all()


@app.post("/entries", response_model=EntryOut)
def create_entry(payload: EntryIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot add entries")
    if payload.module not in VALID_MODULES:
        raise HTTPException(status_code=400, detail="Unknown module")
    entry = Entry(module=payload.module, data=payload.data, created_by=user.username)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@app.delete("/entries/{entry_id}")
def delete_entry(entry_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot delete entries")
    entry = db.query(Entry).filter(Entry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(entry)
    db.commit()
    return {"status": "deleted"}
