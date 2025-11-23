# Sherlock
-----
Extract interesting information about redditors from their submissions and comments. Outputs data in JSON format.

## Setup
-----
* Run `pip install -r requirements.txt` to install dependencies.
* Get Reddit API credentials from https://www.reddit.com/prefs/apps
* Create .env file in the root directory containing:

```
REDDIT_CLIENT_ID=your_client_id_here
REDDIT_SECRET=your_secret_here
REDDIT_USER_AGENT=sherlock/1.0
```

## Authentication
-----
Sherlock uses Reddit's OAuth2 client credentials flow for server-to-server authentication. The authentication system includes:

- **Automatic token refresh**: Tokens are refreshed automatically when they expire
- **Rate limiting**: Built-in rate limiting to respect Reddit's API limits (60 requests/minute)
- **Error handling**: Comprehensive error handling for network issues, authentication failures, and rate limits
- **Retry logic**: Exponential backoff retry logic for failed requests
- **Logging**: Detailed logging for debugging and monitoring

## Security Notes
-----
- Never commit your `.env` file or API credentials to version control
- The application uses read-only API access and only fetches public user data
- All API calls are properly authenticated and rate-limited

## Usage
-----
```
python sherlock.py <reddit-username>
```

## Example
-------

### Command:
```
python sherlock.py MemoryEmptyAgain
```

### Output:
```
Processing user MemoryEmptyAgain
Data saved to MemoryEmptyAgain.json
Processing complete... 0:00:05.465406
```

## License
-------
MIT License
