from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import json
import time
import os
import shutil
import subprocess
import sys
import requests
import zipfile

class InstagramPostScraper:
    def __init__(self, cookies_file_path):
        self.chrome_options = Options()
        self.chrome_options.add_argument("--headless")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        self.chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
        self.chrome_options.add_argument("--disable-extensions")
        self.chrome_options.add_argument("--disable-gpu")
        self.chrome_options.add_argument("--disable-browser-side-navigation")
        self.chrome_options.add_argument("--disable-features=NetworkService")
        self.chrome_options.add_argument("--dns-prefetch-disable")
        self.chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.chrome_options.add_experimental_option("useAutomationExtension", False)
        
        service = Service(executable_path='/usr/bin/chromedriver')
        self.driver = webdriver.Chrome(service=service, options=self.chrome_options)

        chromedriver_path = self.find_chromedriver()
        if chromedriver_path:
            print(f"Using ChromeDriver from: {chromedriver_path}")
            service = Service(executable_path=chromedriver_path)
            self.driver = webdriver.Chrome(service=service, options=self.chrome_options)
        else:
            # Fall back to letting Selenium find ChromeDriver
            print("ChromeDriver path not specified, letting Selenium find it")
            self.driver = webdriver.Chrome(options=self.chrome_options)

        # self.driver = webdriver.Chrome(options=self.chrome_options)
        self.cookies_file_path = cookies_file_path
        self.login_with_cookies()
        self.tabs = {}  
        self.current_tab = None
    def install_chrome_if_needed(self):
        """Install Chrome and ChromeDriver if not already installed"""
        # Check if Chrome is already installed
        chrome_path = self.find_chrome()
        
        if not chrome_path:
            print("Chrome not found. Installing Google Chrome...")
            if sys.platform.startswith('linux'):
                self.install_chrome_linux()
            elif sys.platform == 'darwin':
                print("Please install Chrome manually on macOS")
            elif sys.platform == 'win32':
                print("Please install Chrome manually on Windows")
            
        # Check if ChromeDriver is already installed
        if not self.find_chromedriver():
            print("ChromeDriver not found. Installing ChromeDriver...")
            self.install_chromedriver()
    
    def find_chrome(self):
        """Find Chrome executable path"""
        possible_chrome_paths = {
            'linux': [
                '/usr/bin/google-chrome',
                '/usr/bin/google-chrome-stable',
                '/usr/local/bin/google-chrome',
                '/usr/local/bin/google-chrome-stable'
            ],
            'darwin': [
                '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
                os.path.expanduser('~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
            ],
            'win32': [
                r'C:\Program Files\Google\Chrome\Application\chrome.exe',
                r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
                os.path.expanduser(r'~\AppData\Local\Google\Chrome\Application\chrome.exe')
            ]
        }
        
        platform_key = 'linux' if sys.platform.startswith('linux') else sys.platform
        
        if platform_key in possible_chrome_paths:
            for path in possible_chrome_paths[platform_key]:
                if os.path.exists(path):
                    return path
        
        # Try using which command on Linux/Mac
        if platform_key in ['linux', 'darwin']:
            try:
                chrome_path = subprocess.check_output(['which', 'google-chrome']).decode('utf-8').strip()
                if chrome_path:
                    return chrome_path
            except:
                pass
        
        return None
    
    def install_chrome_linux(self):
        """Install Chrome on Linux"""
        try:
            # Add Google Chrome repository key
            subprocess.run([
                'wget', '-q', '-O', '-', 
                'https://dl.google.com/linux/linux_signing_key.pub', 
                '|', 'sudo', 'apt-key', 'add', '-'
            ], check=True, shell=True)
            
            # Add Google Chrome repository
            with open('/etc/apt/sources.list.d/google-chrome.list', 'w') as f:
                f.write("deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main")
            
            # Update package list
            subprocess.run(['sudo', 'apt-get', 'update'], check=True)
            
            # Install Google Chrome
            subprocess.run([
                'sudo', 'apt-get', 'install', '-y', 'google-chrome-stable'
            ], check=True)
            
            print("Google Chrome installed successfully")
        except subprocess.SubprocessError as e:
            print(f"Failed to install Google Chrome: {e}")
            print("Please install Chrome manually")
    
    def get_chrome_version(self):
        """Get Chrome version"""
        chrome_path = self.find_chrome()
        if not chrome_path:
            return None
            
        try:
            if sys.platform.startswith('linux') or sys.platform == 'darwin':
                output = subprocess.check_output([chrome_path, '--version']).decode('utf-8')
            else:  # Windows
                output = subprocess.check_output(f'"{chrome_path}" --version', shell=True).decode('utf-8')
                
            # Parse version number (typically in format "Google Chrome XX.X.XXXX.XX")
            version = output.strip().split(' ')[-1]
            major_version = version.split('.')[0]
            return major_version
        except:
            return None
    
    def install_chromedriver(self):
        """Install appropriate ChromeDriver for the installed Chrome version"""
        chrome_version = self.get_chrome_version()
        if not chrome_version:
            print("Could not determine Chrome version, skipping ChromeDriver installation")
            return
            
        try:
            # Create directory for ChromeDriver if it doesn't exist
            chromedriver_dir = '/usr/local/bin' if os.access('/usr/local/bin', os.W_OK) else os.path.expanduser('~/.local/bin')
            os.makedirs(chromedriver_dir, exist_ok=True)
            
            # Get appropriate ChromeDriver version
            version_url = f"https://chromedriver.storage.googleapis.com/LATEST_RELEASE_{chrome_version}"
            response = requests.get(version_url)
            driver_version = response.text.strip()
            
            # Determine platform
            if sys.platform.startswith('linux'):
                platform = 'linux64'
            elif sys.platform == 'darwin':
                platform = 'mac64'  # or 'mac_arm64' for Apple Silicon
            else:  # Windows
                platform = 'win32'
                
            # Download ChromeDriver
            download_url = f"https://chromedriver.storage.googleapis.com/{driver_version}/chromedriver_{platform}.zip"
            zip_path = os.path.join(chromedriver_dir, 'chromedriver.zip')
            response = requests.get(download_url)
            
            with open(zip_path, 'wb') as f:
                f.write(response.content)
                
            # Extract ChromeDriver
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(chromedriver_dir)
                
            # Make ChromeDriver executable on Linux/Mac
            if sys.platform.startswith('linux') or sys.platform == 'darwin':
                chromedriver_path = os.path.join(chromedriver_dir, 'chromedriver')
                subprocess.run(['chmod', '+x', chromedriver_path], check=True)
            
            # Cleanup zip file
            os.remove(zip_path)
            
            print(f"ChromeDriver {driver_version} installed successfully")
        except Exception as e:
            print(f"Failed to install ChromeDriver: {e}")
            print("Please install ChromeDriver manually")

    def find_chromedriver(self):
        # Common paths in Docker containers
        possible_paths = [
            '/usr/bin/chromedriver',
            '/usr/local/bin/chromedriver',
            '/opt/chromedriver',
            '/opt/selenium/chromedriver',
            '/app/chromedriver'
        ]
        
        # Check environment variable first
        if 'CHROMEDRIVER_PATH' in os.environ:
            return os.environ['CHROMEDRIVER_PATH']
            
        # Check common paths
        for path in possible_paths:
            if os.path.exists(path) and os.access(path, os.X_OK):
                return path
                
        # Use which command
        try:
            chromedriver_path = shutil.which('chromedriver')
            if chromedriver_path:
                return chromedriver_path
        except:
            pass
            
        return None
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
        
        try:
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
        except Exception as e:
            print(f"Tab {tab_index}: Scrolling interrupted: {str(e)}")
            # Still continue processing - return whatever data we have
        
        # Convert temporary request_id keys to more stable unique identifiers
        final_data = {}
        for i, (req_id, data) in enumerate(all_graphql_data.items()):
            graphql_id = f"graphql_{int(time.time())}_{i}"
            final_data[graphql_id] = data
        
        print(f"Tab {tab_index}: Dynamic scrolling completed after {scroll_attempts if 'scroll_attempts' in locals() else 0} attempts")
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
