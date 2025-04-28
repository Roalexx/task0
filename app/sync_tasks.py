from models.db import db
from models.user import User
from models.asset import Asset

def create_user(username_from_form, email_from_form):
    user = User(username=username_from_form, email=email_from_form)
    db.session.add(user)
    db.session.commit()
    return {
        "messeage": f"User {username_from_form} created successfully",
        "user_id": user.id
    }


def list_users():
    users = User.query.all()
    return[{"id": user.id, "username": user.username, "email": user.email}for user in users]

def create_asset(name_from_form,value_from_form,user_id_from_form):
    asset = Asset(name=name_from_form, value=value_from_form, user_id=user_id_from_form)
    db.session.add(asset)
    db.session.commit()
    return{
        "message": f"Asset {name_from_form} created succesfully",
        "asset_id": asset.id
    }

def list_assets():
    assets = Asset.query.all()
    return[{
        "id": asset.id,
        "name": asset.name,
        "value": asset.value,
        "owner":{
            "user_id": asset.user.id,
            "username": asset.user.username
        }
        } for asset in assets]