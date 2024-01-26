import streamlit as st
import requests
import json

st.set_page_config(layout='wide')

st.header('Введите персональные данные:')
username = st.text_input('Имя пользователя:', value='')
password = st.text_input('Пароль:', type='password', value='')

inputs1 = {'username': username, 'password': password}

if st.button('Регистрация'):
    headers = {'Content-Type': 'application/json'}
    response = requests.post(url="http://127.0.0.1:8000/register", data=json.dumps(inputs1), headers=headers)
    result = json.loads(response.text)
    st.success(f'Регистрация: {result["message"]}')

st.header('Введите параметры 1- есть признак, 0 - отсутствует признак:')
downloads=st.number_input('DOWNLOADS:',min_value=0,max_value=1,value=0)
cache=st.number_input('CACHE:',min_value=0,max_value=1,value=0)
properties=st.number_input('PROPERTIES:',min_value=0,max_value=1,value=0)
network_state=st.number_input('NETWORK_STATE:',min_value=0,max_value=1,value=0)

inputs={'soft': {'downloads': downloads, 'cache': cache, 'properties': properties, 'network_state': network_state}, 'user': {'username': username, 'password': password}}

if st.button('Предсказание модели'):
    headers = {'Content-Type': 'application/json'}
    response = requests.post(url="http://127.0.0.1:8000/predict", data=json.dumps(inputs), headers=headers)
    prediction = response.json()
    st.success(f'The predicted model: {prediction["prediction"]}, Probability: {prediction["probability"]}, Balance: {prediction["balance"]}')