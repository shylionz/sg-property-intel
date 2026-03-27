"""Simple test to understand URA data structure."""
import requests
from bs4 import BeautifulSoup
import time

# Try to get the main transaction page
url = "https://eservice.ura.gov.sg/property-market-information/pmiResidentialTransactionSearch"

# Create a session to maintain cookies
session = requests.Session()

# Set headers to mimic a real browser
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Cache-Control": "no-cache",
}

session.headers.update(headers)

try:
    print("Fetching main page...")
    response = session.get(url, timeout=30)
    response.raise_for_status()
    
    print(f"Status code: {response.status_code}")
    
    # Check if we got HTML content
    if 'html' in response.headers.get('content-type', ''):
        soup = BeautifulSoup(response.text, "lxml")
        
        # Look for project name dropdown or input fields
        print("Looking for project-related elements...")
        
        # Find all input fields with name attributes
        inputs = soup.find_all("input", {"name": True})
        print(f"Found {len(inputs)} input fields with names")
        
        # Look for project name related elements
        project_inputs = [inp for inp in inputs if 'project' in inp.get('name', '').lower()]
        print(f"Found {len(project_inputs)} project-related inputs")
        
        # Look for select dropdowns
        selects = soup.find_all("select")
        print(f"Found {len(selects)} select dropdowns")
        
        for i, select in enumerate(selects):
            select_name = select.get('name', '')
            print(f"Select {i}: name='{select_name}'")
            options = select.find_all("option")
            print(f"  Options: {len(options)}")
            if options:
                print(f"  First few options: {[opt.get_text(strip=True) for opt in options[:5]]}")
        
        # Look for any hidden CSRF fields
        csrf_inputs = soup.find_all("input", {"type": "hidden", "name": "_csrf"})
        if csrf_inputs:
            print(f"Found CSRF input: {csrf_inputs[0].get('value', 'No value')}")
        else:
            print("No CSRF input found")
            
    else:
        print("Received non-HTML content")
        print(f"Content type: {response.headers.get('content-type')}")
        print(f"Content length: {len(response.content)}")
        
except requests.RequestException as e:
    print(f"Error fetching page: {e}")
except Exception as e:
    print(f"Error processing page: {e}")