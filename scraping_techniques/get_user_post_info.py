from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import json
import time

class InstagramPostScraper:
    def __init__(self, cookies_file_path):
        self.chrome_options = Options()
        # self.chrome_options.add_argument("--headless")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        self.chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
        # service = Service(executable_path='/usr/bin/chromedriver')
        # self.driver = webdriver.Chrome(service=service, options=self.chrome_options)
        self.driver = webdriver.Chrome(options=self.chrome_options)
        self.cookies_file_path = cookies_file_path
        self.login_with_cookies()
        self.tabs = {}  
        self.current_tab = None
    
    def login_with_cookies(self):
        self.driver.get("https://www.instagram.com")
        try:
            if self.cookies_file_path.endswith('.json'):
                with open(self.cookies_file_path, 'r') as file:
                    cookies = json.load(file)
            for cookie in cookies:
                if 'expiry' in cookie:
                    cookie['expiry'] = int(cookie['expiry'])
                self.driver.add_cookie(cookie)
            self.driver.refresh()
            time.sleep(3)
            print("Login successful")
        except Exception as e:
            print(f"Error loading cookies: {str(e)}")
    
    def create_new_tab(self):
        self.driver.execute_script("window.open('about:blank', '_blank');")
        handles = self.driver.window_handles
        for handle in handles:
            if handle not in self.tabs.values():
                new_tab_index = max(self.tabs.keys()) + 1 if self.tabs else 0
                self.tabs[new_tab_index] = handle
                break
        self.driver.switch_to.window(self.tabs[new_tab_index])
        return new_tab_index
    
    def switch_to_tab(self, tab_index):
        if tab_index in self.tabs:
            self.driver.switch_to.window(self.tabs[tab_index])
            return True
        return False
    
    def close_tab(self, tab_index):
        if tab_index in self.tabs:
            self.driver.switch_to.window(self.tabs[tab_index])
            del self.tabs[tab_index]
            if self.tabs:
                first_tab = min(self.tabs.keys())
                self.driver.switch_to.window(self.tabs[first_tab])
            return True
        return False
    
    def capture_network_data(self, username, tab_index=None):
        if tab_index is None:
            tab_index = self.create_new_tab()
        else:
            self.switch_to_tab(tab_index)
        
        # Dictionary to store all GraphQL data
        all_graphql_data = {}
        
        # Enable network tracking and set event listeners
        self.driver.execute_cdp_cmd('Network.enable', {})
        self.driver.execute_cdp_cmd('Network.setCacheDisabled', {'cacheDisabled': True})
        
        # Clear logs before navigating
        self.driver.get_log('performance')
        
        # Navigate to the profile
        profile_url = f"https://www.instagram.com/{username}/"
        print(f"Tab {tab_index}: Navigating to {profile_url}")
        self.driver.get(profile_url)
        print(f"Tab {tab_index}: Waiting for initial page load...")
        time.sleep(5)
        
        # Process browser logs and capture responses
        def process_browser_logs():
            logs = self.driver.get_log('performance')
            for log in logs:
                log_entry = json.loads(log['message'])
                if 'message' not in log_entry or 'method' not in log_entry['message']:
                    continue
                    
                method = log_entry['message']['method']
                params = log_entry['message'].get('params', {})
                
                # Track request data for GraphQL requests
                if method == 'Network.requestWillBeSent':
                    request_id = params.get('requestId')
                    if request_id:
                        request = params.get('request', {})
                        url = request.get('url', '')
                        if 'graphql/query' in url:
                            # Immediately try to capture this request info
                            graphql_req_data = {
                                'url': url,
                                'method': request.get('method'),
                                'headers': request.get('headers'),
                                'post_data': request.get('postData'),
                                'timestamp': log_entry.get('timestamp'),
                                'request_id': request_id
                            }
                            # Store temporarily with request_id
                            all_graphql_data[request_id] = graphql_req_data
                            print(f"Tab {tab_index}: Found GraphQL request: {url}")
                
                # When a response is received
                elif method == 'Network.responseReceived':
                    request_id = params.get('requestId')
                    response = params.get('response', {})
                    url = response.get('url', '')
                    
                    # Check if it's a GraphQL request
                    if 'graphql/query' in url:
                        try:
                            # Get the response body immediately
                            body_data = self.driver.execute_cdp_cmd('Network.getResponseBody', {'requestId': request_id})
                            if 'body' in body_data and request_id in all_graphql_data:
                                # Update with response data
                                all_graphql_data[request_id].update({
                                    'status': response.get('status'),
                                    'mime_type': response.get('mimeType'),
                                    'response_headers': response.get('headers'),
                                    'response_body': self._parse_body(body_data['body'])
                                })
                                print(f"Tab {tab_index}: Captured GraphQL response for {url}")
                        except Exception as e:
                            print(f"Tab {tab_index}: Error capturing response for {url}: {str(e)}")
        
        # Start scrolling and processing logs
        print(f"Tab {tab_index}: Starting continuous scroll...")
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        scroll_attempts = 0
        max_attempts = 100  # Maximum number of scroll attempts
        
        # Keep scrolling until no new content loads or max attempts reached
        while scroll_attempts < max_attempts:
            # Process logs before each scroll
            process_browser_logs()
            
            # Scroll to the bottom
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            # Wait for potential new content to load
            time.sleep(2)
            
            # Calculate new scroll height and compare with last scroll height
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            
            if new_height == last_height:
                # If heights are the same, wait a bit longer and try one more time
                time.sleep(2)
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    print(f"Tab {tab_index}: No new content loaded after scrolling. Reached the bottom.")
                    # Process logs one final time before breaking
                    process_browser_logs()
                    break
            
            last_height = new_height
            scroll_attempts += 1
            print(f"Tab {tab_index}: Scroll attempt {scroll_attempts}/{max_attempts}, height: {new_height}")
        
        # Process logs one final time to catch any remaining responses
        process_browser_logs()
        
        # Convert temporary request_id keys to more stable unique identifiers
        final_data = {}
        for i, (req_id, data) in enumerate(all_graphql_data.items()):
            graphql_id = f"graphql_{int(time.time())}_{i}"
            final_data[graphql_id] = data
        
        print(f"Tab {tab_index}: Dynamic scrolling completed after {scroll_attempts} attempts")
        print(f"Tab {tab_index}: Captured {len(final_data)} GraphQL responses")
        
        return tab_index, final_data
    
    def _parse_body(self, body_text):
        """Parse response body text to JSON if possible"""
        try:
            return json.loads(body_text)
        except:
            return body_text
    
    def _process_network_logs(self, logs, tab_index):
        """Legacy method kept for compatibility"""
        request_data = {}
        completed_requests = []
        api_requests = []
        graphql_requests = [] 
        
        for log in logs:
            log_entry = json.loads(log['message'])
            if 'message' not in log_entry or 'method' not in log_entry['message']:
                continue
                
            method = log_entry['message']['method']
            params = log_entry['message'].get('params', {})
            if method == 'Network.requestWillBeSent':
                request_id = params.get('requestId')
                if request_id:
                    request = params.get('request', {})
                    url = request.get('url', '')
                    post_data = request.get('postData')
                    
                    request_data[request_id] = {
                        'url': url,
                        'method': request.get('method'),
                        'headers': request.get('headers'),
                        'post_data': post_data, 
                        'timestamp': log_entry.get('timestamp'),
                        'request_id': request_id
                    }
                    if 'graphql/query' in url:
                        graphql_requests.append(request_id)
                        print(f"Tab {tab_index}: Found GraphQL request: {url}")
            elif method == 'Network.responseReceived':
                request_id = params.get('requestId')
                if request_id in request_data:
                    response = params.get('response', {})
                    request_data[request_id].update({
                        'status': response.get('status'),
                        'mime_type': response.get('mimeType'),
                        'response_headers': response.get('headers'),
                        'response_received': True
                    })
                    url = request_data[request_id].get('url', '')
                    if 'api/v1/' in url or 'graphql/query' in url:
                        api_requests.append(request_id)
        
        all_graphql_data = {}
        print(f"Tab {tab_index}: Fetching response bodies for {len(api_requests)} API requests...")
        print(f"Tab {tab_index}: Including {len(graphql_requests)} GraphQL requests...")
        for request_id in api_requests:
            try:
                url = request_data[request_id].get('url', '')
                response_body = self.driver.execute_cdp_cmd('Network.getResponseBody', {'requestId': request_id})
                if 'body' in response_body:
                    request_data[request_id]['response_body'] = response_body['body']
                    completed_requests.append(request_id)
                    if request_id in graphql_requests:
                        timestamp = int(time.time())
                        graphql_id = f"graphql_{timestamp}_{len(all_graphql_data)}"
                        try:
                            body_content = json.loads(response_body['body'])
                        except:
                            body_content = response_body['body']
                        all_graphql_data[graphql_id] = {
                            'url': url,
                            'method': request_data[request_id].get('method'),
                            'post_data': request_data[request_id].get('post_data'),
                            'request_headers': request_data[request_id].get('headers', {}),
                            'response_headers': request_data[request_id].get('response_headers', {}),
                            'response_body': body_content,
                            'timestamp': request_data[request_id].get('timestamp')
                        }
            except Exception as e:
                print(f"Tab {tab_index}: Could not get response for request {request_id}: {e}")
                continue
        return all_graphql_data
    
    def save_data_to_file(self, data, filename):
        """Save captured data to a JSON file"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"Data successfully saved to {filename}")
            return True
        except Exception as e:
            print(f"Error saving data to file: {str(e)}")
            return False
    
    def extract_posts_from_graphql(self, graphql_data):
        """Extract post information from GraphQL responses"""
        posts = []
        for req_id, data in graphql_data.items():
            try:
                response_body = data.get('response_body', {})
                
                # Handle different GraphQL response structures
                if isinstance(response_body, dict):
                    # Try to extract from data.user.edge_owner_to_timeline_media.edges
                    if 'data' in response_body:
                        user_data = response_body.get('data', {}).get('user', {})
                        if user_data:
                            timeline = user_data.get('edge_owner_to_timeline_media', {})
                            edges = timeline.get('edges', [])
                            for edge in edges:
                                node = edge.get('node', {})
                                if node:
                                    post = {
                                        'id': node.get('id'),
                                        'shortcode': node.get('shortcode'),
                                        'display_url': node.get('display_url'),
                                        'caption': node.get('edge_media_to_caption', {}).get('edges', [{}])[0].get('node', {}).get('text', '') if node.get('edge_media_to_caption', {}).get('edges') else '',
                                        'timestamp': node.get('taken_at_timestamp'),
                                        'likes': node.get('edge_liked_by', {}).get('count', 0),
                                        'comments': node.get('edge_media_to_comment', {}).get('count', 0),
                                        'is_video': node.get('is_video', False)
                                    }
                                    posts.append(post)
            except Exception as e:
                print(f"Error extracting posts from GraphQL response {req_id}: {str(e)}")
                continue
        
        # Remove duplicates based on post ID
        unique_posts = []
        seen_ids = set()
        for post in posts:
            if post['id'] not in seen_ids:
                seen_ids.add(post['id'])
                unique_posts.append(post)
        
        return unique_posts

    def quit(self):
        self.driver.quit()
