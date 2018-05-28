from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData
from flask_migrate import Migrate
from flask_login import LoginManager
from elasticsearch import Elasticsearch

app = Flask(__name__)
app.config.from_object(Config)
naming_convention = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(column_0_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}
db = SQLAlchemy(app, metadata=MetaData(naming_convention=naming_convention))
migrate = Migrate(app, db, render_as_batch=True)
login = LoginManager(app)
login.login_view = 'login' #function's name in routes
app.elasticsearch = Elasticsearch("http://localhost:9200")

from app import routes, models, errors

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': models.User, 'Post': models.Post, 'Item': models.Item, 'Comment': models.Comment, 'Inbox': models.Inbox}

# Reindex: run this after installing ElasticSearch
# with app.app_context():
#     models.User.reindex()
#     models.Item.reindex()
