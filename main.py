import requests
from bs4 import BeautifulSoup
import csv
import logging
import time

# Configure logging to show info-level messages
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_search_terms(filename="input.txt"):
    """Reads search terms from a file, one per line."""
    try:
        with open(filename, 'r') as f:
            # Return a list of non-empty lines with whitespace stripped
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        logging.error(f"The input file was not found: {filename}")
        return []

def construct_url(search_term):
    """Constructs a valid eBay search URL for a given search term."""
    # The base URL for eBay searches
    base_url = "https://www.ebay.com/sch/i.html"
    # URL-encode the search term to handle spaces and special characters
    formatted_term = requests.utils.quote(search_term)
    return f"{base_url}?_nkw={formatted_term}"

def fetch_page(url):
    """Fetches the HTML content of a URL, with retries on failure."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    # Retry logic to handle transient network issues
    for attempt in range(3):
        try:
            # Increased timeout for better resilience
            response = requests.get(url, headers=headers, timeout=20)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            logging.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
            if attempt < 2:
                logging.info("Waiting 5 seconds before retrying...")
                time.sleep(5)
    logging.error(f"Failed to fetch {url} after 3 attempts.")
    return None

def parse_products(html_content):
    """Parses product information from the HTML of a search results page."""
    if not html_content:
        return []

    soup = BeautifulSoup(html_content, 'html.parser')
    products = []

    # Find all product listings. This selector is based on common eBay page structures.
    items = soup.find_all('li', class_='s-item')

    # If the primary selector fails, try a fallback. This adds robustness.
    if not items:
        items = soup.select('div.s-item__wrapper')

    for item in items:
        try:
            title_element = item.find('h3', class_='s-item__title')
            price_element = item.find('span', class_='s-item__price')
            url_element = item.find('a', class_='s-item__link')

            # Extract text and hrefs, with fallback to 'N/A'
            title = title_element.text.strip() if title_element else 'N/A'
            price = price_element.text.strip() if price_element else 'N/A'
            url = url_element['href'] if url_element else 'N/A'

            # Ensure that the item is a valid product listing before adding it
            if title != 'N/A' and price != 'N/A' and url != 'N/A':
                 products.append({'title': title, 'price': price, 'url': url})
        except Exception as e:
            logging.warning(f"Could not parse an item on the page: {e}")
            continue

    return products

def save_to_csv(products, filename="products.csv"):
    """Saves a list of product data to a CSV file."""
    if not products:
        logging.info("No products to save.")
        return

    # Use the keys from the first product dictionary as headers
    keys = products[0].keys()
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as output_file:
            dict_writer = csv.DictWriter(output_file, fieldnames=keys)
            dict_writer.writeheader()
            dict_writer.writerows(products)
        logging.info(f"Successfully saved {len(products)} products to {filename}")
    except IOError as e:
        logging.error(f"Failed to write to {filename}: {e}")

def main():
    """Main function to orchestrate the scraping process."""
    search_terms = get_search_terms()
    if not search_terms:
        logging.warning("No search terms found in input.txt. Exiting.")
        return

    all_products = []
    for term in search_terms:
        logging.info(f"Starting scraping for search term: '{term}'")
        url = construct_url(term)
        html = fetch_page(url)

        if html:
            products = parse_products(html)
            if products:
                logging.info(f"Found {len(products)} products for '{term}'.")
                all_products.extend(products)
            else:
                logging.warning(f"No products found for '{term}'. The website structure may have changed.")

    if all_products:
        save_to_csv(all_products)
    else:
        logging.info("Scraping finished, but no products were found across all search terms.")

if __name__ == "__main__":
    main()
