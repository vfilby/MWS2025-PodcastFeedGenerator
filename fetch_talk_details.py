import requests
from bs4 import BeautifulSoup
import json
from typing import List, Dict, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import getpass

class WebScraper:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        # Initialize Selenium
        self.driver = webdriver.Chrome()  # You'll need to have ChromeDriver installed
        print(f"Initialized scraper with base URL: {base_url}")

    def login(self, username: str, password: str) -> bool:
        """
        Log in to the website
        """
        try:
            # Go to login page
            self.driver.get("https://migraineworldsummit.com/login/")
            
            # Wait for login form to be present
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "log"))
            )
            
            # Fill in login form
            self.driver.find_element(By.ID, "log").send_keys(username)  # Email field
            self.driver.find_element(By.ID, "pwd").send_keys(password)  # Password field
            
            # Click remember me checkbox (it's checked by default)
            # self.driver.find_element(By.ID, "rememberme").click()  # Uncomment if you want to uncheck
            
            # Click login button
            self.driver.find_element(By.ID, "mm-login-button").click()
            
            # Wait for login to complete and redirect
            WebDriverWait(self.driver, 10).until(
                EC.url_changes("https://migraineworldsummit.com/login/")
            )
            
            # Check if we're still on the login page (indicating login failure)
            if "login" in self.driver.current_url:
                print("Login failed - still on login page")
                return False
                
            print("Login successful")
            return True
            
        except Exception as e:
            print(f"Login failed: {e}")
            return False

    def fetch_page(self, url: str) -> Optional[str]:
        """
        Fetch the content of a webpage using Selenium to handle dynamic content
        """
        try:
            self.driver.get(url)
            
            # Extract favicon/icon
            icon_element = self.driver.find_element(By.CSS_SELECTOR, "link[rel='icon'][sizes='192x192']")
            if icon_element:
                self.logo_url = icon_element.get_attribute('href')
                if not self.logo_url.startswith('http'):
                    # Convert relative URL to absolute
                    self.logo_url = f"https://migraineworldsummit.com{self.logo_url}"
                print(f"Found icon: {self.logo_url}")
            
            # Wait for the download buttons to be present
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "download-button-dropdown"))
            )
            return self.driver.page_source
        except TimeoutException:
            print(f"Timeout waiting for dynamic content on {url}")
            return None
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None

    def close(self):
        """Close the Selenium driver"""
        self.driver.quit()

    def parse_talks(self, html_content: str) -> List[Dict[str, str]]:
        """
        Parse talk items from the HTML content
        Each talk is in a tr with class row-talk
        The title is in a link inside h4 with class title-talk
        The third td contains:
        - h6: presenter name
        - p: presenter role
        - span: institution
        Key questions are in data-bs-content of button with class key-questions-toggle
        Media links are in div with class download-button-dropdown
        Presenter image is in td with class column-profile
        """
        if not html_content:
            return []

        soup = BeautifulSoup(html_content, 'html.parser')
        talks = []

        # Find all talk rows
        talk_rows = soup.select('tr.row-talk')
        print(f"Found {len(talk_rows)} talk rows")  # Debug print

        for row in talk_rows:
            # Extract title from the link inside h4.title-talk
            title_h4 = row.select_one('h4.title-talk')
            if title_h4:
                title_link = title_h4.select_one('a')
                if title_link:
                    title = title_link.get_text(strip=True)
                    
                    # Get the third td (index 2)
                    presenter_td = row.select('td')[2] if len(row.select('td')) > 2 else None
                    
                    # Get the image from column-profile td
                    image_td = row.select_one('td.column-profile')
                    image_url = ''
                    if image_td:
                        img = image_td.select_one('img')
                        if img:
                            # First try to get the largest image from srcset
                            if 'srcset' in img.attrs:
                                # Split srcset into individual sources
                                sources = img['srcset'].split(',')
                                # Find the source with the largest width
                                largest_source = max(sources, key=lambda x: int(x.strip().split(' ')[1].replace('w', '')))
                                image_url = largest_source.strip().split(' ')[0]
                            # Fallback to src if no srcset
                            elif 'src' in img.attrs:
                                image_url = img['src']
                            
                            if image_url:
                                print(f"Found image for {title}: {image_url}")  # Debug print
                    
                    if presenter_td:
                        # Extract presenter details
                        presenter_name = presenter_td.select_one('h6').get_text(strip=True) if presenter_td.select_one('h6') else ''
                        presenter_role = presenter_td.select_one('p').get_text(strip=True) if presenter_td.select_one('p') else ''
                        institution = presenter_td.select_one('span').get_text(strip=True) if presenter_td.select_one('span') else ''
                        
                        # Extract key questions
                        key_questions_button = row.select_one('button.key-questions-toggle')
                        key_questions = []
                        if key_questions_button and 'data-bs-content' in key_questions_button.attrs:
                            questions_html = key_questions_button['data-bs-content']
                            questions_soup = BeautifulSoup(questions_html, 'html.parser')
                            key_questions = [li.get_text(strip=True) for li in questions_soup.select('li')]
                        
                        # Extract media links
                        media_links = {
                            'transcript': '',
                            'audio_30min': '',
                            'audio_full': '',
                            'video_30min': '',
                            'video_full': ''
                        }
                        
                        download_div = row.select_one('td.column-action div.download-button-dropdown-container div.download-button-dropdown')
                        if download_div:
                            for link in download_div.select('a'):
                                href = link.get('href', '')
                                text = link.get_text(strip=True)
                                if 'Transcript' in text:
                                    media_links['transcript'] = href
                                elif 'Audio: 30-minute' in text:
                                    media_links['audio_30min'] = href
                                elif 'Audio: Full Length' in text:
                                    media_links['audio_full'] = href
                                elif 'Video: 30-minute' in text:
                                    media_links['video_30min'] = href
                                elif 'Video: Full Length' in text:
                                    media_links['video_full'] = href
                        
                        print(f"Found talk: {title} by {presenter_name}")  # Debug print
                        
                        talks.append({
                            'title': title,
                            'presenter_name': presenter_name,
                            'presenter_role': presenter_role,
                            'institution': institution,
                            'presenter_image': image_url,
                            'key_questions': key_questions,
                            'media_links': media_links
                        })

        return talks

    def save_results(self, data: List[Dict[str, str]], filename: str):
        """
        Save the scraped data to a JSON file
        """
        output = {
            'logo_url': self.logo_url,
            'talks': data
        }
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

def main():
    # Get login credentials
    username = input("Enter your username: ")
    password = getpass.getpass("Enter your password: ")
    
    # Example usage
    scraper = WebScraper("https://migraineworldsummit.com/summit/2025-summit/")
    
    try:
        # Login first
        if not scraper.login(username, password):
            print("Failed to login. Exiting...")
            return
            
        # Fetch and parse the page
        html_content = scraper.fetch_page(scraper.base_url)
        if html_content:
            talks = scraper.parse_talks(html_content)
            scraper.save_results(talks, "talks.json")
            print(f"Saved {len(talks)} talks to talks.json")
    finally:
        # Always close the Selenium driver
        scraper.close()

if __name__ == "__main__":
    main()
