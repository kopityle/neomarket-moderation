# app/core/base.py
from sqlalchemy.orm import declarative_base

# ЕДИНСТВЕННЫЙ Base во всем приложении
Base = declarative_base()