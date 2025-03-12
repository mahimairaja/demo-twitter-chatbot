import os
import logging
from typing import Optional, List
from datetime import datetime
import asyncio
from fastapi import FastAPI, HTTPException, APIRouter, BackgroundTasks
import tweepy
from dotenv import load_dotenv
from pydantic import BaseModel
import time
import threading
import json

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

# Initialize background task for checking mentions
mention_check_task = None
mention_check_running = False

# Pydantic models for request validation
class TweetRequest(BaseModel):
    text: str

# Create routers for different endpoint groups
base_router = APIRouter(tags=["General"])
account_router = APIRouter(prefix="/account", tags=["Account"])
tweet_router = APIRouter(prefix="/tweet", tags=["Tweets"])
system_router = APIRouter(prefix="/system", tags=["System"])
bot_router = APIRouter(prefix="/bot", tags=["Bot"])

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

# Bot Endpoints
class BotConfig(BaseModel):
    enabled: bool = True
    check_interval_seconds: int = 60
    max_mentions_per_check: int = 10
    response_prefix: Optional[str] = None
    use_llm: bool = False
    llm_system_prompt: str = "You are a helpful Twitter bot that responds to users concisely and accurately."
    tweet_max_length: int = 280
    store_processed_mentions: bool = True

class LLMResponse(BaseModel):
    text: str

bot_config = BotConfig(
    enabled=False  # Disabled by default
)

# Store for processed mentions to avoid duplicate replies
processed_mentions = set()

@bot_router.get("/status")
async def get_bot_status():
    """Get the current status of the Twitter reply bot."""
    return {
        "enabled": bot_config.enabled,
        "check_interval_seconds": bot_config.check_interval_seconds,
        "max_mentions_per_check": bot_config.max_mentions_per_check,
        "response_prefix": bot_config.response_prefix
    }

@bot_router.post("/configure")
async def configure_bot(config: BotConfig):
    """Configure the Twitter reply bot settings."""
    global bot_config
    bot_config = config
    return {"message": "Bot configuration updated successfully", "config": bot_config}

@bot_router.post("/enable")
async def enable_bot():
    """Enable the Twitter reply bot."""
    global bot_config, mention_check_task
    bot_config.enabled = True
    
    # Start background task if not already running
    if mention_check_task is None:
        start_background_mention_check()
        
    return {"message": "Twitter reply bot enabled", "status": get_bot_status()}

@bot_router.post("/disable")
async def disable_bot():
    """Disable the Twitter reply bot."""
    global bot_config, mention_check_task, mention_check_running
    bot_config.enabled = False
    
    # Stop background task if running
    mention_check_running = False
    if mention_check_task:
        mention_check_task = None
        
    return {"message": "Twitter reply bot disabled", "status": get_bot_status()}

@bot_router.post("/check-mentions")
async def check_mentions(background_tasks: BackgroundTasks):
    """Manually trigger a check for mentions and respond to them."""
    if not bot_config.enabled:
        return {"message": "Bot is currently disabled. Enable it first."}
    
    background_tasks.add_task(process_mentions)
    return {"message": "Checking for mentions in the background"}

def start_background_mention_check():
    """Start a background thread to periodically check for mentions."""
    global mention_check_task, mention_check_running
    
    if mention_check_running:
        return
    
    mention_check_running = True
    
    def run_mention_check():
        global mention_check_running
        logger.info(f"Starting automated mention check every {bot_config.check_interval_seconds} seconds")
        
        while mention_check_running and bot_config.enabled:
            try:
                # Create an event loop for the background thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Run the process_mentions coroutine
                loop.run_until_complete(process_mentions())
                loop.close()
                
                # Sleep for the configured interval
                time.sleep(bot_config.check_interval_seconds)
            except Exception as e:
                logger.error(f"Error in background mention check: {e}")
                time.sleep(30)  # Wait 30 seconds on error before retrying
        
        logger.info("Stopped automated mention check")
        mention_check_running = False
    
    # Create and start the background thread
    mention_check_task = threading.Thread(target=run_mention_check)
    mention_check_task.daemon = True  # Thread will exit when main program exits
    mention_check_task.start()
    
    return {"message": "Background mention check started"}

# Function to process mentions
async def process_mentions():
    try:
        logger.info("Checking for new mentions...")
        
        # Increment read counter for API usage tracking
        usage.increment_read()
        
        # Get recent mentions
        user_data = client.get_me()
        user_id = user_data.data.id
        
        mentions = client.get_users_mentions(
            id=user_id,
            max_results=bot_config.max_mentions_per_check
        )
        
        if not mentions.data:
            logger.info("No new mentions found.")
            return {"message": "No new mentions found"}
        
        reply_count = 0
        for mention in mentions.data:
            mention_id = mention.id
            
            # Skip already processed mentions
            if bot_config.store_processed_mentions and mention_id in processed_mentions:
                logger.info(f"Skipping already processed mention {mention_id}")
                continue
                
            logger.info(f"Processing mention {mention_id} from user {mention.author_id}")
            
            # Generate a reply
            if bot_config.use_llm:
                reply_text = await generate_llm_reply(mention.text)
            else:
                reply_text = generate_simple_reply(mention.text)
            
            if bot_config.response_prefix:
                reply_text = f"{bot_config.response_prefix} {reply_text}"
                
            # Ensure the tweet doesn't exceed max length
            if len(reply_text) > bot_config.tweet_max_length:
                reply_text = reply_text[:bot_config.tweet_max_length - 3] + "..."
            
            # Reply to the mention
            try:
                response = client.create_tweet(
                    text=reply_text,
                    in_reply_to_tweet_id=mention_id
                )
                
                # Mark as processed
                if bot_config.store_processed_mentions:
                    processed_mentions.add(mention_id)
                
                # Increment post counter
                usage.increment_post()
                
                reply_count += 1
                logger.info(f"Replied to mention {mention_id}")
            except Exception as e:
                logger.error(f"Error replying to mention {mention_id}: {e}")
            
            # Add a small delay between replies to avoid rate limits
            time.sleep(2)
            
        return {"message": f"Processed {reply_count} mentions"}
    
    except Exception as e:
        logger.error(f"Error processing mentions: {e}")
        return {"error": str(e)}

def generate_simple_reply(mention_text):
    """Generate a simple reply to a mention."""
    return f"Thanks for mentioning me! I'm a Twitter bot running on FastAPI. Your message was: '{mention_text}'"

async def generate_llm_reply(mention_text):
    """
    Generate a reply using an LLM (OpenAI GPT, etc).
    
    In a production environment, you would:
    1. Call your LLM API with proper prompt engineering
    2. Process the response to ensure it's appropriate
    3. Handle any API errors or rate limits
    
    This is a mock implementation that simulates an LLM response.
    """
    try:
        # This is where you would call your LLM API
        # Example with OpenAI (commented out):
        """
        import openai
        openai.api_key = os.getenv("OPENAI_API_KEY")
        
        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": bot_config.llm_system_prompt},
                {"role": "user", "content": f"Please respond to this Twitter mention: '{mention_text}'. Keep your response under 280 characters."}
            ],
            max_tokens=100,
            temperature=0.7
        )
        
        return response.choices[0].message.content
        """
        
        # Mock LLM response for demonstration
        logger.info(f"Generating LLM response for: {mention_text}")
        
        # Simulate an LLM response
        sample_responses = [
            f"Thanks for reaching out! I noticed you mentioned '{mention_text}'. How can I help you today?",
            f"I appreciate your mention! I'm a Twitter bot that's here to assist. Regarding '{mention_text}', what would you like to know?",
            f"Hello there! Thanks for the mention. I'm processing your request about '{mention_text}' and will do my best to help."
        ]
        
        import random
        response = random.choice(sample_responses)
        
        # Simulate processing time
        await asyncio.sleep(1)
        
        return response
        
    except Exception as e:
        logger.error(f"Error generating LLM response: {e}")
        return "Thank you for your mention! I'm currently experiencing technical difficulties but will get back to you soon."

# Endpoint to clear the processed mentions cache
@bot_router.post("/clear-cache")
async def clear_processed_mentions():
    """Clear the cache of processed mention IDs."""
    global processed_mentions
    count = len(processed_mentions)
    processed_mentions.clear()
    return {"message": f"Cleared {count} processed mention IDs from cache"}

# Endpoint to configure LLM settings
@bot_router.post("/configure-llm")
async def configure_llm(use_llm: bool, system_prompt: Optional[str] = None):
    """Configure the LLM settings for the bot."""
    bot_config.use_llm = use_llm
    
    if system_prompt:
        bot_config.llm_system_prompt = system_prompt
        
    return {
        "message": f"LLM settings updated. LLM is {'enabled' if use_llm else 'disabled'}.",
        "use_llm": bot_config.use_llm,
        "system_prompt": bot_config.llm_system_prompt
    }

# Include all routers in the main app
app.include_router(base_router)
app.include_router(account_router)
app.include_router(tweet_router)
app.include_router(system_router)
app.include_router(bot_router)

if __name__ == "__main__":
    import uvicorn
    # Run the application
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
