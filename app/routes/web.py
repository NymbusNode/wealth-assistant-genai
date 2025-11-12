from fastapi import APIRouter, Request, Depends, Response, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from jinja2 import Environment, FileSystemLoader, select_autoescape
from app.db import get_db, Base, engine
from app.models import User, Chat, Message, Risk, Document
from app.security import hash_password, verify_password, issue_session, current_user_id, SESSION_COOKIE
from app.rag import answer as rag_answer
import markdown

templates = Environment(loader=FileSystemLoader("app/templates"), autoescape=select_autoescape())
router = APIRouter()
Base.metadata.create_all(bind=engine)

def render(name, **ctx):
    return HTMLResponse(templates.get_template(name).render(**ctx))

def user_or_redirect(request:Request, db:Session):
    uid = current_user_id(request)
    if not uid: 
        return None, RedirectResponse("/login", status_code=302)
    u = db.get(User, uid)
    if not u:
        resp = RedirectResponse("/login", status_code=302); resp.delete_cookie(SESSION_COOKIE); return None, resp
    return u, None

@router.get("/", response_class=HTMLResponse)
def home(request:Request): 
    return RedirectResponse("/dashboard", status_code=302)

@router.get("/register", response_class=HTMLResponse)
def register_form(): 
    return render("register.html") 

@router.post("/register")
def register(username:str=Form(), password:str=Form(), name:str=Form(""),
             age:int=Form(0), annual_income:float=Form(0),
             risk_tolerance:str=Form("medium"), financial_goal:str=Form(""),
             retirement_age:int=Form(65), db:Session=Depends(get_db)):
    
    if db.query(User).filter_by(username=username).first(): 
        raise HTTPException(400, "Username exists")
    
    u = User(username=username, password_hash=hash_password(password), name=name, age=age,
             annual_income=annual_income, risk_tolerance=Risk(risk_tolerance), financial_goal=financial_goal,
             retirement_age=retirement_age)
    db.add(u); db.commit()
    resp = RedirectResponse("/dashboard", status_code=302)
    resp.set_cookie(SESSION_COOKIE, issue_session(u.id), httponly=True) 
    return resp

@router.get("/login", response_class=HTMLResponse)
def login_form(): 
    return render("login.html")

@router.post("/login")
def login(username:str=Form(), password:str=Form(), db:Session=Depends(get_db)):
    u = db.query(User).filter_by(username=username).first()

    if not u or not verify_password(password, u.password_hash): 
        raise HTTPException(401, "Invalid credentials")
    
    resp = RedirectResponse("/dashboard", status_code=302)
    resp.set_cookie(SESSION_COOKIE, issue_session(u.id), httponly=True)
    return resp

@router.get("/logout")
def logout():
    resp = RedirectResponse("/login", status_code=302) 
    resp.delete_cookie(SESSION_COOKIE)
    return resp

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request:Request, db:Session=Depends(get_db)):
    u, r = user_or_redirect(request, db)
    if r: 
        return r
    chats = db.query(Chat).filter_by(user_id=u.id).order_by(Chat.created_at.desc()).limit(3).all()
    return render("dashboard.html", user=u, recent_chats=chats)

@router.get("/profile", response_class=HTMLResponse)
def profile(request:Request, db:Session=Depends(get_db)):
    u, r = user_or_redirect(request, db)
    if r: 
        return r
    return render("profile.html", user=u)

@router.post("/profile")
def profile_update(request:Request, name:str=Form(""), age:int=Form(0), annual_income:float=Form(0),
                   risk_tolerance:str=Form("medium"), financial_goal:str=Form(""), 
                   retirement_age:int=Form(65), db:Session=Depends(get_db)):
    u, r = user_or_redirect(request, db)
    if r: 
        return r
    u.name=name
    u.age=age
    u.annual_income=annual_income
    u.risk_tolerance=Risk(risk_tolerance)
    u.financial_goal=financial_goal
    u.retirement_age=retirement_age
    db.commit()
    return RedirectResponse("/profile", status_code=302)

@router.get("/chat", response_class=HTMLResponse)
def chat_new(request:Request, db:Session=Depends(get_db)):
    u, r = user_or_redirect(request, db)
    if r: 
        return r
    # Render chat page without creating a chat yet
    return render("chat.html", user=u, chat_id="new", messages=[])

@router.get("/chat/{chat_id}", response_class=HTMLResponse)
def chat_view(chat_id:str, request:Request, db:Session=Depends(get_db)):
    u, r = user_or_redirect(request, db)
    if r: 
        return r
    # Handle "new" chat_id
    if chat_id == "new":
        return render("chat.html", user=u, chat_id="new", messages=[])
    
    msgs = db.query(Message).filter_by(chat_id=chat_id).order_by(Message.created_at).all()
    return render("chat.html", user=u, chat_id=chat_id, messages=msgs)

@router.post("/chat/{chat_id}/message", response_class=HTMLResponse)
def chat_message(chat_id:str, request:Request, content:str=Form(), db:Session=Depends(get_db)):
    u, r = user_or_redirect(request, db) 
    if r: 
        return r
    
    # Create new chat if chat_id is "new"
    is_new_chat = (chat_id == "new")
    if is_new_chat:
        c = Chat(user_id=u.id, title="")
        db.add(c)
        db.commit()
        chat_id = c.id
    
    um = Message(chat_id=chat_id, role="user", content=content)
    db.add(um)
    db.commit()
    meta = {
        "name": u.name,
        "age": u.age,
        "annual_income": float(u.annual_income),
        "risk_tolerance": u.risk_tolerance.value,
        "financial_goal": u.financial_goal,
        "retirement_age": u.retirement_age
    }
    res = rag_answer(db, content, meta)
    
    # Convert markdown to HTML for assistant response
    answer_html = markdown.markdown(res["answer"], extensions=['extra', 'nl2br'])
    am = Message(chat_id=chat_id, role="assistant", content=answer_html, retrieval_meta=res["sources"]) 
    db.add(am)
    db.commit()

    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader("app/templates"))
    tpl = env.get_template("_message.html")
    
    # Return both user message and assistant response
    user_html = tpl.render(message=um)
    assistant_html = tpl.render(message=am)
    
    # If this was a new chat, add HTMX headers to update the form action and URL
    response = HTMLResponse(user_html + assistant_html)
    if is_new_chat:
        response.headers["HX-Push-Url"] = f"/chat/{chat_id}"
        response.headers["HX-Trigger"] = f'{{"updateChatForm":"{chat_id}"}}'
    
    return response

@router.get("/library", response_class=HTMLResponse)
def library(request:Request, db:Session=Depends(get_db)):
    u, r = user_or_redirect(request, db)
    if r: 
        return r
    docs = db.query(Document).order_by(Document.created_at.desc()).all()
    from jinja2 import Environment, FileSystemLoader
    return render("library.html", user=u, docs=docs)
