import os
import flask
import requests
import json
import urllib.parse
import google.oauth2.credentials
import google_auth_oauthlib.flow
import googleapiclient.discovery
import pprint
import sys
import subprocess
import spotipy
import spotipy.util as util

clientId = ''
clientSecret = ''
clientRedirect = 'https://google.com/'

username = ''
scope='user-library-read'

os.environ["SPOTIPY_CLIENT_ID"] = clientId
os.environ["SPOTIPY_CLIENT_SECRET"] = clientSecret
os.environ["SPOTIPY_REDIRECT_URI"] = clientRedirect
token = util.prompt_for_user_token(username, scope)

CLIENT_SECRETS_FILE = ''

SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl']
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'
API_KEY = ''

app = flask.Flask(__name__)
app.secret_key = ''


@app.route('/')
def index():
  return print_index_table()


@app.route('/test')
def test_api_request():
	if 'credentials' not in flask.session:
		return flask.redirect('authorize')
		# Load credentials from the session.
	credentials = google.oauth2.credentials.Credentials(
		**flask.session['credentials'])

	youtube = googleapiclient.discovery.build(
	API_SERVICE_NAME, API_VERSION, credentials=credentials)
	d={}
	x=0
	if token:
	# Pull data from spotify
		sp=spotipy.Spotify(auth=token)
		results = sp.current_user()
		searchResults = sp.user_playlist_tracks('', '', offset=0) # enter Spotify account username and playlist hash
		for item in searchResults['items']:
			track = item['track']
			song = track['name'] + ' - ' + track['artists'][0]['name']   
			name = urllib.parse.quote_plus(song)
			url = 'https://www.googleapis.com/youtube/v3/search?part=snippet&q='+name+'&maxResults=1&type=video&order=relevance&key='+API_KEY
			response = requests.get(url).json()
			for respons in response['items']:
				vidId =respons['id']['videoId']
			d['string{0}'.format(x)]=youtube.playlistItems().insert(
				part='snippet',
				body=dict(
					snippet=dict(
						playlistId= '', # enter valid YouTube playlist ID
						resourceId=dict(
							kind= 'youtube#video',
							videoId= vidId
						)
					)
				)
			).execute()
			x+=1
	else:
		print("Can't get token for", username)
	flask.session['credentials'] = credentials_to_dict(credentials)
	return flask.jsonify(results=d)

@app.route('/authorize')
def authorize():
  # Create flow instance to manage the OAuth 2.0 Authorization Grant Flow steps.
  flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
      CLIENT_SECRETS_FILE, scopes=SCOPES)

  flow.redirect_uri = flask.url_for('oauth2callback', _external=True)

  authorization_url, state = flow.authorization_url(
      # Enable offline access so that you can refresh an access token without
      # re-prompting the user for permission. Recommended for web server apps.
      access_type='offline',
      # Enable incremental authorization. Recommended as a best practice.
      include_granted_scopes='true')

  # Store the state so the callback can verify the auth server response.
  flask.session['state'] = state
  return flask.redirect(authorization_url)


@app.route('/oauth2callback')
def oauth2callback():
  # Specify the state when creating the flow in the callback so that it can
  # verified in the authorization server response.
  state = flask.session['state']

  flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
      CLIENT_SECRETS_FILE, scopes=SCOPES, state=state)
  flow.redirect_uri = flask.url_for('oauth2callback', _external=True)

  # Use the authorization server's response to fetch the OAuth 2.0 tokens.
  authorization_response = flask.request.url
  flow.fetch_token(authorization_response=authorization_response)

  # Store credentials in the session.
  # ACTION ITEM: In a production app, you likely want to save these
  #              credentials in a persistent database instead.
  credentials = flow.credentials
  flask.session['credentials'] = credentials_to_dict(credentials)

  return flask.redirect(flask.url_for('test_api_request'))

@app.route('/revoke')
def revoke():
  if 'credentials' not in flask.session:
    return ('You need to <a href="/authorize">authorize</a> before ' +
            'testing the code to revoke credentials.')

  credentials = google.oauth2.credentials.Credentials(
    **flask.session['credentials'])

  revoke = requests.post('https://accounts.google.com/o/oauth2/revoke',
      params={'token': credentials.token},
      headers = {'content-type': 'application/x-www-form-urlencoded'})

  status_code = getattr(revoke, 'status_code')
  if status_code == 200:
    return('Credentials successfully revoked.' + print_index_table())
  else:
    return('An error occurred.' + print_index_table())


@app.route('/clear')
def clear_credentials():
  if 'credentials' in flask.session:
    del flask.session['credentials']
  return ('Credentials have been cleared.<br><br>' +
          print_index_table())


def credentials_to_dict(credentials):
  return {'token': credentials.token,
          'refresh_token': credentials.refresh_token,
          'token_uri': credentials.token_uri,
          'client_id': credentials.client_id,
          'client_secret': credentials.client_secret,
          'scopes': credentials.scopes}

def print_index_table():
  return ('<table>' +
          '<tr><td><a href="/test">Test an API request</a></td>' +
          '<td>Submit an API request and see a formatted JSON response. ' +
          '    Go through the authorization flow if there are no stored ' +
          '    credentials for the user.</td></tr>' +
          '<tr><td><a href="/authorize">Test the auth flow directly</a></td>' +
          '<td>Go directly to the authorization flow. If there are stored ' +
          '    credentials, you still might not be prompted to reauthorize ' +
          '    the application.</td></tr>' +
          '<tr><td><a href="/revoke">Revoke current credentials</a></td>' +
          '<td>Revoke the access token associated with the current user ' +
          '    session. After revoking credentials, if you go to the test ' +
          '    page, you should see an <code>invalid_grant</code> error.' +
          '</td></tr>' +
          '<tr><td><a href="/clear">Clear Flask session credentials</a></td>' +
          '<td>Clear the access token currently stored in the user session. ' +
          '    After clearing the token, if you <a href="/test">test the ' +
          '    API request</a> again, you should go back to the auth flow.' +
          '</td></tr></table>')


if __name__ == '__main__':
  os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app.run('localhost', 8080, debug=True)
