import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("instagram_scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("instagram_scraper")
logger.info("Initilaising the process user post info")

def user_post_details(user_data):
    user_posts_list = []
    for i in user_data:
        response = user_data[i].get("response_body", False)
        if response:
            data = response.get("data", False)
            if data:
                try:
                    if "xdt_api__v1__feed__user_timeline_graphql_connection" in data:
                        timeline_posts = data.get("xdt_api__v1__feed__user_timeline_graphql_connection",False)
                        if timeline_posts:
                            edges = timeline_posts.get("edges",False)
                            if edges:
                                for edge in edges:
                                    node = edge.get("node",False)
                                    if node:
                                        is_caption = False
                                        caption = node.get("caption","")
                                        if caption:
                                            is_caption = True
                                            caption_text = caption.get("text","")
                                            
                                        user_post_dict = {
                                            "post_code": node.get("code", ''),
                                            "comment_count": node.get("comment_count", 0),
                                            "like_count": node.get("like_count", 0),
                                            "media_type": node.get("media_type", 0),
                                            "taken_at": node.get("taken_at", 0),
                                            "caption": caption_text if is_caption else "",
                                            "is_paid_partnership": node.get("is_paid_partnership",False),
                                            "sponsor_tags":node.get("sponsor_tags",""),
                                            "coauthors":node.get("coauthor_producers",[]),
                                            "top_likers":node.get("top_likers",""),
                                            "product_type":node.get("product_type",''),
                                            "usertags":node.get("usertags",[]),
                                            "location":node.get("location","")
                                        }
                                    user_posts_list.append(user_post_dict)
                except Exception as e:
                    print(f"the eror you got is {e}")
                    user_post_dict = {
                        "post_code": '',
                        "comment_count": 0,
                        "like_count": 0,
                        "media_type": 0,
                        "taken_at": 0,
                        "caption":"",
                        "is_paid_partnership":0,
                        "sponsor_tags":"",
                        "coauthor_producers":[],
                        "top_likers":"",
                        "product_type":"",
                        "usertags":[],
                        "location":"",
                    }
                    user_posts_list.append(user_post_dict)
    return user_posts_list