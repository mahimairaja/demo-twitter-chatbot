# Twitter API Client (Minimal)

A simple Python FastAPI application for accessing basic Twitter/X API v2 information.

## Features

- **Account Information**: Get details about the authenticated Twitter account via the `/account/whoami` endpoint
- **Usage Tracking**: Monitor your API usage against Twitter API v2 free tier limits via the `/system/usage` endpoint
- **Tweet Posting**: Post tweets to your Twitter account via the `/tweet` endpoint

## Twitter API v2 Free Tier Limits

This application tracks and respects the Twitter API v2 free tier limits:
- 500 posts per month (app level)
- 500 posts per month (user level)
- 100 reads per month

The application will log warnings when you approach or exceed these limits.

## Setup

### Prerequisites

- Python 3.8+
- A Twitter Developer Account
- Twitter API v2 credentials

### Environment Variables

Create a `.env` file in the root directory with the following variables:

```
# Twitter API Credentials
TWITTER_API_KEY=your_api_key
TWITTER_API_KEY_SECRET=your_api_key_secret
TWITTER_ACCESS_TOKEN=your_access_token
TWITTER_ACCESS_TOKEN_SECRET=your_access_token_secret
TWITTER_BEARER_TOKEN=your_bearer_token
```

### Installation

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run the application:
   ```
   python main.py
   ```
   
The server will start on `http://localhost:8000`.

## API Endpoints

The API endpoints are organized into logical groups for better structure:

### General Endpoints

- `GET /`: Check if the application is running, returns information about available endpoint groups

### Account Endpoints

- `GET /account/whoami`: Get information about the authenticated Twitter account

### Tweet Endpoints

- `POST /tweet`: Post a new tweet to your Twitter account

### System Endpoints

- `GET /system/usage`: Get current API usage statistics against free tier limits

### Usage Examples

#### Posting a Tweet

```bash
curl -X POST "http://localhost:8000/tweet" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello world from my Twitter API Client!"
  }'
```

#### Getting Account Information

```bash
curl -X GET "http://localhost:8000/account/whoami"
```

#### Checking API Usage

```bash
curl -X GET "http://localhost:8000/system/usage"
```

## Setting Up Twitter API v2 Access

1. Go to the [Twitter Developer Portal](https://developer.twitter.com/en/portal/dashboard)
2. Create a Project and an App within that project
3. Apply for Basic (free tier) access
4. Generate the API Key, API Key Secret, Access Token, and Access Token Secret
5. **Important**: Ensure your app has "Read and Write" permissions enabled for the tweet endpoint to work

## Troubleshooting

If you experience issues with authentication:

1. Ensure your Twitter API credentials are correct in the .env file
2. Verify that your Twitter Developer account is active and in good standing
3. Check the application logs for detailed error messages

## License

MIT
