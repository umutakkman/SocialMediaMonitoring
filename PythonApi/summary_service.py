import re
import logging
from typing import List, Dict, Any, Tuple
from sklearn.feature_extraction.text import CountVectorizer
from iointel import Agent, Workflow
from config import OPENAI_API_KEY, LLM_API_BASE_URL, LLM_MODEL

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_summary_and_keywords(posts: List[Dict[str, Any]], keyword: str) -> Tuple[str, List[str]]:
    """
    Generate a detailed summary and extract keywords from posts using a single workflow.
    
    Args:
        posts: List of post dictionaries with 'text' field
        keyword: The original search keyword or hashtag
    
    Returns:
        Tuple containing (summary text, list of related keywords)
    """
    # Combine all texts
    combined = "\n\n---\n\n".join([p['text'] for p in posts])
    
    # Create summary agent with enhanced instructions
    summary_agent = Agent(
        name="ContentSummarizer",
        instructions=(
            "You are an expert at summarizing social media content with specific details "
            "and extracting key topics. You analyze posts to identify key insights, recurring themes, "
            "notable opinions, and specific examples. Your summaries are always detailed, informative, "
            "and include concrete details rather than vague generalizations. You also identify the "
            "most relevant keywords related to the topics discussed."
        ),
        model=LLM_MODEL,
        api_key=OPENAI_API_KEY,
        base_url=LLM_API_BASE_URL
    )
    
    # Create and run a single workflow with enhanced instructions
    workflow = Workflow(text=combined, client_mode=False)
    summary_result = workflow.custom(
        name="ComprehensiveSummary",
        objective=f"create a detailed, informative summary about '{keyword}' and extract related keywords",
        instructions=(
            f"Create a highly detailed and specific summary of Mastodon posts about '{keyword}' "
            f"AND extract exactly 4 related keywords.\n\n"
            "YOUR SUMMARY MUST:\n"
            "1. Include at least 5 specific details and examples from the posts\n"
            "2. Mention specific use cases, products, or technologies if relevant\n"
            "3. Highlight contrasting viewpoints if they exist\n"
            "4. Include at least 5 specific insights rather than vague generalizations\n"
            "5. Be 3-5 paragraphs long with concrete information\n"
            "6. Be highly informative and specific (at least 250 words)\n"
            "7. Avoid generic statements that could apply to any topic\n\n"
            "THE 4 KEYWORDS MUST:\n"
            "1. Be substantive words that capture key themes or concepts\n"
            "2. NOT include common words, URLs, or parts of URLs\n"
            "3. Be derived from significant topics mentioned in the posts\n"
            "4. NOT include the original search term itself\n\n"
            "FORMAT YOUR RESPONSE EXACTLY AS FOLLOWS:\n"
            "SUMMARY: [Your detailed summary here]\n\n"
            "KEYWORDS: [keyword1, keyword2, keyword3, keyword4]"
        ),
        agents=[summary_agent],
    ).run_tasks()

    # Extract result from AI response
    result_text = summary_result.get('results', {}).get('ComprehensiveSummary', '')
    
    # Parse summary and keywords from the result
    summary_text = ""
    related_keywords = []
    
    # Extract summary and keywords using regex
    summary_match = re.search(r'SUMMARY:\s*([\s\S]*?)(?=\s*KEYWORDS:|$)', result_text)
    keywords_match = re.search(r'KEYWORDS:\s*([\s\S]*?)$', result_text)
    
    if summary_match:
        summary_text = summary_match.group(1).strip()
        # Log the summary text for debugging
        logger.info(f"Extracted summary (first 100 chars): {summary_text[:100]}...")
        logger.info(f"Summary length: {len(summary_text)} characters")
    
    if keywords_match:
        keywords_text = keywords_match.group(1).strip()
        # Clean up the keywords text (remove brackets, extra characters)
        keywords_text = re.sub(r'[\[\]\']', '', keywords_text)
        related_keywords = [k.strip() for k in keywords_text.split(',') if k.strip()]
        logger.info(f"Extracted keywords: {related_keywords}")
    
    # Ensure we have 4 keywords if possible
    if len(related_keywords) < 4 and len(posts) > 0:
        related_keywords = extract_fallback_keywords(posts, keyword, related_keywords)
        
    return summary_text, related_keywords

def extract_fallback_keywords(posts: List[Dict[str, Any]], keyword: str, existing_keywords: List[str]) -> List[str]:
    """
    Extract additional keywords using statistical methods when LLM extraction fails.
    
    Args:
        posts: List of post dictionaries with 'text' field
        keyword: The original search keyword to exclude
        existing_keywords: Any keywords already identified
        
    Returns:
        Updated list of keywords (up to 4 total)
    """
    related_keywords = existing_keywords.copy()
    
    try:
        # Function to clean text
        def clean_text(text):
            # Remove URLs
            text = re.sub(r'https?://\S+|www\.\S+', '', text)
            # Remove special characters and numbers
            text = re.sub(r'[^\w\s]', '', text)
            text = re.sub(r'\d+', '', text)
            return text
        
        # Clean and combine all post texts
        cleaned_texts = [clean_text(post["text"].lower()) for post in posts]
        combined_text = " ".join(cleaned_texts)
        
        # Use CountVectorizer with custom stop words
        custom_stop_words = ['https', 'http', 'www', 'com', 'org', 'net', 'the', 'and', 'to', 'in', 'of', 'a', 'is', 'that', 'for', 'on', 'it', 'with', 'as', 'by', 'this', 'be', 'are', 'an', 'at']
        vectorizer = CountVectorizer(stop_words=custom_stop_words, ngram_range=(1, 1), max_features=50)
        X = vectorizer.fit_transform([combined_text])
        
        # Get most common words
        word_freq = [(word, X[0, idx]) for word, idx in vectorizer.vocabulary_.items()]
        word_freq.sort(key=lambda x: x[1], reverse=True)
        
        # Filter words: no short words, no words containing the keyword
        filtered_words = [word for word, freq in word_freq 
                          if len(word) > 3 
                          and keyword.lower() not in word.lower() 
                          and word.lower() != keyword.lower()]
        
        # Add filtered words to our keywords list
        for word in filtered_words:
            if len(related_keywords) < 4:
                if word not in related_keywords:
                    related_keywords.append(word)
            else:
                break
                
    except Exception as e:
        logger.error(f"Error extracting fallback keywords: {str(e)}")
        # If this fails, just continue with what we have
        
    return related_keywords
