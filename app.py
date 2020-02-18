#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#


import json
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect
from flask import url_for, jsonify
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
from datetime import datetime


#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#


app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)

migrate = Migrate(app, db)


#----------------------------------------------------------------------------#
# Helpers
#----------------------------------------------------------------------------#


# return the number of upcoming shows, or zero if there are not any
def num_upcoming_shows(shows):
    num_upcoming_shows = 0
    for show in shows:
        if show.start_time > datetime.now():
            num_upcoming_shows += 1
    return num_upcoming_shows


# return the number of past shows, of zero if there are not any
def num_past_shows(shows):
    num_past_shows = 0
    for show in shows:
        if show.start_time < datetime.now():
            num_past_shows += 1
    return num_past_shows


#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#


class Venue(db.Model):
    __tablename__ = 'Venue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    city = db.Column(db.String(120), nullable=False)
    state = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(120), nullable=False)
    image_link = db.Column(db.String(500), nullable=False)
    facebook_link = db.Column(db.String(120), nullable=True)
    genres = db.Column(db.ARRAY(db.String), nullable=False)
    website = db.Column(db.String(240), nullable=True)
    seeking_talent = db.Column(db.Boolean, nullable=False, default=True)
    seeking_description = db.Column(db.String(500), nullable=False, default='We are looking for artists to perform here!')
    shows = db.relationship('Show', backref='venue', lazy=True)


class Artist(db.Model):
    __tablename__ = 'Artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False, unique=True)
    city = db.Column(db.String(120), nullable=False)
    state = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(120), nullable=False)
    genres = db.Column(db.ARRAY(db.String), nullable=False)
    image_link = db.Column(db.String(500), nullable=False)
    facebook_link = db.Column(db.String(120), nullable=True)
    website = db.Column(db.String(240), nullable=True)
    seeking_venue = db.Column(db.Boolean, nullable=False, default=True)
    seeking_description = db.Column(db.String(500), nullable=False, default='Looking for a place to perform!')
    shows = db.relationship('Show', backref='artist', lazy=True)


class Show(db.Model):
    __tablename__ = 'Shows'

    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.DateTime(), nullable=False)
    venue_id = db.Column(db.Integer, db.ForeignKey('Venue.id'), nullable=False)
    artist_id = db.Column(db.Integer, db.ForeignKey('Artist.id'), nullable=False)


#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#


def format_datetime(value, format='medium'):
    date = dateutil.parser.parse(value)
    if format == 'full':
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == 'medium':
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format)


app.jinja_env.filters['datetime'] = format_datetime


#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#


# homepage
@app.route('/')
def index():
    return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------


# show the venues grouped by location
@app.route('/venues')
def venues():
    data = []

    try:
        # get the city state combos for the venues
        areas = Venue.query.with_entities(Venue.city, Venue.state).group_by(Venue.city, Venue.state).all()

        for area in areas:
            # group the venues by location
            locations = Venue.query.filter_by(city=area.city).filter_by(state=area.state).all()
            # setup venues on each loop of areas
            venues = []
            # prepare venue data to append to location
            for venue in locations:

                venues.append({
                    "id": venue.id,
                    "name": venue.name,
                    "num_upcoming_shows": num_upcoming_shows(venue.shows)
                })

            # setup the data
            data.append({
                "city": area.city,
                "state": area.state,
                "venues": venues
            })

        return render_template('pages/venues.html', areas=data)

    # flash and send user home if fail
    except:

        flash('An error occured!')
        return render_template('pages/home.html')


# allow user to search venues by name
@app.route('/venues/search', methods=['POST'])
def search_venues():
    data = []
    search_term = request.form.get('search_term', '')

    try:
        # find venues matching the search term using ilike
        venues = Venue.query.filter(Venue.name.ilike(f'%{search_term}%')).all()

        # build the id, name and num upcoming shows for each venue in result
        for venue in venues:
            data.append({
              "id": venue.id,
              "name": venue.name,
              "num_upcoming_shows": num_upcoming_shows(venue.shows)
            })

        # build response with the venue data
        response = {
            "count": len(venues),
            "data": data
        }

        return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ''))

    # flash and send user home if fail
    except:

        flash('An error occured!')
        return render_template('pages/home.html')


# show an individual venue page by venue id
@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
    data = []
    upcoming_shows = []
    past_shows = []

    try:

        # get the venue data for the venue with this id
        venue = Venue.query.get(venue_id)

        # join the show and artist tables to fetch artist name, image for venue
        shows = db.session.query(Show).join(Artist).filter(Show.venue_id == venue_id).all()

        for show in shows:

            # append the upcoming shows
            if show.start_time > datetime.now():

                upcoming_shows.append({
                    "artist_id": show.artist_id,
                    "artist_name": show.artist.name,
                    "artist_image_link": show.artist.image_link,
                    "start_time": str(show.start_time)
                })

            # append the past shows
            elif show.start_time < datetime.now():

                past_shows.append({
                    "artist_id": show.artist_id,
                    "artist_name": show.artist.name,
                    "artist_image_link": show.artist.image_link,
                    "start_time": str(show.start_time)
                })

        # build the data
        data = {
            "id": venue.id,
            "name": venue.name,
            "genres": venue.genres,
            "address": venue.address,
            "city": venue.city,
            "state": venue.state,
            "phone": venue.phone,
            "website": venue.website,
            "facebook_link": venue.facebook_link,
            "seeking_talent": venue.seeking_talent,
            "seeking_description": venue.seeking_description,
            "image_link": venue.image_link,
            "past_shows": past_shows,
            "upcoming_shows": upcoming_shows,
            "past_shows_count": num_past_shows(venue.shows),
            "upcoming_shows_count": num_upcoming_shows(venue.shows)
        }

        return render_template('pages/show_venue.html', venue=data)

    # if vevnue id is not valid, flash and send home
    except:

        flash('Not a valid venue id!')
        return render_template('pages/home.html')


#  Create Venue
#  ----------------------------------------------------------------


# get the venue form
@app.route('/venues/create', methods=['GET'])
def create_venue_form():
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)


# create a new venue
@app.route('/venues/create', methods=['POST'])
def create_venue_submission():

    try:

        name = request.form['name']
        city = request.form['city']
        state = request.form['state']
        address = request.form['address']
        phone = request.form['phone']
        image_link = request.form['image_link']
        facebook_link = request.form['facebook_link']
        genres = request.form.getlist('genres')
        website = request.form['website']
        seeking_talent = True
        seeking_description = request.form['seeking_description']
        venue = Venue(name=name, city=city, state=state, address=address,
                      phone=phone, image_link=image_link,
                      facebook_link=facebook_link, genres=genres,
                      website=website, seeking_talent=seeking_talent,
                      seeking_description=seeking_description)
        db.session.add(venue)
        db.session.commit()
        flash('Venue ' + request.form['name'] + ' was successfully listed!')

    except:

        db.session.rollback()
        flash('An error occurred. Venue ' + venue.name + ' could not be listed.')

    finally:

        db.session.close()
        return render_template('pages/home.html')


# allow deletion of a venue by venue id
@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):

    # delete the venue for given id and flash success
    try:

        Venue.query.get(venue_id).delete()
        db.session.commit()
        flash('Venue successfully deleted!')

    # rollback database session and flash error
    except:

        db.session.rollback()
        flash('An error occurred while trying to delete.')

    # close the database session
    finally:

        db.session.close()

    return None


#  Artists
#  ----------------------------------------------------------------


# show all the artists
@app.route('/artists')
def artists():
    data = Artist.query.all()
    return render_template('pages/artists.html', artists=data)


# allow user to search for artists by name
@app.route('/artists/search', methods=['POST'])
def search_artists():

    data = []
    search_term = request.form.get('search_term', '')

    try:

        # find artists matching the search term using ilike
        artists = Artist.query.filter(Artist.name.ilike(f'%{search_term}%')).all()

        # put results in data
        for artist in artists:
            data.append({
              "id": artist.id,
              "name": artist.name,
              "num_upcoming_shows": num_upcoming_shows(artist.shows)
            })

        # prepare respose with a count and the data
        response={
            "count": len(artists),
            "data": data
        }

        return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))

    #flash and send user home if fail
    except:

        flash('An error occured!')
        return render_template('pages/home.html')


# show the artist page given some artist id
@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
    data = []
    upcoming_shows = []
    past_shows = []

    try:

        # get the artist data for the artist with this id
        artist = Artist.query.get(artist_id)

        # join the shows and venue tables to have venue name, venue image
        shows = db.session.query(Show).join(Venue).filter(Show.artist_id==artist_id).all()

        for show in shows:

            # add the upcoming shows
            if show.start_time > datetime.now():

                upcoming_shows.append({
                    "venue_id": show.venue_id,
                    "venue_name": show.venue.name,
                    "venue_image_link": show.venue.image_link,
                    "start_time": str(show.start_time)
                })

            # add the past shows
            elif show.start_time < datetime.now():

                past_shows.append({
                    "venue_id": show.venue_id,
                    "venue_name": show.venue.name,
                    "venue_image_link": show.venue.image_link,
                    "start_time": str(show.start_time)
                })

        # build the data
        data = {
            "id": artist.id,
            "name": artist.name,
            "genres": artist.genres,
            "city": artist.city,
            "state": artist.state,
            "phone": artist.phone,
            "website": artist.website,
            "facebook_link": artist.facebook_link,
            "seeking_venue": artist.seeking_venue,
            "seeking_description": artist.seeking_description,
            "image_link": artist.image_link,
            "past_shows": past_shows,
            "upcoming_shows": upcoming_shows,
            "past_shows_count": num_past_shows(artist.shows),
            "upcoming_shows_count": num_upcoming_shows(artist.shows)
        }

        return render_template('pages/show_artist.html', artist=data)

    # flash and send use home if artist id is bad or if error
    except:

        flash('Not a valid artist id!')
        return render_template('pages/home.html')


#  Update
#  ----------------------------------------------------------------

# allow user to see existing artist values before editing
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    form = ArtistForm()
    artist = Artist.query.get(artist_id)

    # if the artist id is a valid as function of the query
    if artist:

        form.name.data = artist.name
        form.city.data = artist.city
        form.state.data = artist.state
        form.phone.data = artist.phone
        form.genres.data = artist.genres
        form.facebook_link.data = artist.facebook_link
        form.website.data = artist.website
        form.image_link.data = artist.image_link
        form.seeking_venue.data = artist.seeking_venue
        form.seeking_description.data = artist.seeking_description
        return render_template('forms/edit_artist.html', form=form, artist=artist)

    # otherwise send user back to homepage
    else:

        flash('Artist id is not valid!')
        return render_template('pages/home.html')


# allow user to submit new values to update an existing artist
@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
    artist = Artist.query.get(artist_id)

    # store form values to the artist record
    try:

        artist.name = request.form['name']
        artist.city = request.form['city']
        artist.state = request.form['state']
        artist.phone = request.form['phone']
        artist.genres = request.form.getlist('genres')
        artist.image_link = request.form['image_link']
        artist.facebook_link = request.form['facebook_link']
        artist.website = request.form['website']
        artist.seeking_venue = True
        artist.seeking_description = request.form['seeking_description']
        db.session.commit()
        flash('Artist ' + request.form['name'] + ' was successfully edited!')

    # rollback and flash if fail
    except:

        db.session.rollback()
        flash('Artist ' + request.form['name'] + ' edit failed!')

    # close the database session
    finally:

        db.session.close()


    return redirect(url_for('show_artist', artist_id=artist_id))


# all user to see existing venue data before editing
@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    form = VenueForm()
    venue = Venue.query.get(venue_id)

    # if the venue id has results
    if venue:

        form.name.data = venue.name
        form.city.data = venue.city
        form.state.data = venue.state
        form.address.data = venue.address
        form.phone.data = venue.phone
        form.genres.data = venue.genres
        form.facebook_link.data = venue.facebook_link
        form.website.data = venue.website
        form.image_link.data = venue.image_link
        form.seeking_talent.data = venue.seeking_talent
        form.seeking_description.data = venue.seeking_description
        return render_template('forms/edit_venue.html', form=form, venue=venue)

    #otherwise send user back to homepage
    else:

        flash('Venue id is not valid!')
        return render_template('pages/home.html')


# allow user to edit data for existing venue
@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
    venue = Venue.query.get(venue_id)

    # store new form values for the venue
    try:

        venue.name = request.form['name']
        venue.city = request.form['city']
        venue.state = request.form['state']
        venue.address = request.form['address']
        venue.phone = request.form['phone']
        venue.genres = request.form.getlist('genres')
        venue.image_link = request.form['image_link']
        venue.facebook_link = request.form['facebook_link']
        venue.website = request.form['website']
        venue.seeking_talent = True
        venue.seeking_description = request.form['seeking_description']
        db.session.commit()
        flash('Venue ' + request.form['name'] + ' was successfully edited!')

    # rollback session and flash error on fail
    except:

        db.session.rollback()
        flash('Artist ' + request.form['name'] + ' edit failed!')

    # close the database session
    finally:

        db.session.close()


    return redirect(url_for('show_venue', venue_id=venue_id))


#  Create Artist
#  ----------------------------------------------------------------

# get the artist create form
@app.route('/artists/create', methods=['GET'])
def create_artist_form():
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)


# allow user to submit a new artist
@app.route('/artists/create', methods=['POST'])
def create_artist_submission():

    # store values for the new artist
    try:

        name = request.form['name']
        city = request.form['city']
        state = request.form['state']
        phone = request.form['phone']
        genres = request.form.getlist('genres')
        image_link = request.form['image_link']
        facebook_link = request.form['facebook_link']
        website = request.form['website']
        seeking_venue = True
        seeking_description = request.form['seeking_description']
        artist = Artist(name=name, city=city, state=state, phone=phone,
                        genres=genres, image_link=image_link,
                        facebook_link=facebook_link, website=website,
                        seeking_venue=seeking_venue,
                        seeking_description=seeking_description)
        db.session.add(artist)
        db.session.commit()
        flash('Artist ' + request.form['name'] + ' was successfully listed!')

    # rollback session and flash on error
    except:

        db.session.rollback()
        flash('An error occurred. Artist ' + artist.name + ' could not be listed.')

    # close the database session and send user home
    finally:

        db.session.close()
        return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

# show all the shows
@app.route('/shows')
def shows():
    query = Show.query.order_by(db.desc(Show.start_time))
    data = []

    # list the shows that are in future, not the past shows
    for show in query:

        if show.start_time > datetime.now():

            data.append({
                "artist_id": show.artist_id,
                "artist_name": show.artist.name,
                "artist_image_link": show.artist.image_link,
                "start_time": show.start_time,
                "venue_id": show.venue_id,
                "venue_name": show.venue.name,
            })

    return render_template('pages/shows.html', shows=data)


# get the new show create form
@app.route('/shows/create')
def create_shows():
    # renders form. do not touch.
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)


# allow user to submit a new show
@app.route('/shows/create', methods=['POST'])
def create_show_submission():

    # create a new show record
    try:

        artist_id = request.form['artist_id']
        venue_id = request.form['venue_id']
        start_time = request.form['start_time']
        show = Show(artist_id=artist_id, venue_id=venue_id, start_time=start_time)
        db.session.add(show)
        db.session.commit()
        flash('Show was successfully listed!')

    # rollback database session and flash on error
    except:

        db.session.rollback()
        flash('An error occurred. Show could not be added.')

    # close the database session
    finally:

        db.session.close()
        return render_template('pages/home.html')


# 404 error route
@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


# 500 error route
@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
