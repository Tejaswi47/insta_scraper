from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import json
import time

class InstagramProfileScraper:
    def __init__(self, cookies_file_path):
        self.chrome_options = Options()
        self.chrome_options.add_argument("--headless")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        self.chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
        service = Service(executable_path='/usr/bin/chromedriver')
        self.driver = webdriver.Chrome(service=service, options=self.chrome_options)
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
        self.driver.execute_cdp_cmd('Network.enable', {})
        self.driver.get_log('performance')
        profile_url = f"https://www.instagram.com/{username}/"
        print(f"Tab {tab_index}: Navigating to {profile_url}")
        self.driver.get(profile_url)
        print(f"Tab {tab_index}: Waiting for initial page load...")
        time.sleep(5)
        print(f"Tab {tab_index}: Scrolling to trigger more requests...")
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
        time.sleep(3)
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        print(f"Tab {tab_index}: Capturing network logs...")
        logs = self.driver.get_log('performance')
        print(f"Tab {tab_index}: Captured {len(logs)} log entries")
        data = self._process_network_logs(logs, tab_index)
        return tab_index, data
    
    def _process_network_logs(self, logs, tab_index):
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
        return all_graphql_data

    def quit(self):
        self.driver.quit()