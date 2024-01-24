
#from tasks import predict_species
#result = add.delay(4, 5)
#print(result.get())

# Загрузка библиотек

from fastapi import FastAPI,HTTPException
import uvicorn
import joblib
from passlib.hash import bcrypt
from typing import List
import sqlite3 
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from pydantic import BaseModel
from datetime import datetime
from celery import Celery
import json
from tasks import SoftModel, SoftSpecies
from tasks import pred
from pickle import dumps


app = FastAPI()
DATABASE_URL = "sqlite:///./users.db"



pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class User(BaseModel):
    username: str
    password: str
    balance: int=10  #  дефолтное значение баланса пользователя
 
class UsersTable:
    def __init__(self):
        with sqlite3.connect('users.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT,
                    password TEXT,
                    balance INTEGER    --  столбец для  баланса пользователя       
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS models (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    prediction TEXT,
                    probability FLOAT,
                    user_id INTEGER,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bill (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    balance INTEGER ,
                    date_at TEXT,
                    time_at TEXT,
                    user_id INTEGER,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            ''')
            conn.commit()
    

    def create_user(self, user: User):
        hashed_password = pwd_context.hash(user.password)
        with sqlite3.connect('users.db') as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, password,balance) VALUES (?, ?, ?)", (user.username, hashed_password, user.balance))
            conn.commit()
    
    def get_user(self, username: str):
        with sqlite3.connect('users.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username=?", (username,))
            return cursor.fetchone()
        
    def update_balance(self, username: str, amount: int):
        with sqlite3.connect('users.db') as conn:
            cursor = conn.cursor()
        
        # Вычитаем сумму из текущего баланса
            cursor.execute("UPDATE users SET balance = balance - ? WHERE username = ?", (amount, username))

            date_at = datetime.now().date().strftime('%Y-%m-%d')
            time_at = datetime.now().time().strftime('%H:%M:%S')

        # Вставляем запись в таблицу bill с балансом, датой и временем
            cursor.execute("INSERT INTO bill (balance, date_at, time_at, user_id) VALUES (?, ?, ?, (SELECT id FROM users WHERE username = ?))",
                   (amount, date_at, time_at, username))

            conn.commit()

        # Получаем и возвращаем обновленный баланс пользователя
            updated_balance = self.get_user_balance(username)
            return updated_balance

    def get_user_balance(self, username: str):
        with sqlite3.connect('users.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT balance FROM users WHERE username=?", (username,))
            return cursor.fetchone()  
        
    def get_latest_bill_balance(self, username: str):
        with sqlite3.connect('users.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT balance FROM bill WHERE user_id = (SELECT id FROM users WHERE username = ?) ORDER BY id DESC LIMIT 1", (username,))
            return cursor.fetchone()[0] 

    def save_model(self, model_name: str, prediction: str, probability: float, user_id: int):
        with sqlite3.connect('users.db') as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO models (name, prediction, probability, user_id) VALUES (?, ?, ?, ?)",
                       (model_name, prediction, probability, user_id))
            conn.commit()

    def load_model(self, model_name: str):
        with sqlite3.connect('users.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM models WHERE name=?", (model_name,))
            return cursor.fetchone()
            
users_table = UsersTable()

@app.post("/register")
async def register(user: User):
    users_table.create_user(user)
    users_table.update_balance(user.username, user.balance)
    return {"message": "User registered successfully"}

@app.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = users_table.get_user(form_data.username)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    if not pwd_context.verify(form_data.password, user[2]):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    return {"message": "Logged in successfully"}


soft_model= SoftModel(downloads=1, cache=0, properties=0, network_state=1)
#serialized_model = dumps(soft_model.to_dict())
@app.post('/predict')
def predict_species(soft: SoftSpecies, user: User):
    # Получаем значение баланса пользователя из базы данных
    user.balance = users_table.get_latest_bill_balance(user.username)

    data = soft.dict()
    
    
    #initial_balance = users_table.update_balance(updated_balance)
    initial_balance = users_table.get_user_balance(user.username)
    
    prediction, probability = soft_model.predict_species(data['downloads'], data['cache'], data['properties'], data['network_state'])
    
    # Обновляем баланс пользователя, вычитая 1
    #updated_balance = users_table.update_balance(user.username, user.balance - 1 )
    updated_balance = users_table.update_balance(user.username, user.balance - 1)
    users_table.save_model('soft_model', prediction, probability, 1) 
    return {
        'prediction': prediction,
        'probability': probability,
        'balance':  user.balance - 1 
    }


# Вызываю задачу predict_species с использованием Celery

result= pred.delay(soft_model,1, 0, 0, 1)

# ожидаю завершения задачи
#result.wait()
print(result)

