import bcrypt
from itsdangerous import URLSafeSerializer
from fastapi import Request
from app.config import settings

serializer = URLSafeSerializer(settings.SECRET_KEY, salt="session")
SESSION_COOKIE="wa_session"

def hash_password(p:str)->str: 
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()

def verify_password(p:str,h:str)->bool:
    try: 
        return bcrypt.checkpw(p.encode(), h.encode())
    except: 
        return False
    
def issue_session(user_id:str)->str: 
    return serializer.dumps({"uid":user_id})

def read_session(token:str|None)->str|None:
    if not token: 
        return None
    try: 
        return serializer.loads(token).get("uid")
    except: 
        return None
    
def current_user_id(request:Request)->str|None: 
    return read_session(request.cookies.get(SESSION_COOKIE))