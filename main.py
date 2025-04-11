import random
from fastapi import FastAPI, Query
from contextlib import asynccontextmanager
from scraping_techniques.get_user_info import InstagramProfileScraper

# scraper = None
scraper2 = None
scraper3 = None
scraper4 = None
scraper5 = None
scraper6 = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # global scraper
    global scraper2
    global scraper3
    global scraper4
    global scraper5
    global scraper6
    
    # scraper = InstagramProfileScraper(cookies_file_path="dangergod401_cookies.json")
    scraper2 = InstagramProfileScraper(cookies_file_path="loopstar_cookies.json")
    scraper3 = InstagramProfileScraper(cookies_file_path="sfjherbff5_cookies.json")
    scraper4 = InstagramProfileScraper(cookies_file_path="t65530874_cookies.json")
    scraper5 = InstagramProfileScraper(cookies_file_path="theamen_cookies.json")
    scraper6 = InstagramProfileScraper(cookies_file_path="thedanger396_cookies.json")

    print("Scraper initialized and browser opened")
    try:
        yield
    finally:
        for s in [scraper2, scraper3, scraper4, scraper5, scraper6]:
            if s:
                try:
                    s.quit()
                except Exception as e:
                    print(f"Error closing scraper: {e}")
        print("All browsers closed")

app = FastAPI(title="Instagram Profile Scraper API", lifespan=lifespan)

@app.get("/")
def read_root():
    return {"message": "Instagram Profile Scraper API is running. Use /get_user_info/?username=example to scrape data."}

@app.get("/get_user_info")
def user_info(username: str = Query(..., description="The username of the user")):
    global scraper, scraper2, scraper3, scraper4, scraper5, scraper6
    all_scrapers = [scraper, scraper2, scraper3, scraper4, scraper5, scraper6]
    if not hasattr(user_info, "last_used_scraper_index"):
        user_info.last_used_scraper_index = None
    available_indices = list(range(len(all_scrapers)))
    if user_info.last_used_scraper_index is not None:
        available_indices.remove(user_info.last_used_scraper_index)
    chosen_index = random.choice(available_indices)
    current_scraper = all_scrapers[chosen_index]
    user_info.last_used_scraper_index = chosen_index
    print(f"Using scraper {chosen_index + 1} for request: {username}")
    if not hasattr(current_scraper, 'current_tab'):
        current_scraper.current_tab = None
    if current_scraper.current_tab is not None:
        current_scraper.close_tab(current_scraper.current_tab)
    new_tab_index, user_data = current_scraper.capture_network_data(username)
    user_data_dict = {
        "pk": None,
        "username": None,
        "full_name": None,
        "is_verified": None,
        "profile_pic_url": None,
        "hd_profile_pic_url": None,
        "biography": None,
        "bio_links": None,
        "external_url": None,
        "follower_count": None,
        "following_count": None,
        "media_count": None,
        "category": None,
        "is_private": None,
        "is_business": None,
        "account_type": None,
        "friendship_status": None,
        "latest_reel_media": None,
        "text_post_app_badge_label": None,
        "show_text_post_app_badge": None,
        "external_lynx_url": None,
        "biography_with_entities": None,
        "is_memorialized": None,
        "has_profile_pic": None,
        "is_unpublished": None,
        "total_clips_count": None,
        "text_post_new_post_count": None,
        "latest_besties_reel_media": None,
        "live_broadcast_id": None,
        "pronouns": None,
        "fbid_v2": None
    }
    for i in user_data:
        response = user_data[i].get("response_body", False)
        if response:
            data = response.get("data", False)
            if data:
                if "user" in data:
                    user_result = data.get("user", False)
                    if user_result:
                        user_data_dict["pk"] = user_result.get("pk")
                        user_data_dict["username"] = user_result.get("username")
                        user_data_dict["full_name"] = user_result.get("full_name")
                        user_data_dict["is_verified"] = user_result.get("is_verified")
                        user_data_dict["profile_pic_url"] = user_result.get("profile_pic_url")
                        user_data_dict["hd_profile_pic_url"] = user_result.get("hd_profile_pic_url_info", {}).get("url")
                        user_data_dict["biography"] = user_result.get("biography")
                        user_data_dict["bio_links"] = user_result.get("bio_links", [])
                        user_data_dict["external_url"] = user_result.get("external_url")
                        user_data_dict["follower_count"] = user_result.get("follower_count")
                        user_data_dict["following_count"] = user_result.get("following_count")
                        user_data_dict["media_count"] = user_result.get("media_count")
                        user_data_dict["category"] = user_result.get("category")
                        user_data_dict["is_private"] = user_result.get("is_private")
                        user_data_dict["is_business"] = user_result.get("is_business")
                        user_data_dict["account_type"] = user_result.get("account_type")
                        user_data_dict["friendship_status"] = user_result.get("friendship_status", {})
                        user_data_dict["latest_reel_media"] = user_result.get("latest_reel_media")
                        user_data_dict["text_post_app_badge_label"] = user_result.get("text_post_app_badge_label")
                        user_data_dict["show_text_post_app_badge"] = user_result.get("show_text_post_app_badge")
                        user_data_dict["external_lynx_url"] = user_result.get("external_lynx_url")
                        user_data_dict["biography_with_entities"] = user_result.get("biography_with_entities")
                        user_data_dict["is_memorialized"] = user_result.get("is_memorialized")
                        user_data_dict["has_profile_pic"] = user_result.get("has_profile_pic")
                        user_data_dict["is_unpublished"] = user_result.get("is_unpublished")
                        user_data_dict["total_clips_count"] = user_result.get("total_clips_count")
                        user_data_dict["text_post_new_post_count"] = user_result.get("text_post_new_post_count")
                        user_data_dict["latest_besties_reel_media"] = user_result.get("latest_besties_reel_media")
                        user_data_dict["live_broadcast_id"] = user_result.get("live_broadcast_id")
                        user_data_dict["pronouns"] = user_result.get("pronouns")
                        user_data_dict["fbid_v2"] = user_result.get("fbid_v2")
    current_scraper.current_tab = new_tab_index    
    return {
        "username": username,
        "data": user_data_dict,
        "status": "success",
        "scraper_used": chosen_index + 1
    }