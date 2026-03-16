
from fastapi import FastAPI
from app.database import Base, engine, SessionLocal
from app import models
from app.routers import requests, approvals, suppliers, documents, integrations, reports, sync
from sqlalchemy.orm import Session

app = FastAPI(title="EcoSystem Procurement PoC")

# init DB
Base.metadata.create_all(bind=engine)

# seed minimal users for roles
def seed():
    db: Session = SessionLocal()
    if db.query(models.User).count() == 0:
        db.add_all([
            models.User(fio="Иванов И.И.", role=models.RoleEnum.initiator, email="i@ex.ru"),
            models.User(fio="Петров П.П.", role=models.RoleEnum.director, email="d@ex.ru"),
            models.User(fio="Сидорова С.С.", role=models.RoleEnum.legal, email="l@ex.ru"),
        ])
        db.commit()
    db.close()

seed()

app.include_router(requests.router)
app.include_router(approvals.router)
app.include_router(suppliers.router)
app.include_router(documents.router)
app.include_router(integrations.router)
app.include_router(reports.router)
app.include_router(sync.router)

@app.get("/health")
def health():
    return {"status": "ok"}
