from fastapi import FastAPI, Form, HTTPException, Body, Request
from fastapi.responses import RedirectResponse
import mysql.connector
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import time

app = FastAPI()

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    print(f"Incoming request: {request.method} {request.url}")
    response = await call_next(request)
    process_time = time.time() - start_time
    print(f"Finished request: {request.method} {request.url} - Status: {response.status_code} - Time: {process_time:.2f}s")
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Temporarily allow ALL for debugging
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"Hello": "World"}

# Database Settings
db_config = {
    'host': '127.0.0.1', # Use explicit IP
    'user': 'root',      
    'password': '',      
    'database': 'NewsHub',
    'connect_timeout': 5 # 5 seconds timeout
}

@app.post("/register")
def register_user(
    full_name: str = Form(...), 
    email: str = Form(...), 
    password: str = Form(...)
):
    conn = None
    try:
        print(f"--- Registration attempt for {email} ---")
        print("Connecting to database...")
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        print("Connected. Executing insert...")

        # Using 'password' as it exists in the actual database
        query = "INSERT INTO users (full_name, email, password) VALUES (%s, %s, %s)"
        cursor.execute(query, (full_name, email, password))
        
        print("Insert executed. Committing...")
        conn.commit()
        user_id = cursor.lastrowid
        
        print(f"Success! User ID: {user_id}")
        return {"message": "Success", "user_id": user_id}

    except mysql.connector.Error as err:
        print(f"Database error: {err}")
        if err.errno == 1062:
            raise HTTPException(status_code=400, detail="This email is already registered. Please use a different one.")
        raise HTTPException(status_code=500, detail=f"Database Error: {err}")
    except Exception as e:
        print(f"Unexpected error: {e}")
        return {"error": str(e)}
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
            print("Database connection closed.")
        print("--- Registration attempt finished ---")

@app.get("/interests")
def get_interests():
    conn = None
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM interests")
        rows = cursor.fetchall()
        interests = [{"id": row[0], "name": row[1]} for row in rows]
        return interests
    except Exception as e:
        print(f"Error fetching interests: {e}")
        raise HTTPException(status_code=500, detail="Could not fetch interests")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.post("/save-interests")
def save_interests(user_id: int = Body(...), interest_ids: List[int] = Body(...)):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # Delete existing interests for this user to avoid duplicates if re-submitting
        cursor.execute("DELETE FROM user_interests WHERE user_id = %s", (user_id,))
        
        # Insert new interests
        query = "INSERT INTO user_interests (user_id, interest_id) VALUES (%s, %s)"
        data = [(user_id, i_id) for i_id in interest_ids]
        cursor.executemany(query, data)
        
        conn.commit()
        cursor.close()
        conn.close()
        return {"message": "Interests saved successfully"}

    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=str(err))

from pydantic import BaseModel

class SignupData(BaseModel):
    full_name: str
    email: str
    password: str
    interest_ids: List[int]

@app.post("/complete-signup")
async def complete_signup(data: SignupData):
    full_name = data.full_name
    email = data.email
    password = data.password
    interest_ids = data.interest_ids

    conn = None
    try:
        print(f"--- Atomic Signup attempt for {email} ---")
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        # Start transaction
        conn.start_transaction()

        # 1. Insert User (using 'password' as it exists in the actual database)
        query_user = "INSERT INTO users (full_name, email, password) VALUES (%s, %s, %s)"
        try:
            cursor.execute(query_user, (full_name, email, password))
        except mysql.connector.Error as err:
            if err.errno == 1062:
                raise HTTPException(status_code=400, detail="This email is already registered.")
            raise err
            
        user_id = cursor.lastrowid
        print(f"User created with ID: {user_id}")

        # 2. Insert Interests
        if interest_ids:
            query_interests = "INSERT INTO user_interests (user_id, interest_id) VALUES (%s, %s)"
            interest_data = [(user_id, i_id) for i_id in interest_ids]
            cursor.executemany(query_interests, interest_data)
            print(f"Linked {len(interest_ids)} interests.")

        conn.commit()
        print("Signup transaction committed successfully.")
        return {"message": "Signup complete", "user_id": user_id}

    except HTTPException as he:
        if conn: conn.rollback()
        raise he
    except mysql.connector.Error as err:
        if conn: conn.rollback()
        print(f"Database error during signup: {err}")
        raise HTTPException(status_code=500, detail=f"Database Error: {err}")
    except Exception as e:
        if conn: conn.rollback()
        print(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
            print("Database connection closed.")
        print("--- Atomic Signup finished ---")

@app.get("/check-email/{email}")
def check_email(email: str):
    conn = None
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        return {"exists": user is not None}
    except Exception as e:
        print(f"Error checking email: {e}")
        raise HTTPException(status_code=500, detail="Error checking email")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

class LoginData(BaseModel):
    email: str
    password: str

@app.post("/login")
def login(data: LoginData):
    conn = None
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        # Note: In a real app, you would use password hashing (e.g., bcrypt)
        cursor.execute("SELECT id, full_name, email FROM users WHERE email = %s AND password = %s", 
                       (data.email, data.password))
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid email or password")
            
        return {"message": "Login successful", "user": user}
        
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Login error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

# To run: uvicorn main:app --reload
