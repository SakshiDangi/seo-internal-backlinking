import os

from sqlalchemy import create_engine, Column, String, Text, Integer, Boolean, ForeignKey, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

# Create a base class for the ORM models
Base = declarative_base()


# Define the User model
class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    active = Column(Boolean, nullable=True)


# Define the Website model
class Website(Base):
    __tablename__ = 'website'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    domain = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP, nullable=False)
    updated_at = Column(TIMESTAMP, nullable=False)


# Define the WebsitePages model
class WebsitePages(Base):
    __tablename__ = 'website_pages'
    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String(255), nullable=False)
    canonical_url = Column(String(255), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    author = Column(String(255), nullable=True)
    keywords = Column(Text, nullable=True)
    language_code = Column(String(10), nullable=False)
    text = Column(Text, nullable=False)
    markdown = Column(Text, nullable=False)
    website_id = Column(Integer, ForeignKey('website.id'), nullable=False)
    website = relationship("Website")


# Define the UserWebsite model
class UserWebsite(Base):
    __tablename__ = 'user_website'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    website_id = Column(Integer, ForeignKey('website.id'), nullable=False)
    user = relationship("User")
    website = relationship("Website")


def create_tables():
    # Define the MySQL connection string
    DATABASE_URL = os.getenv('TIDB_CONNECTION_STRING')

    # Create the SQLAlchemy engine
    engine = create_engine(DATABASE_URL)

    # Create the tables in the database
    Base.metadata.create_all(engine)

