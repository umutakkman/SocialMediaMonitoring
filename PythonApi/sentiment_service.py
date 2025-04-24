import json
import re
import logging
import datetime
from collections import defaultdict
from typing import List, Dict, Any, Tuple
from iointel import Agent, Workflow
from config import OPENAI_API_KEY_SENTIMENT, LLM_API_BASE_URL, LLM_MODEL

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_sentiment_with_details(posts: List[Dict[str, Any]], batch_size: int = 50) -> Tuple[Dict[str, int], List[Dict[str, Any]]]:
    """
    Analyze posts in batches to determine sentiment distribution and track individual post sentiments.
    
    Args:
        posts: List of post dictionaries with 'text' field
        batch_size: Number of posts to analyze in each batch
        
    Returns:
        Tuple containing:
        1. Dictionary with percentages for positive, neutral, and negative sentiment
        2. List of posts with sentiment information
    """
    if not posts:
        logger.warning("No posts provided for sentiment analysis")
        return {"positive": 0, "neutral": 0, "negative": 0}, []
        
    logger.info(f"Analyzing {len(posts)} posts with batch size {batch_size}")

    # Create an agent specifically for batch sentiment analysis
    sentiment_agent = Agent(
        name="BatchSentimentAnalyzer",
        instructions=(
            "You are a sentiment analysis expert who analyzes multiple posts at once. "
            "For each batch of posts, count how many are positive, neutral, and negative. "
            "Be objective and consider the language, tone, and context of each post. "
            "Ensure you categorize posts across all three sentiment categories - don't omit neutral sentiments. "
            "When uncertain about a post's sentiment, classify it as neutral rather than guessing."
        ),
        model=LLM_MODEL,
        api_key=OPENAI_API_KEY_SENTIMENT,
        base_url=LLM_API_BASE_URL
    )

    # Track raw sentiment counts (not percentages)
    positive_count = 0
    neutral_count = 0
    negative_count = 0
    post_sentiments = []
    processed_indices = set()  # Track which post indices we've processed
    
    # Process in batches
    for batch_start in range(0, len(posts), batch_size):
        batch_end = min(batch_start + batch_size, len(posts))
        batch = posts[batch_start:batch_end]
        
        if not batch:
            continue
            
        # Combine batch posts with clear separators and post IDs
        post_texts = []
        for i, post in enumerate(batch):
            post_id = batch_start + i
            # Ensure the text field exists and is not empty
            text = post.get('text', '')
            if not text:
                logger.warning(f"Post at index {post_id} has no text content")
                text = "(No content)"
            post_texts.append(f"POST_ID_{post_id}: {text}")
            
        batch_text = "\n\n===== POST START =====\n\n" + "\n\n===== POST END =====\n\n===== POST START =====\n\n".join(post_texts) + "\n\n===== POST END ====="
        
        # Create a workflow for this batch
        workflow = Workflow(text=batch_text, client_mode=False)
        batch_result = workflow.custom(
            name=f"BatchSentiment{batch_start}",
            objective="determine sentiment counts and individual post sentiments",
            instructions=(
                f"Analyze each of the {len(batch)} posts separated by '===== POST START/END ====='. "
                "For each post, determine if it's primarily positive, neutral, or negative. "
                "IMPORTANT: Make sure to use all three categories - don't skip neutral sentiment. "
                "When in doubt, classify as neutral rather than forcing positive or negative. "
                "Count the total number of posts in each category. "
                "Return your answer in this exact JSON format:\n"
                "{\n"
                '  "summary": {\n'
                '    "positive": [number of positive posts],\n'
                '    "neutral": [number of neutral posts],\n'
                '    "negative": [number of negative posts]\n'
                '  },\n'
                '  "individual": [\n'
                '    {"post_id": "POST_ID_0", "sentiment": "positive/neutral/negative"},\n'
                '    {"post_id": "POST_ID_1", "sentiment": "positive/neutral/negative"},\n'
                '    ...\n'
                '  ]\n'
                "}\n\n"
                "The sum of positive, neutral, and negative posts must equal the total number of posts."
            ),
            agents=[sentiment_agent],
        ).run_tasks()
                
        # Extract and validate the result
        result_text = batch_result.get('results', {}).get(f'BatchSentiment{batch_start}', '')
        if not result_text:
            logger.error(f"No result returned for batch starting at {batch_start}")
            continue

        logger.debug(f"Raw result text: {result_text}")
        
        # Extract JSON from the result
        result_data = None
        try:
            # First try direct JSON parsing
            result_data = json.loads(result_text)
        except json.JSONDecodeError:
            # If direct parsing fails, try to extract JSON with regex
            json_match = re.search(r'({[\s\S]*})', result_text)
            if json_match:
                try:
                    result_data = json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    # Further cleanup: remove any non-JSON text within the matched braces
                    json_candidate = json_match.group(1)
                    # More aggressive cleaning might be needed for complex cases
            
            # If no JSON found, use regex to extract sentiment counts and individual sentiments
            if not result_data:
                logger.warning(f"Failed to parse JSON from batch {batch_start}, falling back to regex")
                
                # Extract sentiment counts
                pos_match = re.search(r'positive[^\d]*(\d+)', result_text, re.IGNORECASE)
                neu_match = re.search(r'neutral[^\d]*(\d+)', result_text, re.IGNORECASE)
                neg_match = re.search(r'negative[^\d]*(\d+)', result_text, re.IGNORECASE)
                
                pos_count = int(pos_match.group(1)) if pos_match else 0
                neu_count = int(neu_match.group(1)) if neu_match else 0
                neg_count = int(neg_match.group(1)) if neg_match else 0
                
                # Create a synthetic result_data structure
                result_data = {
                    "summary": {
                        "positive": pos_count,
                        "neutral": neu_count,
                        "negative": neg_count
                    },
                    "individual": []
                }
                
                # Extract individual post sentiments
                pattern = r'POST_ID_(\d+)[^"]+"?sentiment"?:?\s*"?(\w+)"?'
                for match in re.finditer(pattern, result_text, re.IGNORECASE):
                    try:
                        post_id = f"POST_ID_{match.group(1)}"
                        sentiment = match.group(2).lower()
                        # Standardize sentiment value
                        if sentiment in ('pos', 'positive'):
                            sentiment = 'positive'
                        elif sentiment in ('neg', 'negative'):
                            sentiment = 'negative'
                        else:
                            sentiment = 'neutral'
                            
                        result_data["individual"].append({
                            "post_id": post_id,
                            "sentiment": sentiment
                        })
                    except:
                        continue
        
        # Process the result data
        if result_data:
            # Get summary counts
            summary = result_data.get('summary', {})
            batch_positive = summary.get('positive', 0)
            batch_neutral = summary.get('neutral', 0)
            batch_negative = summary.get('negative', 0)
            
            # Validate the counts - the total should match the batch size
            total_sentiment = batch_positive + batch_neutral + batch_negative
            if total_sentiment != len(batch):
                logger.warning(f"Sentiment count mismatch: got {total_sentiment}, expected {len(batch)}")
                
                # Adjust totals if needed to match the actual batch size
                if total_sentiment > 0:
                    # Scaling factor to adjust counts proportionally
                    scale = len(batch) / total_sentiment
                    batch_positive = round(batch_positive * scale)
                    batch_negative = round(batch_negative * scale)
                    batch_neutral = len(batch) - batch_positive - batch_negative
                else:
                    # Default to equal distribution if all counts are zero
                    batch_neutral = len(batch)
                    
            # Update overall counts
            positive_count += batch_positive
            neutral_count += batch_neutral
            negative_count += batch_negative
            
            # Process individual post sentiments
            individuals = result_data.get('individual', [])
            
            # Create a mapping of post_id to sentiment
            sentiment_map = {}
            for ind in individuals:
                post_id_str = ind.get('post_id', '')
                sentiment = ind.get('sentiment', 'neutral')
                # Normalize sentiment values
                if sentiment.lower() in ('pos', 'positive'):
                    sentiment = 'positive'
                elif sentiment.lower() in ('neg', 'negative'):
                    sentiment = 'negative'
                else:
                    sentiment = 'neutral'
                    
                match = re.search(r'POST_ID_(\d+)', post_id_str)
                if match:
                    post_index = int(match.group(1))
                    sentiment_map[post_index] = sentiment
            
            # Apply sentiments to posts
            for i, post in enumerate(batch):
                post_index = batch_start + i
                if post_index not in processed_indices:  # Avoid duplicates
                    post_with_sentiment = post.copy()
                    post_with_sentiment['sentiment'] = sentiment_map.get(post_index, 'neutral')
                    post_sentiments.append(post_with_sentiment)
                    processed_indices.add(post_index)
        else:
            logger.error(f"Failed to extract sentiment data from batch {batch_start}")
            # Apply a default neutral sentiment for this batch as fallback
            for i, post in enumerate(batch):
                post_index = batch_start + i
                if post_index not in processed_indices:
                    post_with_sentiment = post.copy()
                    post_with_sentiment['sentiment'] = 'neutral'
                    post_sentiments.append(post_with_sentiment)
                    processed_indices.add(post_index)
            
            # Count all as neutral for this failed batch
            neutral_count += len(batch)
    
    # Verify that we have processed all posts
    if len(processed_indices) != len(posts):
        logger.warning(f"Not all posts were processed: {len(processed_indices)} out of {len(posts)}")
        # Handle any missed posts (should be rare)
        for i, post in enumerate(posts):
            if i not in processed_indices:
                post_with_sentiment = post.copy()
                post_with_sentiment['sentiment'] = 'neutral'  # Default to neutral
                post_sentiments.append(post_with_sentiment)
                neutral_count += 1
    
    # Calculate overall sentiment percentages
    total_posts = positive_count + neutral_count + negative_count
    if total_posts > 0:
        positive_pct = round((positive_count / total_posts) * 100)
        neutral_pct = round((neutral_count / total_posts) * 100)
        negative_pct = round((negative_count / total_posts) * 100)
        
        # Ensure percentages add up to 100% (adjust for rounding errors)
        total_pct = positive_pct + neutral_pct + negative_pct
        if total_pct != 100:
            # Adjust the largest percentage to make total 100%
            if positive_pct >= neutral_pct and positive_pct >= negative_pct:
                positive_pct += (100 - total_pct)
            elif neutral_pct >= positive_pct and neutral_pct >= negative_pct:
                neutral_pct += (100 - total_pct)
            else:
                negative_pct += (100 - total_pct)
    else:
        positive_pct = neutral_pct = negative_pct = 0
    
    # Log the actual counts for debugging
    logger.info(f"Sentiment counts - Positive: {positive_count}, Neutral: {neutral_count}, Negative: {negative_count}")
    logger.info(f"Sentiment percentages - Positive: {positive_pct}%, Neutral: {neutral_pct}%, Negative: {negative_pct}%")
    
    overall_sentiment = {
        "positive": positive_pct,
        "neutral": neutral_pct,
        "negative": negative_pct
    }
    
    # Ensure all posts have valid timestamps
    process_timestamps(post_sentiments)
    
    return overall_sentiment, post_sentiments

def process_timestamps(posts: List[Dict[str, Any]]) -> None:
    """
    Process and normalize timestamps for all posts.
    
    Args:
        posts: List of post dictionaries to process
    """
    current_time = datetime.datetime.now()
    timestamp_count = sum(1 for post in posts if 'timestamp' in post)
    
    # If most posts don't have timestamps, create artificial timestamps
    if timestamp_count < len(posts) * 0.7:  # Less than 70% have real timestamps
        logger.warning(f"Not enough posts with real timestamps ({timestamp_count}/{len(posts)}). Creating time distribution.")
        
        # Create a reasonable time range (7 days)
        time_range = datetime.timedelta(days=7)
        time_start = current_time - time_range
        
        # Sort posts by sentiment to avoid artificial patterns
        # (this prevents all positive posts from appearing at the same time)
        sentiment_groups = {
            'positive': [],
            'neutral': [],
            'negative': []
        }
        
        # Group posts by sentiment
        for post in posts:
            sentiment = post.get('sentiment', 'neutral')
            sentiment_groups[sentiment].append(post)
        
        # Interleave posts from different sentiment groups
        sorted_posts = []
        max_group_size = max(len(group) for group in sentiment_groups.values())
        
        for i in range(max_group_size):
            for sentiment in ['positive', 'neutral', 'negative']:
                if i < len(sentiment_groups[sentiment]):
                    sorted_posts.append(sentiment_groups[sentiment][i])
        
        # Distribute posts evenly across time range
        for i, post in enumerate(sorted_posts):
            position = i / max(1, len(sorted_posts) - 1)
            artificial_time = time_start + (time_range * position)
            post['timestamp'] = artificial_time
            post['artificial_timestamp'] = True
    else:
        # We have enough real timestamps, just normalize them
        for post in posts:
            if 'timestamp' not in post:
                post['timestamp'] = current_time
            elif not isinstance(post['timestamp'], datetime.datetime):
                try:
                    if isinstance(post['timestamp'], str):
                        # Try common timestamp formats
                        for fmt in ['%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%d %H:%M:%S']:
                            try:
                                post['timestamp'] = datetime.datetime.strptime(post['timestamp'], fmt)
                                break
                            except ValueError:
                                continue
                        
                        # If still a string, try ISO format with timezone handling
                        if isinstance(post['timestamp'], str):
                            post['timestamp'] = datetime.datetime.fromisoformat(
                                post['timestamp'].replace('Z', '+00:00')
                            )
                    else:
                        post['timestamp'] = current_time
                except Exception as e:
                    logger.warning(f"Failed to parse timestamp: {str(e)}")
                    post['timestamp'] = current_time

def get_sentiment_over_time(posts_with_sentiment: List[Dict[str, Any]], time_interval: str = 'day') -> List[Dict[str, Any]]:
    """
    Group posts that already have sentiment analysis by time periods.
    
    Args:
        posts_with_sentiment: List of post dictionaries with 'text', 'timestamp', and 'sentiment' fields
        time_interval: Time grouping ('hour', 'day', 'week')
        
    Returns:
        List of time periods with sentiment analysis for each
    """
    if not posts_with_sentiment:
        logger.warning("No posts available for time-based analysis")
        return []
    
    logger.info(f"Grouping sentiment by time with interval: {time_interval}")
    
    # Sort posts by timestamp first to ensure chronological ordering
    sorted_posts = sorted(posts_with_sentiment, key=lambda p: p.get('timestamp', datetime.datetime.now()))
    
    # Group posts by time interval
    time_groups = defaultdict(list)
    
    for post in sorted_posts:
        if 'timestamp' not in post or 'sentiment' not in post:
            logger.warning(f"Post missing required fields: timestamp={('timestamp' in post)}, sentiment={('sentiment' in post)}")
            continue
            
        timestamp = post['timestamp']
        
        # Define period key based on selected interval
        try:
            if time_interval == 'hour':
                period_key = timestamp.strftime('%Y-%m-%d %H:00')
            elif time_interval == 'week':
                # ISO week format (YYYY-WW)
                period_key = f"{timestamp.isocalendar()[0]}-W{timestamp.isocalendar()[1]:02d}"
            else:  # Default to day
                period_key = timestamp.strftime('%Y-%m-%d')
                
            time_groups[period_key].append(post)
        except Exception as e:
            logger.error(f"Error formatting timestamp {timestamp}: {str(e)}")
            continue
    
    # Check if we have enough time groups for meaningful visualization
    if len(time_groups) < 2:
        logger.warning(f"Not enough time periods for analysis: found {len(time_groups)} periods, need at least 2")
        
        # Create more time periods if needed based on post distribution
        if len(posts_with_sentiment) >= 10:
            # Split posts into equal-sized groups for better visualization
            posts_per_group = max(5, len(posts_with_sentiment) // 4)  # Aim for at least 4 groups
            num_groups = max(3, len(posts_with_sentiment) // posts_per_group)
            
            # Create artificial time periods
            artificial_groups = {}
            
            # Use actual post dates to define period names when possible
            timespan = (sorted_posts[-1]['timestamp'] - sorted_posts[0]['timestamp']).days
            if timespan > 0:
                # Create equally spaced dates within the timespan
                start_date = sorted_posts[0]['timestamp']
                for i in range(num_groups):
                    # Calculate a date within the range
                    offset_days = (timespan * i) // (num_groups - 1) if num_groups > 1 else 0
                    period_date = start_date + datetime.timedelta(days=offset_days)
                    period_key = period_date.strftime('%Y-%m-%d')
                    
                    # Assign posts to this period
                    start_idx = (i * len(sorted_posts)) // num_groups
                    end_idx = ((i + 1) * len(sorted_posts)) // num_groups
                    artificial_groups[period_key] = sorted_posts[start_idx:end_idx]
            else:
                # If all posts are from the same day, use hour intervals
                for i in range(num_groups):
                    period_key = f"Period {i+1}"
                    start_idx = (i * len(sorted_posts)) // num_groups
                    end_idx = ((i + 1) * len(sorted_posts)) // num_groups
                    artificial_groups[period_key] = sorted_posts[start_idx:end_idx]
            
            # Use these artificial groups instead
            time_groups = artificial_groups
            logger.info(f"Created {len(time_groups)} artificial time periods for visualization")
    
    # Calculate sentiment percentages for each time period
    time_series_data = []
    
    for period, period_posts in sorted(time_groups.items()):
        if not period_posts:
            continue
            
        # Count sentiments in this period
        sentiment_counts = {'positive': 0, 'neutral': 0, 'negative': 0}
        for post in period_posts:
            sentiment = post.get('sentiment', 'neutral')
            if sentiment in sentiment_counts:
                sentiment_counts[sentiment] += 1
            else:
                # Handle nonstandard sentiment values
                sentiment_counts['neutral'] += 1
                
        total_count = len(period_posts)
        
        # Calculate actual percentages based on counts
        sentiment_pcts = {}
        for sentiment, count in sentiment_counts.items():
            sentiment_pcts[sentiment] = round((count / total_count) * 100) if total_count > 0 else 0
        
        # Ensure percentages add up to 100%
        total_pct = sum(sentiment_pcts.values())
        if total_pct != 100 and total_pct > 0:
            # Find the largest category to adjust
            largest = max(sentiment_pcts.items(), key=lambda x: x[1])[0]
            sentiment_pcts[largest] += (100 - total_pct)
        
        time_series_data.append({
            'period': period,
            'count': total_count,
            'sentiment': sentiment_pcts
        })
    
    logger.info(f"Generated {len(time_series_data)} time periods for sentiment visualization")
    return time_series_data

def analyze_sentiment(posts: List[Dict[str, Any]], batch_size: int = 50, time_interval: str = 'day') -> Dict[str, Any]:
    """
    Complete sentiment analysis function that returns both overall sentiment and sentiment over time.
    
    Args:
        posts: List of post dictionaries with 'text' and 'timestamp' fields
        batch_size: Number of posts to analyze in each batch
        time_interval: Time grouping ('hour', 'day', 'week')
        
    Returns:
        Dictionary with overall sentiment and sentiment over time
    """
    if not posts:
        logger.warning("No posts provided for sentiment analysis")
        return {
            "overall": {"positive": 0, "neutral": 0, "negative": 0},
            "overTime": []
        }
    
    # Validate input posts
    valid_posts = []
    for post in posts:
        if isinstance(post, dict) and 'text' in post and post['text']:
            valid_posts.append(post)
        else:
            logger.warning(f"Skipping invalid post: {post}")
    
    if not valid_posts:
        logger.warning("No valid posts found with text content")
        return {
            "overall": {"positive": 0, "neutral": 0, "negative": 0},
            "overTime": []
        }
    
    # Process posts to get overall sentiment and individual post sentiments
    overall_sentiment, posts_with_sentiment = analyze_sentiment_with_details(valid_posts, batch_size)
    
    # Group by time periods
    sentiment_over_time = get_sentiment_over_time(posts_with_sentiment, time_interval)
    
    # Validate consistency between overall sentiment and time-based sentiment
    if sentiment_over_time:
        # Calculate the weighted average from time periods
        total_posts = sum(period['count'] for period in sentiment_over_time)
        if total_posts > 0:
            weighted_sentiment = {
                'positive': 0,
                'neutral': 0,
                'negative': 0
            }
            
            for period in sentiment_over_time:
                weight = period['count'] / total_posts
                for sentiment_type in weighted_sentiment:
                    weighted_sentiment[sentiment_type] += period['sentiment'][sentiment_type] * weight
            
            # Round to integers
            for sentiment_type in weighted_sentiment:
                weighted_sentiment[sentiment_type] = round(weighted_sentiment[sentiment_type])
            
            # Ensure weighted sentiment percentages add up to 100%
            total_pct = sum(weighted_sentiment.values())
            if total_pct != 100:
                # Adjust the largest value to make total 100%
                largest = max(weighted_sentiment.items(), key=lambda x: x[1])[0]
                weighted_sentiment[largest] += (100 - total_pct)
            
            # Check if there's a significant discrepancy between overall and time-based sentiment
            significant_diff = False
            for sentiment_type in weighted_sentiment:
                if abs(weighted_sentiment[sentiment_type] - overall_sentiment[sentiment_type]) > 10:
                    significant_diff = True
                    break
            
            if significant_diff:
                logger.warning("Significant discrepancy detected between overall sentiment and time-based sentiment")
                logger.info(f"Overall: {overall_sentiment}")
                logger.info(f"Time-weighted: {weighted_sentiment}")
                
                # Use the time-weighted sentiment as the source of truth
                overall_sentiment = weighted_sentiment
    
    return {
        "overall": overall_sentiment,
        "overTime": sentiment_over_time
    }
