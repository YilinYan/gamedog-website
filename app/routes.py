from os import path
from app import app, db
from uuid import uuid4
from sqlalchemy import or_, and_
from flask import render_template, flash, redirect, url_for, request, g, send_from_directory, jsonify
from app.forms import LoginForm, RegistrationForm, EditProfileForm, PostForm, CommentForm, SearchForm, EditItemForm, SendMessageForm
from app.models import User, Post, Comment, Item, Inbox
from flask_login import current_user, login_user, logout_user, login_required
from werkzeug.urls import url_parse
from app.search import add_to_index, remove_from_index, query_index

@app.before_request
def before_request():
    if current_user.is_authenticated:
        g.search_form = SearchForm()

# Static files
@app.route('/css/<path:path>')
def send_css(path):
    return send_from_directory('templates/css', path)
@app.route('/js/<path:path>')
def send_js(path):
    return send_from_directory('templates/js', path)
@app.route('/img/<path:path>')
def send_img(path):
    return send_from_directory('templates/img', path)

# return number of unread messages (for polling query)
@app.route('/inbox/unread')
@login_required
def inbox_unread():
    unread = Inbox.query.filter(and_(Inbox.read==False, Inbox.receiver_id==current_user.id)).order_by(Inbox.timestamp.asc())
    unread = [m for m in unread] # query to list
    return jsonify(len(unread))

# render the main inbox view
@app.route('/inbox')
@login_required
def inbox():
    users = User.query.all()
    unread = Inbox.query.filter(and_(Inbox.read==False, Inbox.receiver_id==current_user.id)).order_by(Inbox.timestamp.asc())
    unread = [m for m in unread] # query to list
    return render_template('inbox.html', title='Inbox', users=users, all_messages=unread)

# render the chat view
@app.route('/inbox/from/<username>', methods=['GET','POST'])
@login_required
def inbox_to(username):
    form = SendMessageForm()
    if form.validate_on_submit():
        receiver = User.query.filter_by(username=form.receiver.data).first_or_404()
        inbox = Inbox(body=form.body.data, author=current_user, receiver=receiver, read=False)
        db.session.add(inbox)
        db.session.commit()
        flash('Message sent.')
        return redirect(url_for('inbox_to', username=username))
    users = User.query.all()
    user = User.query.filter_by(username=username).first_or_404()

    # read all messages from <username>
    Inbox.query.filter(and_(Inbox.sender_id==user.id, Inbox.receiver_id==current_user.id)).update({Inbox.read: True})
    db.session.commit()

    unread = Inbox.query.filter(and_(Inbox.read==False, Inbox.receiver_id==current_user.id)).order_by(Inbox.timestamp.asc())
    unread = [m for m in unread] # query to list

    messages = Inbox.query.filter(or_(and_(Inbox.sender_id==current_user.id, Inbox.receiver_id==user.id), and_(Inbox.sender_id==user.id, Inbox.receiver_id==current_user.id))).order_by(Inbox.timestamp.asc())

    return render_template('inbox_to.html', title='Messages with ' + username, users=users, user=user, form=form, all_messages=unread, messages=messages)

@app.route('/search')
@login_required
def search():
    if g.search_form.q.data == '':  #err
        return redirect(url_for('explore'))
    page = request.args.get('page', 1, type=int)
    items, total = Item.search(g.search_form.q.data, 1, 1000)
    users, total = User.search(g.search_form.q.data, 1, 1000)
    return render_template('explore.html', title='Search "' + g.search_form.q.data + '"...', users=users, items=items)

@app.route('/add_item', methods=['GET','POST'])
@login_required
def add_item():
    form = EditItemForm()
    if form.validate_on_submit():
        item = Item()
        item.title = form.title.data
        item.image = form.image.data
        item.body = form.body.data
        db.session.add(item)
        db.session.commit()
        flash('Successfully Adding.')
        return redirect(url_for('item', item_id=item.id))
    return render_template('Edit_item.html', title='Add Game', form=form)

@app.route('/item/<item_id>', methods=['GET','POST'])
@login_required
def item(item_id):
    form = CommentForm()
    item = Item.query.filter_by(id=item_id).first()
    if item is None:
        flash('Item {} not found.'.format(item_id))
        return redirect(url_for('index'))
    if form.validate_on_submit():
        comment = Comment(body=form.comment.data, score=form.score.data, author=current_user, item=item)
        db.session.add(comment)
        db.session.commit()
        flash('Successful comment!')
        return redirect(url_for('item', item_id=item_id))
    return render_template('item.html',title='Game', form=form, item=item, comments=item.comments)

@app.route('/edit_item/<id>', methods=['GET','POST'])
@login_required
def edit_item(id): #duplicate
    form = EditItemForm()
    item = Item.query.filter_by(id=id).first()
    if Item is None:
        flash('Game {} not found.'.format(id))
        redirect(url_for('explore'))
    if form.validate_on_submit():
        item.title = form.title.data
        item.image = form.image.data
        item.body = form.body.data
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('item', item_id=id))
    elif request.method == 'GET':
        form.title.data = item.title
        form.image.data = item.image
        form.body.data = item.body
    return render_template('edit_item.html', title='Edit Game', form=form)

@app.route("/explore", methods=['GET', 'POST'])
@login_required
def explore():
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', 'default', type=str)
    if sort=='popularity':
        items = Item.query.order_by(db.desc(db.session.query(db.func.sum(Item.comments)))).paginate(page, 20, False)
    elif sort=='score':
        items = Item.query.order_by(db.desc(db.session.query(db.func.avg(Comment.score)).filter(Comment.item_id==Item.id))).paginate(page, 20, False)
    else:
        items = Item.query.paginate(page, 20, False)
    users = User.query.all()
    next_url = url_for('explore', page=items.next_num, sort=sort) \
            if items.has_next else None
    prev_url = url_for('explore', page=items.prev_num, sort=sort) \
            if items.has_prev else None
    return render_template('explore.html', title='Explore', users=users, items=items.items, next_url=next_url, prev_url=prev_url)

@app.route('/follow/<username>')
@login_required
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('User {} not found.'.format(username))
        return redirect(url_for('index'))
    if user == current_user:
        flash('You can not follow yourself.')
        return redirect(url_for('user', username=username))
    current_user.follow(user)
    db.session.commit()
    flash('You are following {}!'.format(username))
    return redirect(url_for('user', username=username))

@app.route('/unfollow/<username>')
@login_required
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('User {} not found.'.format(username))
        return redirect(url_for('index'))
    if user == current_user:
        flash('You can not unfollow yourself.')
        return redirect(url_for('user', username=username))
#   if not current_user.is_following(user):
    current_user.unfollow(user)
    db.session.commit()
    flash('You unfollowed {}.'.format(username))
    return redirect(url_for('user', username=username))

@app.route('/edit_profile', methods=['GET','POST'])
@login_required
def edit_profile(): #duplicate
    form = EditProfileForm()
    if form.validate_on_submit():
        avatar = form.avatar.data
        if avatar:
            filename = avatar.filename
            extension = filename.rsplit('.', 1)[1].lower()
            if extension in ['jpg', 'jpeg', 'png', 'gif']:
                img_id = str(uuid4())
                filename = img_id + '.' + extension
                avatar.save(path.join(app.root_path, 'templates', 'img', filename))
                current_user.avatar = filename
            else:
                flash('Image file not supported.')
                return render_template('edit_profile.html', title='Edit Profile', form=form)

        current_user.username = form.username.data
        current_user.introduction = form.introduction.data
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('user', username=current_user.username))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.introduction.data = current_user.introduction
    else:
        flash('Failed to update your profile.')
    return render_template('edit_profile.html', title='Edit Profile', form=form)

@app.route('/user/<username>')
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    posts = user.posts
    followed = user.followed
    comments = user.comments
    return render_template('user.html', title='Profile', user=user, posts=posts, comments=comments, followed=followed)

@app.route('/register', methods=['GET','POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data, admin=False)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("Welcome! You're now a member of us!")
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/delete_post/<id>')
@login_required
def delete_post(id):
    post = Post.query.filter_by(id=id).first_or_404()
    if(post.author != current_user):
        flash("Permission denied!")
        return redirect(url_for('index'))
    db.session.delete(post)
    db.session.commit()
    flash("Post deleted!")
    return redirect(url_for('index'))

@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(body=form.post.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Successful post sending!')
        return redirect(url_for('index'))
    posts = current_user.followed_posts()
    return render_template('index.html', title='Home', form=form, posts=posts)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)

        next_page = request.args.get('next')
        if next_page is None or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
#        flash('Login requested for user {}, remember_me={}'.format(
#            form.username.data, form.remember_me.data))
    return render_template('login.html', title='Sign In', form=form)
