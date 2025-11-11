import glob, os
from sqlalchemy import text as sqltext
from app.db import engine, SessionLocal
from app.models import Document, Chunk
from app.config import settings
from app.rag import embed
import tiktoken

def ensure_pgvector():
    with engine.connect() as conn:
        conn.execute(sqltext("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()

def chunk(text, max_tokens=int(os.getenv("CHUNK_TOKENS","700")), overlap=0.15):
    enc = tiktoken.get_encoding("cl100k_base")
    ids = enc.encode(text)
    step = int(max_tokens*(1-overlap))
    out=[]

    for start in range(0,len(ids),step):
        part = ids[start:start+max_tokens]
        if not part: break
        out.append(enc.decode(part))
        if start+max_tokens>=len(ids): break
    return out

def run():
    ensure_pgvector(); s=SessionLocal()
    for path in glob.glob("seed_docs/*.md"):
        title=os.path.basename(path).replace("_"," ").replace(".md","")
        
        with open(path,"r",encoding="utf-8") as f: 
            txt=f.read().strip()
        
        d=Document(title=title, category=title.split()[0], source_tag="wm-guide")
        s.add(d)
        s.flush()
        parts=chunk(txt)
        vecs=embed(parts)
        for i,(p,v) in enumerate(zip(parts,vecs),1):
            s.add(Chunk(id=f"{d.id}::#{i}", doc_id=d.id, content=p, meta={"source":"wm-guide"}, embedding=v))

    s.commit()
    print("Seed ingest complete.")

if __name__=="__main__":
    run()
