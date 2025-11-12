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

    user_clause = f"User profile: risk={user_meta.get('risk','medium')}, goal={user_meta.get('goal','')}"
    
    messages=[{"role":"system","content":SYSTEM_PROMPT},
              {"role":"user","content":f"{user_clause}\n\nContext:\n{ctx}\n---\nQuestion: {query}"}]
    
    chat = client.chat.completions.create(model=settings.CHAT_MODEL, messages=messages)

    return {"answer": chat.choices[0].message.content,
            "sources": [{"id":c.id,"meta":c.meta,"distance":d} for c,d in hits]
            }
