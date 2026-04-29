# ScottyConnect Web App

## About

### [Production Link](https://scottyconnect-1.onrender.com/)

## Getting Started


### Backend

Dependency Installation

```
cd backend

python3 -m venv venv
source venv/bin/activate

pip install -r ../requirements.txt
```

Running the server

```
cd backend
source venv/bin/activate

python3 run.py
```

### Frontend

```
npm install

npm run dev
```

## Documentation

### Login Workflow

```mermaid
stateDiagram-v2
    login_page --> register_page: wants to register, redirect
    register_page --> verification_page: successful registration, redirect
    login_page --> verification_page: valid credentials but not verified, redirect
    verification_page --> main_page: successful verification, redirect
    login_page --> main_page: successful login, redirect
```



