import sqlalchemy
import sqlalchemy as sq
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy import Boolean


Base = declarative_base()


#Создание и заполнение базы данных
Base = declarative_base()


class User(Base):
    __tablename__ = "user"

    #id = sq.Column(sq.Integer, primary_key=True)
    name = sq.Column(sq.Integer, primary_key=True)
    words = relationship("User_Words", backref='users')
    
    def __str__(self):
        return f'{self.name}'


class User_Words(Base):
    __tablename__ = 'user_words'
    id = sq.Column(sq.Integer, primary_key=True)
    user_id = sq.Column(sq.Integer(), sq.ForeignKey("user.name"))
    words_id =  sq.Column(sq.Integer(), sq.ForeignKey("words.id"))


class Words(Base):
    __tablename__ = "words"

    id = sq.Column(sq.Integer, primary_key=True)
    word = sq.Column(sq.String(length=160), unique=True)
    translation = sq.Column(sq.String(length=160), unique=True)
    is_public = sq.Column(Boolean)
    user = relationship("User_Words", backref='wordss')  #cascade="all, delete-orphan"
    
    def __str__(self):
        return f'{self.word}, {self.translation}'