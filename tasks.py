import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from pydantic import BaseModel
import joblib
import datetime as _dt
import sqlalchemy as _sql
import sqlalchemy.orm as _orm
import passlib.hash as _hash
from celery import Celery
import json
#import database as _database
from celery import Celery
REDIS_URL='redis://127.0.0.1:6379'
#app = Celery('tasks', broker='redis://localhost:6379/0', backend='redis://localhost:6379/0')
app= Celery("tasks", broker=REDIS_URL, backend='redis')

app.conf.update(
    CELERY_TASK_SERIALIZER='pickle',
    CELERY_RESULT_SERIALIZER='pickle'
)

#@app.task
#def add(x:int, y:int):
    #return x + y
    #print(f"Вывод{x} и  {y}  {result}")
  
# Класс описывает характеристики soft
class SoftSpecies(BaseModel):
    downloads: int
    cache: int
    properties: int
    network_state: int

# обучение модели и делает предсказания
class SoftModel:
    def __init__(self,downloads,cache,properties,network_state):
        self.df=pd.read_csv('soft.csv')
        self.model_fname_='soft_model.pkl'
        self.downloads = downloads
        self.cache = cache
        self.properties = properties
        self.network_state = network_state
        try:
            self.model=joblib.load(self.model_fname_)
        except Exception as _:
            self.model=self._train_model()
            joblib.dump(self.model,self.model_fname_)
    
        
    
    
#Обучение модели используя RandomForest Classifier
    def _train_model(self):
        X=self.df.drop('Label',axis=1)
        y=self.df['Label']
        rfc=RandomForestClassifier()
        model=rfc.fit(X,y)
        return model
    
    # Создание предсказания по пользоват. данным
    def predict_species(self,downloads, cache,properties, network_state):
        data_in=[[downloads, cache,properties, network_state]]
        prediction=self.model.predict(data_in)
        probability=self.model.predict_proba(data_in).max()
        return prediction[0], probability
    
# Задача, которая будет выполняться в фоновом режиме
@app.task
def pred(model,downloads, cache,properties, network_state):

            data_in=[[downloads, cache,properties, network_state]]
            prediction=model.predict(data_in)
            probability=model.predict_proba(data_in).max()
            return prediction[0], probability
     

    
 



