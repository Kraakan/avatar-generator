# Following tutorial by Miguel Grinberg
# https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-iv-database
from datetime import datetime
from typing import Optional
import sqlalchemy as sa
import sqlalchemy.orm as so
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from flask_app import db, login, app

@login.user_loader
def load_user(id):
    return db.session.get(User, int(id))

class User(UserMixin, db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    username: so.Mapped[str] = so.mapped_column(sa.String(64), index=True,
                                                unique=True)
    email: so.Mapped[str] = so.mapped_column(sa.String(120), index=True,
                                             unique=True)
    password_hash: so.Mapped[Optional[str]] = so.mapped_column(sa.String(256))
    visibility: so.Mapped[int] = so.mapped_column(default=0) # 0=visible to admin, 1=visible to confirmed users, 2=visible to anyone
    avatar: so.Mapped[int] = so.mapped_column(default=0)
    models: so.Mapped['Model'] = so.relationship(
        back_populates='owner')
    pictures: so.Mapped['Generated_image'] = so.relationship(
        back_populates='owner')
    tuning_images: so.WriteOnlyMapped[list['Tuning_image']] = so.relationship(
        back_populates='owner',)
    def __repr__(self):
        return '<User {}>'.format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
class Model(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    name: so.Mapped[str] = so.mapped_column(sa.String(64))
    dir: so.Mapped[str] = so.mapped_column(sa.String(64), unique=True)
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id),
                                               index=True)
    timestamp: so.Mapped[datetime] = so.mapped_column(
        index=True, default=lambda: datetime.now())
    fine_tuning_prompt: so.Mapped[str] = so.mapped_column(sa.String(64))
    owner: so.Mapped['User'] = so.relationship(
        back_populates='models')
    generated_images: so.Mapped['Generated_image'] = so.relationship(
        back_populates='model')
    #tuning_images_used: so.Mapped['Tuning_image'] = so.relationship(back_populates='used_in_model')
    def __repr__(self):
        return 'Model {}'.format(self.name)

class Generated_image(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id),
                                               index=True)
    model_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(Model.id),
                                               index=True)
    timestamp: so.Mapped[datetime] = so.mapped_column(
        index=True, default=lambda: datetime.now())
    prompt : so.Mapped[str] = so.mapped_column(sa.String(140))
    filename: so.Mapped[str] = so.mapped_column(sa.String(64), unique=True)
    owner: so.Mapped['User'] = so.relationship(
        back_populates='pictures')
    model: so.Mapped['Model'] = so.relationship(
        back_populates='generated_images')
    def __repr__(self):
        return '{}'.format(self.filename)

class Tuning_image(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id),
                                               index=True)
    timestamp: so.Mapped[datetime] = so.mapped_column(
        index=True, default=lambda: datetime.now())
    filename: so.Mapped[str] = so.mapped_column(sa.String(64), unique=True)
    #used_in_model: so.WriteOnlyMapped['Model'] = so.relationship(back_populates='tuning_images_used')
    owner: so.Mapped[list['User']] = so.relationship(
        back_populates='tuning_images')
    def __repr__(self):
        return '{}'.format(self.filename)
    

with app.app_context():
        db.create_all()