import logging
from typing import List, Dict, Any, Optional
from functools import lru_cache
from mastodon import Mastodon
from bs4 import BeautifulSoup
import datetime
from config import MASTODON_API_BASE_URL, MASTODON_ACCESS_TOKEN

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Mastodon client
mastodon = Mastodon(
    access_token=MASTODON_ACCESS_TOKEN,
    api_base_url=MASTODON_API_BASE_URL
)

@lru_cache(maxsize=100)
def get_mastodon_posts(keyword: str, max_results: int = 200) -> List[Dict[str, Any]]:
    """
    Fetches up to `max_results` recent toots (Mastodon entries) containing the hashtag or keyword.
    
    Args:
        keyword: Hashtag or search term to look for (will strip # if present)
        max_results: Maximum number of posts to retrieve
        
    Returns:
        List of dicts containing post text and timestamp
        
    Raises:
        Exception: If Mastodon API call fails
    """
    tag = keyword.lstrip('#')
    
    # Set batch size (Mastodon API typically works best with 40 results per request)
    batch_size = 40
    
    # Calculate how many batches we need
    num_batches = (max_results + batch_size - 1) // batch_size  # Ceiling division
    
    all_posts = []
    max_id = None  # Used for pagination
    
    # Fetch posts in multiple batches
    for batch in range(num_batches):
        try:
            # If we have a max_id from previous batch, use it for pagination
            if max_id:
                statuses = mastodon.timeline_hashtag(tag, limit=batch_size, max_id=max_id)
            else:
                statuses = mastodon.timeline_hashtag(tag, limit=batch_size)
                
            if not statuses:
                # No more results to fetch
                logger.info(f"No more posts found after batch {batch}")
                break
                
            # Process posts in this batch
            for status in statuses:
                plain = BeautifulSoup(status.content, "html.parser").get_text(separator=" ")
                all_posts.append({
                    "text": plain,
                    "timestamp": status.created_at
                })
                
            # Get the ID of the last post for pagination
            if statuses:
                max_id = statuses[-1].id
            
            logger.info(f"Batch {batch+1}: Retrieved {len(statuses)} posts, total so far: {len(all_posts)}")
            
            # If we've reached our target or there are no more results, stop
            if len(all_posts) >= max_results:
                all_posts = all_posts[:max_results]  # Trim to exact max_results
                break
                
        except Exception as e:
            logger.error(f"Error fetching batch {batch+1}: {str(e)}")
            # Continue with what we've got so far
            break
    
    logger.info(f"Total retrieved: {len(all_posts)} posts from Mastodon API for keyword '{keyword}'")
    return all_posts
