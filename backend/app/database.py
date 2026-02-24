import os
from supabase import create_client, Client
from dotenv import load_dotenv
import time
from functools import wraps
import logging

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

logger = logging.getLogger(__name__)

# Create a fresh client instance
def get_supabase_client():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize global client
supabase: Client = get_supabase_client()

# Retry decorator for database operations with exponential backoff
def retry_on_disconnect(max_retries=5, initial_delay=0.3):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            global supabase
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    error_msg = str(e).lower()
                    
                    # Check if it's a connection-related error
                    is_connection_error = any([
                        "disconnected" in error_msg,
                        "server disconnected" in error_msg,
                        "remoteprotocol" in error_msg,
                        "connection" in error_msg,
                        "timeout" in error_msg,
                        "refused" in error_msg,
                        "reset" in error_msg,
                    ])
                    
                    if is_connection_error and attempt < max_retries - 1:
                        delay = initial_delay * (2 ** attempt)  # Exponential backoff
                        logger.warning(f"Database connection error on attempt {attempt + 1}/{max_retries}. Retrying in {delay}s: {str(e)[:100]}")
                        time.sleep(delay)
                        
                        # Recreate client with fresh connection
                        try:
                            supabase = get_supabase_client()
                        except Exception as client_err:
                            logger.error(f"Failed to recreate client: {client_err}")
                        continue
                    
                    # If not a connection error or max retries exceeded
                    if not is_connection_error:
                        logger.error(f"Non-connection error in {func.__name__}: {str(e)[:200]}")
                        raise
            
            logger.error(f"Max retries ({max_retries}) exceeded for {func.__name__}")
            raise last_error
        
        return wrapper
    return decorator

