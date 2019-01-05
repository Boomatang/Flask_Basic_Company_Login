from flask import url_for, redirect, flash, current_app
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, current_user

from app.email import send_email
from . import db, login_manager


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    email = db.Column(db.String(64), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    confirmed = db.Column(db.Boolean, default=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=True)
    company = db.relationship("Company", back_populates="users", lazy=False)
    admin = db.relationship("Company", back_populates="owner")


    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_confirmation_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'confirm': self.id})

    def confirm(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('confirm') != self.id:
            return False
        self.confirmed = True
        db.session.add(self)
        return True

    def generate_reset_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'reset': self.id})

    def reset_password(self, token, new_password):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('reset') != self.id:
            return False
        self.password = new_password
        db.session.add(self)
        return True

    def generate_email_change_token(self, new_email, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'change_email': self.id, 'new_email': new_email})

    def change_email(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('change_email') != self.id:
            return False
        new_email = data.get('new_email')
        if new_email is None:
            return False
        if self.query.filter_by(email=new_email).first() is not None:
            return False
        self.email = new_email
        db.session.add(self)
        return True

    @property
    def is_admin(self):
        if self.email == self.company.owner.email:
            return True
        else:
            return False

    def generate_invite_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'invite': self.id})

    @staticmethod
    def confirm_invited_user(token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        return True

    @staticmethod
    def load_invited_user(token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False

        user_id = data.get('invite')

        user = User.load_user(user_id)

        return user

    @staticmethod
    def load_user(user_id):
        user = User.query.filter_by(id=user_id).first_or_404()

        return user

    def __repr__(self):
        return f'<email : {self.email}>'


class Company(db.Model):
    __tablename__ = 'company'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True)
    users = db.relationship("User", back_populates="company")
    owner = db.relationship("User", uselist=False, back_populates="admin")

    def add_user(self, user):
        self.users.append(user)

    def set_company_owner(self, user):
        self.owner = user


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def email_in_system(email):
    user = User.query.filter_by(email=email).first()

    if user:
        return True
    else:
        return False


def invite_user(email):
    flash(f'Invite email has been set to {email}')

    user = User()
    user.email = email

    db.session.add(user)
    current_user.company.add_user(user)
    db.session.commit()

    token = user.generate_invite_token()
    send_email(user.email, 'You have been invited',
               'auth/email/invite', user=user, token=token)



