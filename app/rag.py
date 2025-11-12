from typing import List, Dict, Tuple
from sqlalchemy import select, func, text
from sqlalchemy.orm import Session
from openai import OpenAI
from app.config import settings
from app.models import Chunk
from app.prompts import SYSTEM_PROMPT

client = OpenAI(api_key=settings.OPENAI_API_KEY)

def embed(texts: List[str]) -> List[List[float]]:
    res = client.embeddings.create(model=settings.EMBED_MODEL, input=texts)
    return [d.embedding for d in res.data]

def embed_one(q:str)->List[float]: 
    return embed([q])[0]

def search_chunks(db:Session, qv:List[float], k:int)->List[Tuple[Chunk,float]]:
    # Convert list to string format for pgvector
    qv_str = "[" + ",".join(map(str, qv)) + "]"
    stmt = select(Chunk, func.cosine_distance(Chunk.embedding, text(f"'{qv_str}'::vector")).label("dist")).order_by(text("dist")).limit(k)
    rows = db.execute(stmt).all(); 
    return [(r[0], float(r[1])) for r in rows]

def build_context(hits): 
    return "\n".join([f"[source:{c.meta.get('source','doc')}:{c.id}]\n{c.content}\n" for c,_ in hits])

def answer(db:Session, query:str, user_meta:Dict)->Dict:
    qv = embed_one(query)
    hits = search_chunks(db, qv, settings.TOP_K)
    ctx = build_context(hits)

    # Build comprehensive user profile clause
    profile_parts = []
    
    # Add current date/time information first
    if user_meta.get('current_date'):
        profile_parts.append(f"Current Date: {user_meta['current_date']}")
    
    if user_meta.get('name'):
        profile_parts.append(f"Name: {user_meta['name']}")
    if user_meta.get('age'):
        profile_parts.append(f"Age: {user_meta['age']}")
    if user_meta.get('annual_income'):
        profile_parts.append(f"Annual Income: ${user_meta['annual_income']:,.2f}")
    if user_meta.get('risk_tolerance'):
        profile_parts.append(f"Risk Tolerance: {user_meta['risk_tolerance']}")
    if user_meta.get('retirement_age'):
        profile_parts.append(f"Target Retirement Age: {user_meta['retirement_age']}")
        # Calculate years until retirement if we have age
        if user_meta.get('age') and user_meta.get('retirement_age'):
            years_to_retirement = user_meta['retirement_age'] - user_meta['age']
            if years_to_retirement > 0:
                profile_parts.append(f"Years Until Retirement: {years_to_retirement}")
    if user_meta.get('financial_goal'):
        profile_parts.append(f"Financial Goal: {user_meta['financial_goal']}")
    
    user_clause = "User Profile:\n" + "\n".join(profile_parts) if profile_parts else "User profile not provided"
    
    messages=[{"role":"system","content":SYSTEM_PROMPT},
              {"role":"user","content":f"{user_clause}\n\nContext:\n{ctx}\n---\nQuestion: {query}"}]
    
    chat = client.chat.completions.create(model=settings.CHAT_MODEL, messages=messages)

    return {"answer": chat.choices[0].message.content,
            "sources": [{"id":c.id,"meta":c.meta,"distance":d} for c,d in hits]
            }
