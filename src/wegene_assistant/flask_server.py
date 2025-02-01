from flask import Flask, request
from oauthlib.oauth2 import WebApplicationClient
import requests
import redislite
import os
import sys
from dotenv import load_dotenv
import logging
from werkzeug.serving import WSGIRequestHandler


# Load environment variables
load_dotenv()

# Initialize RedisLite
redis_db = redislite.Redis(os.getenv('REDIS_DB_PATH'))

# WeGene OAuth configuration
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # 禁用HTTPS验证
WEGENE_CLIENT_ID = os.getenv('WEGENE_CLIENT_ID')
WEGENE_CLIENT_SECRET = os.getenv('WEGENE_CLIENT_SECRET')
WEGENE_TOKEN_URL = "https://api.wegene.com/token/"
REDIRECT_URI = "http://localhost:8787/oauth/callback"  # 改为HTTP


def create_flask_app():

    # Remove logs so flask output will not interfere with MCP messages
    cli = sys.modules['flask.cli']
    cli.show_server_banner = lambda *x: None

    app = Flask(__name__)

    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)   

    client = WebApplicationClient(WEGENE_CLIENT_ID)

    @app.route('/oauth/callback')
    def oauth_callback():
        code = request.args.get('code')
        
        # Prepare token request
        token_url, headers, body = client.prepare_token_request(
            WEGENE_TOKEN_URL,
            authorization_response=request.url,
            code=code,
            client_id=WEGENE_CLIENT_ID,
            client_secret=WEGENE_CLIENT_SECRET,
            scope="basic names athletigen skin psychology risk health",
        )
        
        # Send token request
        token_response = requests.post(
            token_url,
            headers=headers,
            data=body
        )

        # Parse token response
        client.parse_request_body_response(token_response.text)
        
        # Store access token in Redis with 24h expiration
        redis_db.set('wegene_access_token', client.token['access_token'], ex=86400)
        
        return "Authorization successful! You can now close this window."

    return app


def run_flask(): 
    app = create_flask_app()
    app.run(host='0.0.0.0', port=8787, debug=False, use_reloader=False)