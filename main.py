import logging
import random
from fastapi import FastAPI, Query,Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from contextlib import asynccontextmanager


from scraping_techniques.get_user_info import InstagramProfileScraper
from scraping_techniques.get_user_post_info import InstagramPostScraper

from process_data.process_user_info import user_info_details
from process_data.process_user_post_info import user_post_details

import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("instagram_scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("instagram_scraper")

scraper = None
scraper2 = None
scraper3 = None
scraper4 = None
scraper5 = None
scraper6 = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global scraper
    global scraper2
    global scraper3
    global scraper4
    global scraper5
    global scraper6
    
    logger.info("Starting application and initializing scrapers")
    
    try:
        logger.info("Initializing scraper with dangergod401_cookies.json")
        scraper = InstagramProfileScraper(cookies_file_path="dangergod401_cookies.json")
        
        logger.info("Initializing scraper2 with loopstar_cookies.json")
        scraper2 = InstagramProfileScraper(cookies_file_path="loopstar_cookies.json")
        logger.info("Scraper2 initialized successfully")
        
        logger.info("Initializing scraper3 with sfjherbff5_cookies.json")
        scraper3 = InstagramProfileScraper(cookies_file_path="sfjherbff5_cookies.json")
        logger.info("Scraper3 initialized successfully")
        
        logger.info("Initializing scraper4 with t65530874_cookies.json")
        scraper4 = InstagramProfileScraper(cookies_file_path="t65530874_cookies.json")
        
        logger.info("Initializing scraper5 with theamen_cookies.json")
        scraper5 = InstagramProfileScraper(cookies_file_path="theamen_cookies.json")
        
        logger.info("Initializing scraper6 with thedanger396_cookies.json")
        scraper6 = InstagramProfileScraper(cookies_file_path="thedanger396_cookies.json")

        logger.info("All scrapers initialized and browsers opened")
        yield
    except Exception as e:
        logger.error(f"Error during scraper initialization: {e}")
        raise

app = FastAPI(title="Instagram Profile Scraper API", lifespan=lifespan)
limiter = Limiter(key_func=get_remote_address)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, lambda request, exc: JSONResponse(
    status_code=429, content={"message": "Too many requests, slow down!"})
)
app.add_middleware(SlowAPIMiddleware)

@app.get("/")
def read_root():
    logger.info("Root endpoint accessed")
    return {"message": "Instagram Profile Scraper API is running. Use /get_user_info/?username=example to scrape data."}

@app.get("/get_user_info")
def user_info(request:Request,username: str = Query(..., description="The username of the user")):
    logger.info(f"Received request to get info for username: {username}")

    global scraper3,scraper2,scraper,scraper4,scraper5,scraper6
    all_scrapers = [scraper3,scraper2,scraper,scraper4,scraper5,scraper6]
    
    if not hasattr(user_info, "last_used_scraper_index"):
        logger.debug("Initializing last_used_scraper_index")
        user_info.last_used_scraper_index = None
    
    available_indices = list(range(len(all_scrapers)))
    if user_info.last_used_scraper_index is not None and len(all_scrapers) > 1:
        available_indices.remove(user_info.last_used_scraper_index)
    
    chosen_index = random.choice(available_indices)
    current_scraper = all_scrapers[chosen_index]
    user_info.last_used_scraper_index = chosen_index
    logger.info(f"Using scraper {chosen_index + 1} for request: {username}")
    
    if not hasattr(current_scraper, 'current_tab'):
        logger.debug("Initializing current_tab attribute for scraper")
        current_scraper.current_tab = None
    
    if current_scraper.current_tab is not None:
        logger.debug(f"Closing existing tab with index {current_scraper.current_tab}")
        current_scraper.close_tab(current_scraper.current_tab)
    
    logger.info(f"Capturing network data for {username}")
    try:
        new_tab_index, user_data = current_scraper.capture_network_data(username)
        logger.info(f"Successfully captured network data in tab {new_tab_index}")
    except Exception as e:
        logger.error(f"Error capturing network data: {e}")
        return {
            "username": username,
            "data": None,
            "status": "error",
            "message": f"Failed to capture data: {str(e)}"
        }
    
    user_basic_details = user_info_details(username=username, user_data=user_data)
    logger.debug(f"Setting current tab to {new_tab_index}")
    current_scraper.current_tab = new_tab_index    
    logger.debug(f"The user details {user_basic_details}")
    
    logger.info(f"Successfully processed data for {username}")
    return {
        "username": username,
        "data": user_basic_details,
        "status": "success",
        "scraper_used": chosen_index + 1
    }

@app.get("/get_user_post_info")
def user_post_info(username: str = Query(..., description="The username of the user")):
    logger.info(f"Received request to get info for username: {username}")
    
    global scraper2
    all_scrapers = [scraper2]

    if not hasattr(user_post_info, "last_used_scraper_index"):
        logger.debug("Initializing last_used_scraper_index")
        user_post_info.last_used_scraper_index = None
    
    available_indices = list(range(len(all_scrapers)))
    if user_post_info.last_used_scraper_index is not None and len(all_scrapers) > 1:
        available_indices.remove(user_post_info.last_used_scraper_index)
    
    chosen_index = random.choice(available_indices)
    current_scraper = all_scrapers[chosen_index]
    user_post_info.last_used_scraper_index = chosen_index
    logger.info(f"Using scraper {chosen_index + 1} for request: {username}")
    
    if not hasattr(current_scraper, 'current_tab'):
        logger.debug("Initializing current_tab attribute for scraper")
        current_scraper.current_tab = None
    
    if current_scraper.current_tab is not None:
        logger.debug(f"Closing existing tab with index {current_scraper.current_tab}")
        current_scraper.close_tab(current_scraper.current_tab)
    
    logger.info(f"Capturing network data for {username}")
    try:
        new_tab_index, user_data = current_scraper.capture_network_data(username)
        logger.info(f"Successfully captured network data in tab {new_tab_index}")
    except Exception as e:
        logger.error(f"Error capturing network data: {e}")
        return {
            "username": username,
            "data": None,
            "status": "error",
            "message": f"Failed to capture data: {str(e)}"
        }
    
    # Even if there was an exception during data capture, we might have partial data
    if not user_data:
        logger.error("No data captured before timeout")
        return {
            "username": username,
            "data": None,
            "status": "error",
            "message": "No data was captured before connection timeout"
        }
    
    # Process whatever data we managed to collect
    user_posts_list = user_post_details(user_data=user_data)
    current_scraper.current_tab = new_tab_index
    
    # Return the posts we collected, even if incomplete due to timeout
    return {
        "username": username,
        "data": user_posts_list,
        "status": "partial" if len(user_data) < 5 else "success",  # Consider it partial if few responses
        "message": f"Collected {len(user_data)} GraphQL responses" 
    }