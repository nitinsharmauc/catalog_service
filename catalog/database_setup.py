import sys

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.engine import create_engine
from sqlalchemy.types import DateTime
from sqlalchemy.sql import func

Base = declarative_base()


class Category(Base):
    __tablename__ = 'categories'

    name = Column(String(250), nullable=False)
    id = Column(Integer, primary_key=True)

# serializable format for JSON
    @property
    def serialize(self):

        return {
            'name': self.name,
            'id': self.id, }


class Item(Base):
    __tablename__ = "items"

    title = Column(String(80), nullable=False)
    id = Column(Integer, primary_key=True)
    description = Column(String(250))
    creation_date = Column(DateTime, nullable=False, default=func.now())
    category_id = Column(Integer, ForeignKey('categories.id'))
    category = relationship(Category)

# serializable format for JSON
    @property
    def serialize(self):

        return {
            'title': self.title,
            'id': self.id,
            'description': self.description,
            'category_id': self.category_id, }


engine = create_engine('postgresql:///catalog')

Base.metadata.create_all(engine)
