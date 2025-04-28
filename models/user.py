from models.db import db
from models.asset import Asset

class User(db.Model):
    __tablename__ = 'users'
 
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False, unique=True)
    email = db.Column(db.String(100), nullable=False, unique=True)

    assets = db.relationship(Asset, backref='user', lazy=True)

    def __repr__(self):
        return f"<User {self.username}>"