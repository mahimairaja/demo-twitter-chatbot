import os
import logging
from typing import Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, APIRouter
import tweepy
from dotenv import load_dotenv
from pydantic import BaseModel

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Twitter API Client (Minimal)")

# Twitter API credentials
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_KEY_SECRET = os.getenv("TWITTER_API_KEY_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")

# Initialize Tweepy client
client = tweepy.Client(
    bearer_token=TWITTER_BEARER_TOKEN,
    consumer_key=TWITTER_API_KEY,
    consumer_secret=TWITTER_API_KEY_SECRET,
    access_token=TWITTER_ACCESS_TOKEN,
    access_token_secret=TWITTER_ACCESS_TOKEN_SECRET
)

# Usage tracking for free tier limits
class UsageTracker:
    def __init__(self):
        self.reads_this_month = 0
        self.posts_this_month_app = 0
        self.posts_this_month_user = 0
        self.last_reset = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
    def increment_read(self):
        self._check_reset()
        self.reads_this_month += 1
        if self.reads_this_month > 100:  # Free tier limit: 100 reads per month
            logger.warning("FREE TIER READ LIMIT EXCEEDED: 100 reads per month")
            
    def increment_post(self):
        self._check_reset()
        self.posts_this_month_app += 1
        self.posts_this_month_user += 1
        
        if self.posts_this_month_app > 500:  # Free tier limit: 500 posts per month (app level)
            logger.warning("FREE TIER APP POST LIMIT EXCEEDED: 500 posts per month")
            
        if self.posts_this_month_user > 500:  # Free tier limit: 500 posts per month (user level)
            logger.warning("FREE TIER USER POST LIMIT EXCEEDED: 500 posts per month")
            
    def _check_reset(self):
        # Reset counters on the first day of each month
        current_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if current_month_start > self.last_reset:
            logger.info("Resetting monthly usage counters")
            self.reads_this_month = 0
            self.posts_this_month_app = 0
            self.posts_this_month_user = 0
            self.last_reset = current_month_start
            
    def get_usage_stats(self):
        self._check_reset()
        return {
            "reads_this_month": self.reads_this_month,
            "posts_this_month_app": self.posts_this_month_app,
            "posts_this_month_user": self.posts_this_month_user,
            "reads_remaining": max(0, 100 - self.reads_this_month),
            "posts_remaining_app": max(0, 500 - self.posts_this_month_app),
            "posts_remaining_user": max(0, 500 - self.posts_this_month_user),
            "last_reset": self.last_reset.isoformat()
        }

# Initialize usage tracker
usage = UsageTracker()

# Pydantic models for request validation
class TweetRequest(BaseModel):
    text: str

# Create routers for different endpoint groups
base_router = APIRouter(tags=["General"])
account_router = APIRouter(prefix="/account", tags=["Account"])
tweet_router = APIRouter(prefix="/tweet", tags=["Tweets"])
system_router = APIRouter(prefix="/system", tags=["System"])

# General Endpoints
@base_router.get("/")
async def root():
    return {"message": "Twitter API Client - Minimal Version", "groups": ["account", "tweet", "system"]}

# Account Endpoints
@account_router.get("/whoami")
async def whoami():
    """Return information about the authenticated Twitter account."""
    try:
        # Increment read counter
        usage.increment_read()
        
        me = client.get_me(user_fields=["username", "name", "description"])
        return {
            "id": me.data.id,
            "username": me.data.username,
            "name": me.data.name,
            "description": me.data.description
        }
    except Exception as e:
        logger.error(f"Error getting user info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Tweet Endpoints
@tweet_router.post("")
async def create_tweet(request: TweetRequest):
    """Post a new tweet with the provided text."""
    try:
        # Increment post counter
        usage.increment_post()
        
        # Post the tweet
        response = client.create_tweet(text=request.text)
        
        return {
            "success": True,
            "tweet_id": response.data["id"],
            "text": request.text
        }
    except tweepy.TweepyException as e:
        logger.error(f"Error posting tweet: {e}")
        
        # Check for permission errors
        if "403" in str(e):
            error_msg = f"Permission error: {e}. Ensure your Twitter app has write permissions enabled in the Twitter Developer Portal."
        else:
            error_msg = str(e)
            
        raise HTTPException(status_code=500, detail=error_msg)
    except Exception as e:
        logger.error(f"Unexpected error posting tweet: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# System Endpoints
@system_router.get("/usage")
async def get_usage():
    """Get current API usage statistics against free tier limits."""
    return usage.get_usage_stats()

# Include all routers in the main app
app.include_router(base_router)
app.include_router(account_router)
app.include_router(tweet_router)
app.include_router(system_router)

if __name__ == "__main__":
    import uvicorn
    # Run the application
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
