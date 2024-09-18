from email.message import EmailMessage
from flask_bcrypt import Bcrypt,check_password_hash

from flask import Flask, flash, render_template, url_for,redirect,request,session
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from flask_wtf import FlaskForm
from wtforms import DateField, FileField, IntegerField, StringField,PasswordField,SubmitField,SelectField, TextAreaField
from wtforms.validators import InputRequired,Length,ValidationError,Email,DataRequired
from sqlalchemy import LargeBinary
from sqlalchemy.orm import aliased
import os
from werkzeug.utils import secure_filename
import uuid as unique_id
import plotly.express as px
import pandas as pd



app=Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI']="sqlite:///sample.sqlite3"
app.config['SECRET_KEY']='sanjikun'
UPLOAD_FOLDER = 'static/images/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
UPLOAD_FOLDER_1 = 'static/audio/'
app.config['UPLOAD_FOLDER_1'] = UPLOAD_FOLDER_1

db=SQLAlchemy(app)
app.app_context().push()

app.debug = True

bcrypt = Bcrypt(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    creator = db.Column(db.Boolean, default=False)
    blacklist = db.Column(db.Boolean, default=False)
    #registration_date = db.Column(db.DateTime)


class Song(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    artist_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    lyrics = db.Column(db.Text)
    duration = db.Column(db.Integer)
    release_date = db.Column(db.Date)
    audio_file = db.Column(db.String(255))
    song_picture = db.Column(db.String(),nullable = True)

    album = db.relationship('Album',secondary='album_song',back_populates='song_album')
    artist = db.relationship('User', backref='song_creator')
    playlists = db.relationship('Playlist', secondary='playlist_song', back_populates='songs')
    ratings = db.relationship('Rating', backref='song', lazy=True)
        
    def average_rating(self):
        if self.ratings:
            total_ratings = sum(r.rating for r in self.ratings)
            return total_ratings / len(self.ratings)
        else:
            return 0
   

class Album(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(120), nullable=False)
    genre = db.Column(db.String(80))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    song_album = db.relationship('Song', secondary='album_song', back_populates='album')


class Playlist(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(120), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    description = db.Column(db.Text)
    public_status = db.Column(db.Boolean, default=True)

    songs = db.relationship('Song', secondary='playlist_song', back_populates='playlists')
   
class playlist_song(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    playlist_id = db.Column('playlist_id', db.Integer, db.ForeignKey('playlist.id'))
    song_id= db.Column('song_id', db.Integer, db.ForeignKey('song.id')) 

class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True,autoincrement=True)
    song_id = db.Column(db.Integer, db.ForeignKey('song.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    rating = db.Column(db.Integer)

class album_song(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    album_id = db.Column('album_id', db.Integer, db.ForeignKey('album.id'))
    song_id= db.Column('song_id', db.Integer, db.ForeignKey('song.id')) 

class RegistrationForm(FlaskForm):
    id = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "ID"})
    username = StringField("Username", validators=[InputRequired(), Length(min=4, max=20)])
    email = StringField("Email", validators=[InputRequired(), Email()])
    password = PasswordField("Password", validators=[InputRequired(), Length(min=4, max=20)])
    role = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Role"})


    submit = SubmitField("Register")
    

    def validate_username(self,username):
        existing_user_username = User.query.filter_by(
            username=username.data).first()
        
        if existing_user_username:
            raise ValidationError("that username is already taken.Please choose another one")

class AdminLoginForm(FlaskForm):
    username = StringField("Username", validators=[InputRequired(), Length(min=4, max=20)],render_kw={"placeholder": "Username"})
    password = PasswordField("Password", validators=[InputRequired(), Length(min=4, max=20)],render_kw={"placeholder": "Password"})
    submit = SubmitField("Login")

class UserLoginForm(FlaskForm):
    username = StringField("Username", validators=[InputRequired(), Length(min=4, max=20)],render_kw={"placeholder": "Username"})
    password = PasswordField("Password", validators=[InputRequired(), Length(min=4, max=20)],render_kw={"placeholder": "Password"})
    submit = SubmitField("Login")

class CreatorLoginForm(FlaskForm):
    username = StringField("Username", validators=[InputRequired(), Length(min=4, max=20)],render_kw={"placeholder": "Username"})
    password = PasswordField("Password", validators=[InputRequired(), Length(min=4, max=20)],render_kw={"placeholder": "Password"})
    submit = SubmitField("Login")

class CreatorRegistrationForm(FlaskForm):
    submit = SubmitField('Register as Creator')

class SongDetailsForm(FlaskForm):
    id = IntegerField("Song ID", validators=[InputRequired()])
    title = StringField("Song Title", validators=[InputRequired(), Length(max=120)])
    lyrics = TextAreaField("Lyrics", validators=[InputRequired()])
    duration = IntegerField("Duration", validators=[InputRequired()])
    release_date = DateField("Release Date", format='%Y-%m-%d', validators=[InputRequired()])
    audio_file = FileField("Audio File (MP3)", validators=[InputRequired()])
    song_picture = FileField("Song Picture (JPEG/PNG)", validators=[InputRequired()])  # Added label for song picture
    submit = SubmitField("Submit")

class PlaylistForm(FlaskForm):
    title = StringField("Playlist Name", validators=[InputRequired(), Length(min=3, max=50)])
    description = TextAreaField("Description", validators=[InputRequired()])

    submit = SubmitField("Create Playlist")

class AddSongToPlaylistForm(FlaskForm):
    song = SelectField('Select Song', validators=[DataRequired()], coerce=int)
    submit = SubmitField('Add Song to Playlist')

    def set_song_choices(self, songs):
        self.song.choices = [(song.id, song.title) for song in songs]

class AlbumForm(FlaskForm):
    title = StringField("Album Name", validators=[InputRequired(), Length(min=3, max=50)])
    genre = TextAreaField("Genre", validators=[InputRequired()])

    submit = SubmitField("Create Album")


class AddSongToAlbumForm(FlaskForm):
    song = SelectField('Select Song', validators=[DataRequired()], coerce=int)
    submit = SubmitField('Add Song to Playlist')

    def set_song_choices(self, songs):
        self.song.choices = [(song.id, song.title) for song in songs]


        
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/user_login', methods=['GET', 'POST'])
def user_login():
    form = UserLoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('user_dashboard')) 
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('user_login.html', form=form)

@app.route('/creator_login', methods=['GET', 'POST'])
def creator_login():
    form = CreatorLoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password) and user.creator == 1:
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('creator_page')) 
        else:
            flash('Invalid username, password, or user is not a creator', 'error')
    
    return render_template('creator_login.html', form=form)


@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    form = AdminLoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        admin = User.query.filter_by(username=username).first()

        if admin and check_password_hash(admin.password, password):
            return redirect(url_for('admin_dashboard'))  
        else:
            flash('Invalid username or password', 'error')

    return render_template('admin_login.html', form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()

    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')  # Decode the hashed password
        new_user = User(
            id=form.id.data,
            username=form.username.data,
            email=form.email.data,
            password=hashed_password,
            role=form.role.data
        )
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('home'))
        

    return render_template('register.html', form=form)

@app.route('/user_dashboard')
def user_dashboard():
    songs = Song.query.all()
    playlists = Playlist.query.all()
    albums = Album.query.all()
    user_id = session.get('user_id', None)

    return render_template('user_dashboard.html', songs=songs,playlists=playlists,user_id=user_id,albums=albums)

@app.route('/user/<int:user_id>')
def user_profile(user_id):
    user = User.query.get_or_404(user_id)
    return render_template('user.html', user=user)

@app.route('/register_as_creator', methods=['POST'])
def register_as_creator():
    user_id = session.get('user_id')


    user = User.query.get(user_id)
    user.creator = True
    db.session.commit()

    return redirect(url_for('creator_page'))  

@app.route('/creator_page')
def creator_page():

    user_id = session.get('user_id', None)

    return render_template('creator_page.html',user_id = user_id)

@app.route('/creator_dashboard/<int:user_id>')
def creator_profile(user_id):
    user = User.query.get_or_404(user_id)
    songs = Song.query.filter_by(artist_id=user_id).all()
    albums = Album.query.filter_by(created_by=user.username).count()
    songs_count = Song.query.filter_by(artist_id=user_id).count()

    total_rating = sum(song.average_rating() for song in songs)
    count = len(songs)
    avg_rating = total_rating / count if count > 0 else 0

    return render_template('creator_dashboard.html', user=user,songs=songs,songs_count = songs_count,albums = albums,avg_rating = avg_rating)

@app.route('/song_details', methods=['GET', 'POST'])
def song_details():
    form = SongDetailsForm()
    
    if request.method == 'POST' and form.validate():

        song_id = form.id.data
        title = form.title.data
        lyrics = form.lyrics.data
        duration = form.duration.data
        release_date = form.release_date.data

        audio_file = form.audio_file.data
        song_picture_file = form.song_picture.data
    
        audio_filename = secure_filename(audio_file.filename)

        audio_file.save(os.path.join(app.config['UPLOAD_FOLDER_1'],audio_filename))
        audio_file=audio_filename


      
        song_picture_filename = secure_filename(song_picture_file.filename)
        song_picture_name = str(unique_id.uuid1())+"_"+song_picture_filename

        song_picture_file.save(os.path.join(app.config['UPLOAD_FOLDER'],song_picture_name))

        song_picture_file = song_picture_name  

        user_id = session.get('user_id', None)


        new_song = Song(
            id=song_id,
            title=title,
            artist_id=user_id,  # Set the artist_id to the user_id from the session
            lyrics=lyrics,
            duration=duration,
            release_date=release_date,
            audio_file=audio_filename,  
            song_picture=song_picture_file

        )

        db.session.add(new_song)
        db.session.commit()

        return redirect(url_for('creator_page'))
    
    return render_template('song_details.html', form=form)

@app.route("/search")
def search():
    queries=request.args.get("queries")

    if queries:
        results = Song.query.filter((Song.title.ilike(queries))).order_by(Song.id.asc(), Song.release_date.desc()).limit(100).all()
    else:
        results = []
    return render_template("song_edit_page.html",results=results)


@app.route('/song_edit_page')
def song_edit_page():
    user_id = session.get('user_id', None)
    songs = Song.query.filter_by(artist_id=user_id).all()
  
    return render_template('song_edit_page.html',songs=songs)

@app.route('/edit_song/<int:song_id>', methods=['GET', 'POST'])
def edit_song(song_id):
    # Query the song by its ID
    song = Song.query.get(song_id)

    if not song:
        flash('Song not found', 'error')
        return redirect(url_for('song_edit_page'))

    if request.method == 'POST':
        # Get updated data from the form
        new_lyrics = request.form.get('lyrics')
        new_title = request.form.get('title')
        # Update the song data
        song.lyrics = new_lyrics
        song.title = new_title
        db.session.commit()
        return redirect(url_for('song_edit_page'))

    return render_template('edit_song.html', song=song)

@app.route('/delete__song/<int:song_id>', methods=['GET','POST'])
def delete__song(song_id):
    song = Song.query.get_or_404(song_id)
    db.session.delete(song)
    db.session.commit()
    return redirect(url_for('song_edit_page'))

@app.route('/create_playlist', methods=['GET', 'POST'])
def create_playlist():
    form = PlaylistForm()

    if request.method == 'POST' and form.validate_on_submit():

        playlist_name = form.title.data
        created_by = User.query.get(session['user_id']).username  # Get username from the session
        playlist_desc = form.description.data
        public_status = True  # Default to True

        new_playlist = Playlist(
            title=playlist_name,
            created_by=created_by,
            description=playlist_desc,
            public_status=public_status
        )

        db.session.add(new_playlist)
        db.session.commit()

        return redirect(url_for('user_dashboard'))  

    return render_template('create_playlist.html', form=form)

@app.route("/playlists")
def show_all_playlists():

    all_playlists = Playlist.query.all()
    return render_template("playlists.html", playlists=all_playlists)

@app.route("/playlists/<int:playlist_id>")
def show_playlist(playlist_id):
    """Show detail on specific playlist."""

    
    playlist = Playlist.query.get_or_404(playlist_id)
    songs_in_playlist = playlist_song.query.filter_by(playlist_id=playlist_id).all()
    song_ids = [playlist_song.song_id for playlist_song in songs_in_playlist]
    songs = Song.query.filter(Song.id.in_(song_ids)).all()
    return render_template("playlist.html", playlist=playlist,songs=songs)

@app.route("/playlists/add", methods=["GET", "POST"])
def add_playlist():

    form = PlaylistForm()

    if request.method == 'POST' and form.validate_on_submit():

        playlist_name = form.title.data
        created_by = User.query.get(session['user_id']).username  # Get username from the session
        playlist_desc = form.description.data
        public_status = True  # Default to True

        new_playlist = Playlist(
            title=playlist_name,
            created_by=created_by,
            description=playlist_desc,
            public_status=public_status
        )

        db.session.add(new_playlist)
        db.session.commit()

        return redirect("/playlists")

    return render_template("create_playlist.html", form=form)

@app.route("/songs/<int:song_id>")
def show_song(song_id):
    """return a specific song"""

    song = Song.query.get_or_404(song_id)
    return render_template("song.html", song=song)

@app.route('/playlists/<int:playlist_id>/add_song', methods=['GET', 'POST'])
def add_song_to_playlist(playlist_id):
    playlist = Playlist.query.get_or_404(playlist_id)
    form = AddSongToPlaylistForm()

    all_songs = Song.query.all()


    form.set_song_choices(all_songs)
    
    if form.validate_on_submit():
        song_id = form.song.data
        song = Song.query.get(song_id)

        if song:
            playlist_song_1 = playlist_song(playlist_id=playlist.id, song_id=song.id)
            db.session.add(playlist_song_1)
            db.session.commit()
            
        return redirect("/playlists")

    return render_template('add_song_to_playlist.html', playlist=playlist, form=form)

@app.route('/songs/<int:id>/rate', methods=['POST'])
def rate_song(id):
    if request.method == 'POST':
        
        u_id = session.get('user_id', None)

        song_id = id
        user_id = u_id
        rating = int(request.form['rating'])

        new_rating = Rating(song_id=song_id, user_id=user_id, rating=rating)
        db.session.add(new_rating)
        db.session.commit()
        return redirect("/user_dashboard")

    return render_template('user_dashboard.html')

@app.route('/admin_dashboard')
def admin_dashboard(): 

    total_users = User.query.count()
    creator_users = User.query.filter_by(creator=True).count()
    tracks = Song.query.count()
    total_albums = Album.query.count()

    songs = Song.query.all()
    ratings = Rating.query.all()


    data = {'Song': [song.title for song in songs],
            'Rating': [ song.average_rating() for song in songs]}  

    df = pd.DataFrame(data)

    fig = px.bar(df, x='Song', y='Rating', title='Songs and Ratings', labels={'Rating': 'Average Rating'})

    rating_graph = fig.to_html(full_html=False)

    creator_data = db.session.query(Song.artist_id, db.func.count(Song.id).label('count')).group_by(Song.artist_id).all()
    df1 = pd.DataFrame(creator_data, columns=['creator', 'count'])
    fig1 = px.bar(df1, x='creator', y='count', title='Creator Statistics')
    creator_graph = fig1.to_html(full_html=False)



    return render_template('admin_dashboard.html', total_users=total_users, creator_users=creator_users,tracks=tracks,songs=songs,ratings=ratings,rating_graph=rating_graph,creator_graph=creator_graph,total_albums = total_albums)

@app.route("/albums")
def show_all_albums():

    all_albums = Album.query.all()
    return render_template("albums.html", albums=all_albums)

@app.route("/albums/<int:album_id>")
def show_album(album_id):

    
    query = album_song.query.filter_by(album_id=album_id).all()
    songs = [result.song_id for result in query]
    songs_details = Song.query.filter(Song.id.in_(songs)).all()
    user_id = session.get('user_id', None)
    user = User.query.get_or_404(user_id)
  

    
    album = Album.query.get_or_404(album_id)
    return render_template("album.html", album=album,songs_details=songs_details,user=user)

@app.route("/albums/add", methods=["GET", "POST"])
def add_album():

    form = AlbumForm()

    if request.method == 'POST' and form.validate_on_submit():

        album_name = form.title.data
        genre = form.genre.data
        created_by = User.query.get(session['user_id']).username  # Get username from the session

        new_album = Album(
            title=album_name,
            genre=genre,
            created_by=created_by
        )

        db.session.add(new_album)
        db.session.commit()

        return redirect("/albums")

    return render_template("create_album.html", form=form)

@app.route('/albums/<int:album_id>/add_song', methods=['GET', 'POST'])
def add_song_to_album(album_id):
    album = Album.query.get_or_404(album_id)
    form = AddSongToAlbumForm()

    all_songs = Song.query.all()

    # Set choices for the 'song' field in the form
    form.set_song_choices(all_songs)
    
    if form.validate_on_submit():
        song_id = form.song.data
        song = Song.query.get(song_id)

        if song:
            album_song_1 = album_song(album_id=album.id, song_id=song.id)
            db.session.add(album_song_1)
            db.session.commit()
            
        return redirect("/albums")

    return render_template('album_add_page.html', album=album, form=form)

@app.route("/tracks")
def show_all_songs():

    all_songs = Song.query.all()
    return render_template("tracks.html", songs=all_songs)

@app.route('/tracks/<int:id>/delete', methods=['POST'])
def delete_song(id):
    song = Song.query.get_or_404(id)
    db.session.delete(song)
    db.session.commit()
    return redirect("/tracks")

@app.route("/user_search")
def user_search():
    queries=request.args.get("queries")
    songs = Song.query.all()
    rate=['1','2','3','4','5']
    results1 = results2 = []

    if queries in rate:
        results2 = [song for song in songs if int(song.average_rating()) == int(queries)]
    elif queries:
        results1 = Song.query.filter((Song.title.ilike(queries))).order_by(Song.id.asc(), Song.release_date.desc()).limit(100).all()
    else:
        results1 = results2 = []
    
    results = results1+results2


    return render_template("search.html",results=results)

@app.route("/user_album_search")
def user_album_search():
    queries1=request.args.get("queries1")
  
    if queries1:
        album_results1 = Album.query.filter((Album.title.ilike(queries1))).order_by(Album.id.asc()).limit(100).all()
        album_results2 = Album.query.filter((Album.genre.ilike(queries1))).order_by(Album.id.asc()).limit(100).all()

    album_results =  album_results1+album_results2

    return render_template("search.html",album_results=album_results)

@app.route("/blacklist")
def show_all_creators():

    all_creators = User.query.filter_by(creator=True).all()
    return render_template("blacklist.html", all_creators=all_creators)

@app.route('/user/<int:user_id>',methods=['POST'])
def blacklist_creator(user_id):
    user = User.query.get_or_404(user_id)

    user.blacklist = True
    db.session.commit()

    return render_template('blacklist.html')


if __name__ == '__main__':
    app.debug = True
    app.run()