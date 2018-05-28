from app import db, login
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from hashlib import md5
from app.search import add_to_index, remove_from_index, query_index

class Inbox(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String(140))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.now)
    read = db.Column(db.Boolean)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    # def replies(self):
    #     return Inbox.query.filter(Inbox.reply_id==self.id).order_by(Inbox.timestamp.asc())

    def __repr__(self):
        return '<Inbox {}>'.format(self.body)

class SearchableMixin(object):
    @classmethod
    def search(cls, expression, page, per_page):
        ids, total = query_index(cls.__tablename__, expression, page, per_page)
        if total == 0:
            return cls.query.filter_by(id=0), 0
        when = []
        for i in range(len(ids)):
            when.append((ids[i], i))
        return cls.query.filter(cls.id.in_(ids)).order_by(
            db.case(when, value=cls.id)), total

    @classmethod
    def before_commit(cls, session):
        if not hasattr(session, '_changes'):
           session._changes = { 'add':[], 'update':[], 'delete':[] }
        session._changes['add'] += [obj for obj in session.new if isinstance(obj, cls)]
        session._changes['update'] += [obj for obj in session.dirty if isinstance(obj, cls)]
        session._changes['delete'] += [obj for obj in session.deleted if isinstance(obj, cls)]

    @classmethod
    def after_commit(cls, session):
        for obj in session._changes['add']:
            if isinstance(obj, cls):
                add_to_index(cls.__tablename__, obj)
                session._changes['add'].remove(obj)
        for obj in session._changes['update']:
            if isinstance(obj, cls):
                add_to_index(cls.__tablename__, obj)
                session._changes['update'].remove(obj)
        for obj in session._changes['delete']:
            if isinstance(obj, cls):
                remove_from_index(cls.__tablename__, obj)
                session._changes['delete'].remove(obj)

    @classmethod
    def reindex(cls):
        for obj in cls.query:
            add_to_index(cls.__tablename__, obj)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.now)
    body = db.Column(db.String(128))
    score = db.Column(db.Integer)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'))

    def __repr__(self):
        return '<Comment {}>'.format(self.body)

class Item(SearchableMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128), index=True)
    image = db.Column(db.String(128))
    body = db.Column(db.String(256))
    comments = db.relationship('Comment', backref='item', lazy='dynamic')

    __searchable__ = ['title']

    def __repr__(self):
        return '<Item {}>'.format(self.title)

    def score(self):
        score = db.session.query(db.func.avg(Comment.score)).filter(Comment.item_id==self.id).scalar()
        if score is None:
            score = 0
        return round(score, 1)

db.event.listen(db.session, 'before_commit', Item.before_commit)
db.event.listen(db.session, 'after_commit', Item.after_commit)

follows = db.Table('followers',
        db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
        db.Column('followed_id', db.Integer, db.ForeignKey('user.id'))
        )

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

class User(SearchableMixin, UserMixin, db.Model): # usermixin?
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    introduction = db.Column(db.String(128))
    avatar = db.Column(db.String(128))
    admin = db.Column(db.Boolean)

    posts = db.relationship('Post', backref='author', lazy='dynamic')
    comments = db.relationship('Comment', backref='author', lazy='dynamic')
    followed = db.relationship('User', secondary=follows,
            primaryjoin=(follows.c.follower_id == id),
            secondaryjoin=(follows.c.followed_id == id),
            backref=db.backref('followers', lazy='dynamic'), lazy='dynamic')
    sent_messages = db.relationship('Inbox', backref='author', lazy='dynamic', foreign_keys="[Inbox.sender_id]")
    received_messages = db.relationship('Inbox', backref='receiver', lazy='dynamic', foreign_keys="[Inbox.receiver_id]")

    __searchable__ = ['username']

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_avatar(self, size):
        if self.avatar:
            return '/img/' + self.avatar
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return 'https://www.gravatar.com/avatar/{}?d=retro&s={}'.format(
                digest, size)

    def follow(self, user):
        if not self.is_following(user):
            self.followed.append(user)

    def unfollow(self, user):
        if self.is_following(user):
            self.followed.remove(user)

    def is_following(self, user):
        return self.followed.filter(
                follows.c.followed_id == user.id).count() > 0

    def followed_posts(self):
        others = Post.query.join(
                follows, (follows.c.followed_id == Post.user_id)).filter(
                        follows.c.follower_id == self.id)
        own = Post.query.filter_by(user_id = self.id)
        return others.union(own).order_by(Post.timestamp.desc())

db.event.listen(db.session, 'before_commit', User.before_commit)
db.event.listen(db.session, 'after_commit', User.after_commit)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String(140))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.now)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return '<Post {}>'.format(self.body)
