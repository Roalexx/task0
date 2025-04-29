from models.db import db
from models.user import User
from models.asset import Asset
from app import create_app
from app.celery_app import celery

flask_app = create_app()

@celery.task(bind=True, name="async_db_tasks.create_user")
def create_user(self, username_from_form, email_from_form):
    with flask_app.app_context():
        try: 
            user = User(username=username_from_form, email=email_from_form)
            db.session.add(user)
            db.session.commit()
            return {
                "message": f"User {username_from_form} created successfully",
                "user_id": user.id
            }
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}
        finally:
            db.session.remove()

@celery.task(bind=True, name="async_db_tasks.list_users")
def list_users(self):
    with flask_app.app_context():
        try:
            users = User.query.all()
            return {
                "message": "Users fetched successfully",
                "users": [
                    {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email
                    }
                    for user in users
                ]
            }
        except Exception as e:
            return {"error": str(e)}
        finally:
            db.session.remove()

@celery.task(bind=True, name="async_db_tasks.creat_asset")
def create_asset(self, name_from_form, value_from_form, user_id_from_form):
    with flask_app.app_context():
        try:
            asset = Asset(name=name_from_form,value=value_from_form, user_id=user_id_from_form)
            db.session.add(asset)
            db.session.commit()
            return{
            "message": f"Asset {name_from_form} created succesfully",
            "asset_id": asset.id}
        except Exception as e:
            db.session.rollback()
            return{"error": str(e)}
        finally:
            db.session.remove

@celery.task(bind=True, name="async_db_tasks.list_assets")
def list_assets(self):
    with flask_app.app_context():
        try:
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
        except Exception as e:
            return{"error": str(e)}
        finally:
            db.session.remove()