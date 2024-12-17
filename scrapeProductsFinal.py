import json
import re
import time
import logging
import sys
import traceback
from typing import List, Dict, Any, Optional

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import (
    WebDriverException,
    NoSuchElementException,
    TimeoutException,
    StaleElementReferenceException
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class ScraperError(Exception):
    """Custom exception for scraping-related errors."""
    pass

def setup_webdriver(headless: bool = True, max_retries: int = 3):
    """
    Set up and return a Selenium WebDriver instance with retry mechanism.

    Args:
        headless (bool): Whether to run the browser in headless mode. Defaults to False.
        max_retries (int): Maximum number of retry attempts for WebDriver setup.

    Returns:
        webdriver.Chrome: Configured Chrome WebDriver

    Raises:
        ScraperError: If WebDriver setup fails after max retries
    """
    for attempt in range(max_retries):
        try:
            options = Options()
            if headless:
                options.add_argument('--headless')


            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
            driver.set_page_load_timeout(30)  # Set a timeout for page loading
            return driver

        except WebDriverException as e:
            logging.error(f"WebDriver setup attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                raise ScraperError(f"Failed to setup WebDriver after {max_retries} attempts: {e}")
            time.sleep(2)  # Wait before retrying

def safe_find_element(driver: webdriver.Chrome, by: By, value: str, timeout: int = 10):
    """
    Safely find an element with error handling and logging.

    Args:
        driver (webdriver.Chrome): Selenium WebDriver instance
        by (By): Selenium By locator strategy
        value (str): Locator value
        timeout (int): Maximum time to wait for element

    Returns:
        Optional[Any]: Found element or None

    Raises:
        ScraperError: If element cannot be found
    """
    try:
        element = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, value))) # Wait for element to be present
        return element
    except NoSuchElementException: # To handle in case of missing elements
        logging.warning(f"Element not found: {by}={value}")
        return None
    except StaleElementReferenceException: # To handle in case of dynamic pages
        logging.warning(f"Stale element encountered: {by}={value}. Retrying...") 
        time.sleep(1)
        return safe_find_element(driver, by, value, timeout) 
    except Exception as e:
        logging.error(f"Unexpected error finding element {by}={value}: {e}")
        raise ScraperError(f"Failed to find element: {e}")

def safe_find_elements(driver: webdriver.Chrome, by: By, value: str) -> List[Any]:
    """
    Safely find multiple elements with error handling and logging.

    Args:
        driver (webdriver.Chrome): Selenium WebDriver instance
        by (By): Selenium By locator strategy
        value (str): Locator value

    Returns:
        List[Any]: List of found elements
    """
    try:
        elements = driver.find_elements(by, value)
        return elements
    except Exception as e:
        logging.error(f"Error finding elements {by}={value}: {e}")
        return []

def extract_overall_rating(rating_element: Optional[Any]):
    """
    Extract overall product rating and total reviews with robust error handling.

    Args:
        rating_element (Optional[Any]): The rating element from the webpage

    Returns:
        tuple: (overall rating, total reviews)
    """
    if not rating_element:
        return "N/A", "N/A"

    try:
        rating_text = rating_element.text
        overall_rating_match = re.search(r'(\d+(\.\d+)?) out of 5 stars', rating_text)
        total_reviews_match = re.search(r'(\d+) reviews', rating_text)

        overall_rating = f"{overall_rating_match.group(1)}/5 Stars" if overall_rating_match else "N/A"
        total_reviews = int(total_reviews_match.group(1)) if total_reviews_match else "N/A"

        return overall_rating, total_reviews
    except Exception as e:
        logging.error(f"Error extracting rating: {e}")
        return "N/A", "N/A"

def extract_stock_availability(driver: webdriver.Chrome):
    """
    Extract stock status and available stock quantity with comprehensive error handling.

    Args:
        driver (webdriver.Chrome): Active Selenium WebDriver instance

    Returns:
        int or str: Number of items in stock or 'N/A'
    """
    try:
        stock_status_element = safe_find_element(
            driver,
            By.XPATH,
            "//div[contains(@class, 'inline-flex items-center') and (contains(text(), 'In stock') or contains(text(), 'Out of stock'))]"
        )

        if not stock_status_element:
            return "N/A"

        stock_status_text = stock_status_element.text

        if "Out of stock" in stock_status_text:
            return 0
        elif "In stock" in stock_status_text:
            stock_text_element = safe_find_element(
                driver,
                By.XPATH,
                "//p[contains(@class, 'ml-2') and contains(@class, 'text-sm') and contains(@class, 'text-gray-500')]"
            )

            if not stock_text_element:
                return "Unspecified Stock"

            stock_text = stock_text_element.text
            stock_match = re.search(r'(\d+)', stock_text)
            return int(stock_match.group(1)) if stock_match else "Unspecified Stock"
        else:
            return "N/A"
    except Exception as e:
        logging.error(f"Comprehensive error in stock availability extraction: {e}")
        return "N/A"

def extract_reviews(driver: webdriver.Chrome):
    """
    Extract customer reviews with advanced error handling and logging.

    Args:
        driver (webdriver.Chrome): Active Selenium WebDriver instance

    Returns:
        List[Dict[str, Any]]: List of review dictionaries
    """
    reviews = []
    reviewID = 0

    try:
        review_elements = safe_find_elements(
            driver,
            By.CSS_SELECTOR,
            'div.border-b.border-gray-200.pb-8'
        )

        if not review_elements:
            logging.warning("No review elements found")
            return reviews

        for review in review_elements:
            try:
                review_data = {}
                reviewID += 1
                review_data["Review ID"] = reviewID

                # Reviewer Name
                reviewer_info_element = safe_find_element(review, By.XPATH, ".//p[@class='text-sm text-gray-500']")
                reviewer_info = reviewer_info_element.text if reviewer_info_element else "Unknown"
                name_match = re.search(r'By (.+?) on', reviewer_info)
                review_data["Name"] = name_match.group(1) if name_match else "Anonymous"

                # Rating
                rating_stars = safe_find_elements(review, By.CSS_SELECTOR, 'svg.text-yellow-400')
                review_data["Rating"] = f"{len(rating_stars)}/5 Stars"

                # Review Title
                review_title_element = safe_find_element(review, By.XPATH, ".//p[@class='ml-3 text-sm font-medium text-gray-900']")
                review_data["Title"] = review_title_element.text if review_title_element else "Untitled Review"

                # Review Date
                review_p_elements = safe_find_elements(review, By.XPATH, ".//p")
                review_date_text = review_p_elements[-1].text if len(review_p_elements) > 1 else "N/A"
                match = re.search(r'on (\d{1,2}/\d{1,2}/\d{4})', review_date_text)
                review_data["Date"] = match.group(1) if match else "Unknown Date"

                # Review Body
                review_body_element = safe_find_element(review, By.XPATH, ".//p[contains(@class, 'text-base') and contains(@class, 'text-gray-900')]")
                review_data["Review Body"] = review_body_element.text if review_body_element else "No review text"

                # Review Checksum
                checksum_element = safe_find_element(review, By.XPATH, ".//code[contains(@class, 'text-xs') and contains(@class, 'font-mono')]")
                review_data["Review Checksum"] = checksum_element.text if checksum_element else "No Checksum"

                reviews.append(review_data)

            except Exception as review_error:
                logging.error(f"Error processing individual review: {review_error}")
                continue

        return reviews

    except Exception as e:
        logging.error(f"Comprehensive error in review extraction: {e}")
        return reviews

def scrape_product(driver: webdriver.Chrome, product_id: int):
    """
    Scrape product details with comprehensive error handling.

    Args:
        driver (webdriver.Chrome): Active Selenium WebDriver instance
        product_id (int): Product ID to scrape

    Returns:
        Optional[Dict[str, Any]]: Product details dictionary or None if scraping fails
    """
    url = f"https://hiring-xry4.onrender.com/products/{product_id}"

    try:
        driver.get(url)
        WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, "//h1[contains(@class, 'text-3xl') and contains(@class, 'font-bold')]"))) # Wait for product title to load
        logging.info(f"Scraping details from: {url}") # Log the URL

        # Check if the page contains products
        product_titles = safe_find_elements(
            driver,
            By.XPATH,
            "//h1[contains(@class, 'text-3xl') and contains(@class, 'font-bold')]"
        )

        if not product_titles:
            logging.warning(f"No product found on page {product_id}")
            return None

        # Scrape product data with fallback values
        row = {}
        row["Product Title"] = safe_find_element(
            driver,
            By.XPATH,
            "//h1[contains(@class, 'text-3xl') and contains(@class, 'font-bold')]"
        ).text if safe_find_element(driver, By.XPATH, "//h1[contains(@class, 'text-3xl') and contains(@class, 'font-bold')]") else "Untitled Product"

        row["Price"] = safe_find_element(
            driver,
            By.XPATH,
            "//p[contains(@class, 'text-3xl') and contains(@class, 'tracking-tight') and contains(@class, 'text-gray-900')]"
        ).text if safe_find_element(driver, By.XPATH, "//p[contains(@class, 'text-3xl') and contains(@class, 'tracking-tight') and contains(@class, 'text-gray-900')]") else "Price Unavailable"

        row["Categories"] = [category.text for category in safe_find_elements(
            driver,
            By.XPATH,
            "//a[contains(@class, 'bg-primary-100') and contains(@class, 'text-primary-800')]"
        )]

        row["Product Image URLs"] = [
            img.get_attribute('src')
            for img in safe_find_elements(
                driver,
                By.XPATH,
                "//img[@class='h-full w-full object-cover object-center']"
            )
        ]

        row["Description"] = safe_find_element(
            driver,
            By.XPATH,
            "//p[@class='text-base text-gray-700']"
        ).text if safe_find_element(driver, By.XPATH, "//p[@class='text-base text-gray-700']") else "No Description Available"

        # Overall Rating
        overall_rating_element = safe_find_element(
            driver,
            By.XPATH,
            "//div[@class='flex items-center']/p[@class='ml-3 text-sm text-gray-700']"
        )
        row["Overall Rating"], row["Total Reviews"] = extract_overall_rating(overall_rating_element)

        # Stock Status
        stock_status_element = safe_find_element(
            driver,
            By.XPATH,
            "//div[contains(@class, 'inline-flex items-center') and (contains(text(), 'In stock') or contains(text(), 'Out of stock'))]"
        )
        row["Inventory Status"] = stock_status_element.text if stock_status_element else "Stock Status Unavailable"
        row["Inventory Stock Available"] = extract_stock_availability(driver)

        # SKU
        sku_element = safe_find_element(
            driver,
            By.XPATH,
            "//p[@class='text-sm text-gray-500']"
        )
        row["SKU"] = sku_element.text.replace("SKU: ", "") if sku_element else "SKU Unavailable"

        # Product Checksum
        checksum_elements = safe_find_elements(
            driver,
            By.XPATH,
            "//code[contains(@class, 'text-xs') and contains(@class, 'font-mono')]"
        )
        row["Product Checksum"] = checksum_elements[0].text if checksum_elements else "N/A"

        # Customer Reviews
        row["Customer Reviews"] = extract_reviews(driver)

        return row

    except TimeoutException:
        logging.error(f"Timeout occurred while scraping product {product_id}")
        print(f"Error: No product found on page {product_id}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error processing product ID {product_id}: {e}")
        logging.error(traceback.format_exc())
        return None

#                                  #range start is inclusive, range end is exclusive
def main(product_id_range: range = range(1, 52), output_file: str = 'def2Upgrade1.json', headless: bool = True): 
    """
    Main function to scrape product data with comprehensive error handling.

     Key Responsibilities:
        - Initialize WebDriver
        - Iterate through product IDs
        - Handle scraping errors
        - Generate detailed JSON output
        - Track and log scraping statistics

    Arguments Passed:
        product_id_range (range): Range of product IDs to scrape. Defaults to range(1, 52) to include all products plus show error handling.
        output_file (str): Outputs JSON file name. Defaults to 'def2Upgrade.json'
        headless (bool): Whether to run browser in headless mode. Defaults to True
    """
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('scraper.log'),  # Log to file
            logging.StreamHandler(sys.stdout)    # Log to console
        ]
    )

    # Track scraping statistics
    total_attempted = 0
    total_successful = 0
    failed_products = []

    driver = None
    try:
        # Initialize WebDriver
        driver = setup_webdriver(headless)

        # Final container for scraped data that will be saved to JSON later
        data = []

        for id in product_id_range: # Iterate through product IDs that were passed as arguments above
            total_attempted += 1
            try:
                product_data = scrape_product(driver, id) # This variable will hold the data scraped from the individual product and will later be appended to the data list
                if product_data:
                    data.append(product_data)
                    total_successful += 1
                else:
                    failed_products.append(id)
            except Exception as e:
                logging.error(f"Error scraping product {id}: {e}")
                failed_products.append(id)

        # Save data to JSON file
        with open(output_file, 'w') as json_file:
            json.dump(data, json_file, indent=4)

        # Log scraping statistics
        logging.info(f"Scraping complete")
        logging.info(f"Total products attempted: {total_attempted}")
        logging.info(f"Total products successfully scraped: {total_successful}")
        if failed_products:
            logging.warning(f"Failed product IDs: {failed_products}")

    except Exception as e:
        logging.error(f"An unexpected error occurred during scraping: {e}")
        logging.error(traceback.format_exc())

    finally:
        # Close the driver if it was created
        if driver:
            driver.quit()

if __name__ == "__main__":
    main()
