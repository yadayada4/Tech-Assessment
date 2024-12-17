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
    """Custom exception for scraping related errors."""
    pass

def setup_webdriver(headless: bool = True, max_retries: int = 3):
    """
    Set up and return a Selenium WebDriver instance with retry mechanism.

    Args:
        headless (bool): Whether to run the browser in headless mode. Defaults to True.
        max_retries (int): Maximum number of retry attempts for WebDriver setup.

    Returns:
        webdriver.Chrome: Configured Chrome WebDriver

    Raises:
        ScraperError: If WebDriver setup fails after max retries
    """
    for attempt in range(max_retries):  # Loop to retry WebDriver setup
        try:
            options = Options()  # Create an instance of the Chrome options
            if headless:
                options.add_argument('--headless')  # Run in headless mode (no UI)

            # Initialize the WebDriver with the specified options
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

            # Set a page load timeout to avoid long waiting times
            driver.set_page_load_timeout(30)

            # Return the initialized driver if successful
            return driver

        except WebDriverException as e:
            # Log the failure of the WebDriver setup and attempt retry
            logging.error(f"WebDriver setup attempt {attempt + 1} failed: {e}")

            # If this is the last retry, raise an error
            if attempt == max_retries - 1:
                raise ScraperError(f"Failed to setup WebDriver after {max_retries} attempts: {e}")

            # Wait for a short period before retrying
            time.sleep(2)  

def safe_find_element(driver: webdriver.Chrome, by: By, value: str, timeout: int = 10):
    """
    Safely find an element with error handling and logging.

    Args:
        driver (webdriver.Chrome): Selenium WebDriver instance used to interact with the browser.
        by (By): Selenium By locator strategy to identify the element.
        value (str): Locator value to find the element.
        timeout (int): Maximum time (in seconds) to wait for the element to appear on the page. Defaults to 10 seconds.

    Returns:
        Optional[Any]: The found WebElement, or None if the element is not found within the timeout.

    Raises:
        ScraperError: If an unexpected error occurs while trying to find the element.
    """
    try:
        # Wait for the element to be present in the DOM
        element = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, value)))
        return element  # Return the element if found

    except NoSuchElementException:  # Element is not found
        # Log a warning and return None if the element is not found
        logging.warning(f"Element not found: {by}={value}")
        return None

    except StaleElementReferenceException:  # Handle case when element is no longer attached to the DOM
        # Log a warning and retry in case the element becomes stale (e.g., due to dynamic content changes)
        logging.warning(f"Stale element encountered: {by}={value}. Retrying...")
        time.sleep(1)  # Brief pause before retrying
        return safe_find_element(driver, by, value, timeout)  # Recursively retry to find the element

    except Exception as e:  # Handle any other unexpected exceptions
        # Log the error and raise a custom exception if an unexpected error occurs
        logging.error(f"Unexpected error finding element {by}={value}: {e}")
        raise ScraperError(f"Failed to find element: {e}")


def safe_find_elements(driver: webdriver.Chrome, by: By, value: str) -> List[Any]:
    """
    Safely find multiple elements with error handling and logging.

    Args:
        driver (webdriver.Chrome): Selenium WebDriver instance used to interact with the browser.
        by (By): Selenium By locator strategy to identify the elements.
        value (str): Locator value to find the elements.

    Returns:
        List[Any]: List of WebELements found, or an empty list if an error occurs.
    """
    try:
        # Attempt to find the elements using the provided locator strategy and value
        elements = driver.find_elements(by, value)
        return elements  # Return the list of found elements

    except Exception as e:  # Catch any unexpected exceptions
        # Log the error and return an empty list if elements cannot be found
        logging.error(f"Error finding elements {by}={value}: {e}")
        return []  # Return an empty list if there's an error


def extract_overall_rating(rating_element: Optional[Any]):
    """
    Extract overall product rating and total reviews with robust error handling.

    Args:
        rating_element (Optional[Any]): The rating element from the webpage containing rating and reviews data.

    Returns:
        tuple: A tuple containing:
            - overall rating (str): Rating formatted as 'x/5 Stars', or 'N/A' if not available.
            - total reviews (int or str): Total number of reviews, or 'N/A' if not available or an error occurs.
    """
    # If the rating element is not provided or is invalid, return "N/A" for both values
    if not rating_element:
        return "N/A", "N/A"

    try:
        # Extract the text content of the rating element
        rating_text = rating_element.text
        
        # Use regular expressions to search for the rating and review count
        overall_rating_match = re.search(r'(\d+(\.\d+)?) out of 5 stars', rating_text)
        total_reviews_match = re.search(r'(\d+) reviews', rating_text)

        # Extract and format the overall rating if a match is found
        overall_rating = f"{overall_rating_match.group(1)}/5 Stars" if overall_rating_match else "N/A"
        
        # Extract the total reviews count if a match is found and convert to an integer
        total_reviews = int(total_reviews_match.group(1)) if total_reviews_match else "N/A"

        return overall_rating, total_reviews  # Return the extracted data

    except Exception as e:  # Catch any unexpected errors that may arise during extraction
        # Log the error and return "N/A" for both values
        logging.error(f"Error extracting rating: {e}")
        return "N/A", "N/A"  # Return "N/A" in case of error to avoid crashing the program


def extract_stock_availability(driver: webdriver.Chrome):
    """
    Extract stock status and available stock quantity with comprehensive error handling.

    Args:
        driver (webdriver.Chrome): Active Selenium WebDriver instance used for interacting with the webpage.

    Returns:
        int or str: Returns the number of items in stock, '0' for out-of-stock items, 'N/A' if unable to extract data, or 'Unspecified Stock' if stock quantity is unclear.
    """
    try:
        # Find the element containing stock status (either "In stock" or "Out of stock")
        stock_status_element = safe_find_element(
            driver,
            By.XPATH,
            "//div[contains(@class, 'inline-flex items-center') and (contains(text(), 'In stock') or contains(text(), 'Out of stock'))]"
        )

        # If no stock status element is found, return "N/A"
        if not stock_status_element:
            return "N/A"

        stock_status_text = stock_status_element.text

        # Check if the item is out of stock
        if "Out of stock" in stock_status_text:
            return 0  # Return 0 if the item is out of stock
        elif "In stock" in stock_status_text:
            # Find the element containing the quantity of in-stock items
            stock_text_element = safe_find_element(
                driver,
                By.XPATH,
                "//p[contains(@class, 'ml-2') and contains(@class, 'text-sm') and contains(@class, 'text-gray-500')]"
            )

            # If the quantity element is not found, return "Unspecified Stock"
            if not stock_text_element:
                return "Unspecified Stock"

            stock_text = stock_text_element.text
            stock_match = re.search(r'(\d+)', stock_text)

            # Return the stock quantity if a match is found, otherwise return "Unspecified Stock"
            return int(stock_match.group(1)) if stock_match else "Unspecified Stock"
        else:
            return "N/A"  # Return "N/A" if the stock status text is unrecognized
    except Exception as e:
        # Log any errors encountered during the extraction process
        logging.error(f"Comprehensive error in stock availability extraction: {e}")
        return "N/A"  # Return "N/A" in case of an error to prevent failure

def extract_reviews(driver: webdriver.Chrome):
    """
    Extract customer reviews with advanced error handling and logging.

    Args:
        driver (webdriver.Chrome): Active Selenium WebDriver instance used for interacting with the webpage.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries where each dictionary contains review details such as ID, name, rating, title, date, body, and checksum.
    """
    reviews = []  # List to store all review data
    reviewID = 0  # Initialize review ID counter

    try:
        # Find all review elements on the page
        review_elements = safe_find_elements(
            driver,
            By.CSS_SELECTOR,
            'div.border-b.border-gray-200.pb-8'
        )

        # If no reviews are found, log a warning and return an empty list
        if not review_elements:
            logging.warning("No review elements found")
            return reviews

        # Loop through each review element
        for review in review_elements:
            try:
                review_data = {}  # Initialize a dictionary to store data for each review
                reviewID += 1  # Increment review ID
                review_data["Review ID"] = reviewID

                # Extract reviewer's name
                reviewer_info_element = safe_find_element(review, By.XPATH, ".//p[@class='text-sm text-gray-500']")
                reviewer_info = reviewer_info_element.text if reviewer_info_element else "Unknown"
                name_match = re.search(r'By (.+?) on', reviewer_info)
                review_data["Name"] = name_match.group(1) if name_match else "Anonymous"

                # Extract rating
                rating_stars = safe_find_elements(review, By.CSS_SELECTOR, 'svg.text-yellow-400')
                review_data["Rating"] = f"{len(rating_stars)}/5 Stars"  # Rating is determined by the number of star elements

                # Extract review title
                review_title_element = safe_find_element(review, By.XPATH, ".//p[@class='ml-3 text-sm font-medium text-gray-900']")
                review_data["Title"] = review_title_element.text if review_title_element else "Untitled Review"

                # Extract review date
                review_p_elements = safe_find_elements(review, By.XPATH, ".//p")
                review_date_text = review_p_elements[-1].text if len(review_p_elements) > 1 else "N/A"
                match = re.search(r'on (\d{1,2}/\d{1,2}/\d{4})', review_date_text)
                review_data["Date"] = match.group(1) if match else "Unknown Date"

                # Extract review body (text of the review)
                review_body_element = safe_find_element(review, By.XPATH, ".//p[contains(@class, 'text-base') and contains(@class, 'text-gray-900')]")
                review_data["Review Body"] = review_body_element.text if review_body_element else "No review text"

                # Extract review checksum (unique identifier)
                checksum_element = safe_find_element(review, By.XPATH, ".//code[contains(@class, 'text-xs') and contains(@class, 'font-mono')]")
                review_data["Review Checksum"] = checksum_element.text if checksum_element else "No Checksum"

                reviews.append(review_data)  # Add the review data to the list

            except Exception as review_error:
                # Log any errors encountered while processing individual reviews, but continue with the next review
                logging.error(f"Error processing individual review: {review_error}")
                continue

        return reviews  # Return the list of extracted reviews

    except Exception as e:
        # Log any errors that occur during the review extraction process
        logging.error(f"Comprehensive error in review extraction: {e}")
        return reviews  # Return the reviews list (could be empty if extraction fails)


def scrape_product(driver: webdriver.Chrome, product_id: int):
    """
    Scrape product details with comprehensive error handling.

    Args:
        driver (webdriver.Chrome): Active Selenium WebDriver instance used to interact with the webpage.
        product_id (int): Product ID to scrape from the product page.

    Returns:
        Optional[Dict[str, Any]]: A dictionary containing product details such as title, price, categories, image URLs, etc.,
        or None if an error occurs during scraping.
    """
    url = f"https://hiring-xry4.onrender.com/products/{product_id}"  # Construct the product page URL

    try:
        driver.get(url)  # Load the product page
        WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, "//h1[contains(@class, 'text-3xl') and contains(@class, 'font-bold')]")))  # Wait for product title to load
        logging.info(f"Scraping details from: {url}")  # Log the URL being scraped

        # Check if the page contains product titles (i.e., product exists on page)
        product_titles = safe_find_elements(
            driver,
            By.XPATH,
            "//h1[contains(@class, 'text-3xl') and contains(@class, 'font-bold')]"
        )

        if not product_titles:  # If no product found, return None
            logging.warning(f"No product found on page {product_id}")
            return None

        # Initialize a dictionary to store scraped product data
        row = {}

        # Scrape the product title with a fallback value
        row["Product Title"] = safe_find_element(
            driver,
            By.XPATH,
            "//h1[contains(@class, 'text-3xl') and contains(@class, 'font-bold')]"
        ).text if safe_find_element(driver, By.XPATH, "//h1[contains(@class, 'text-3xl') and contains(@class, 'font-bold')]") else "Untitled Product"

        # Scrape the product price with a fallback value
        row["Price"] = safe_find_element(
            driver,
            By.XPATH,
            "//p[contains(@class, 'text-3xl') and contains(@class, 'tracking-tight') and contains(@class, 'text-gray-900')]"
        ).text if safe_find_element(driver, By.XPATH, "//p[contains(@class, 'text-3xl') and contains(@class, 'tracking-tight') and contains(@class, 'text-gray-900')]") else "Price Unavailable"

        # Scrape product categories
        row["Categories"] = [category.text for category in safe_find_elements(
            driver,
            By.XPATH,
            "//a[contains(@class, 'bg-primary-100') and contains(@class, 'text-primary-800')]"
        )]

        # Scrape product image URLs
        row["Product Image URLs"] = [
            img.get_attribute('src')
            for img in safe_find_elements(
                driver,
                By.XPATH,
                "//img[@class='h-full w-full object-cover object-center']"
            )
        ]

        # Scrape product description with fallback value
        row["Description"] = safe_find_element(
            driver,
            By.XPATH,
            "//p[@class='text-base text-gray-700']"
        ).text if safe_find_element(driver, By.XPATH, "//p[@class='text-base text-gray-700']") else "No Description Available"

        # Scrape overall rating and total reviews
        overall_rating_element = safe_find_element(
            driver,
            By.XPATH,
            "//div[@class='flex items-center']/p[@class='ml-3 text-sm text-gray-700']"
        )
        row["Overall Rating"], row["Total Reviews"] = extract_overall_rating(overall_rating_element)

        # Scrape stock availability and status
        stock_status_element = safe_find_element(
            driver,
            By.XPATH,
            "//div[contains(@class, 'inline-flex items-center') and (contains(text(), 'In stock') or contains(text(), 'Out of stock'))]"
        )
        row["Inventory Status"] = stock_status_element.text if stock_status_element else "Stock Status Unavailable"
        row["Inventory Stock Available"] = extract_stock_availability(driver)

        # Scrape SKU information
        sku_element = safe_find_element(
            driver,
            By.XPATH,
            "//p[@class='text-sm text-gray-500']"
        )
        row["SKU"] = sku_element.text.replace("SKU: ", "") if sku_element else "SKU Unavailable"

        # Scrape product checksum (unique identifier)
        checksum_elements = safe_find_elements(
            driver,
            By.XPATH,
            "//code[contains(@class, 'text-xs') and contains(@class, 'font-mono')]"
        )
        row["Product Checksum"] = checksum_elements[0].text if checksum_elements else "N/A"

        # Scrape customer reviews
        row["Customer Reviews"] = extract_reviews(driver)

        return row  # Return the dictionary with all scraped product details

    except TimeoutException:
        # Handle timeout error if the product page fails to load within the given time
        logging.error(f"Timeout occurred while scraping product {product_id}")
        print(f"Error: No product found on page {product_id}")
        return None  # Return None if the page load times out

    except Exception as e:
        # Handle unexpected errors and log the stack trace
        logging.error(f"Unexpected error processing product ID {product_id}: {e}")
        logging.error(traceback.format_exc())
        return None  # Return None if any other unexpected error occurs


#                                  #range start is inclusive, range end is exclusive
def main(product_id_range: range = range(1, 52), output_file: str = 'products1.json', headless: bool = True): 
    """
    Main function to scrape product data with comprehensive error handling.

    Key Responsibilities:
        - Initialize WebDriver
        - Iterate through product IDs
        - Handle scraping errors
        - Generate detailed JSON output
        - Track and log scraping statistics

    Arguments Passed:
        product_id_range (range): Range of product IDs to scrape. Defaults to range(1, 52).
        output_file (str): Output JSON file name. Defaults to 'products1.json'.
        headless (bool): Whether to run the browser in headless mode. Defaults to True.
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
    total_attempted = 0  # Total number of product IDs attempted for scraping
    total_successful = 0  # Total number of products successfully scraped
    failed_products = []  # List to track failed product IDs

    driver = None
    try:
        # Initialize WebDriver
        driver = setup_webdriver(headless)

        # Final container for Scraped data that will be saved to JSON later
        data = []

        # Iterate through product IDs that were passed as arguments above
        for id in product_id_range: 
            total_attempted += 1  # Increment the attempted counter
            try:
                # Scrape product data for the current product ID
                product_data = scrape_product(driver, id)
                if product_data:
                    data.append(product_data)  # Add successfully scraped data to the list
                    total_successful += 1  # Increment successful counter
                else:
                    failed_products.append(id)  # Add failed product ID to the list
            except Exception as e:
                logging.error(f"Error scraping product {id}: {e}")  # Log errors for the specific product
                failed_products.append(id)  # Add failed product ID to the list

        # Save scraped data to a JSON file
        with open(output_file, 'w') as json_file:
            json.dump(data, json_file, indent=4)  # Write the data to the JSON file

        # Log scraping statistics
        logging.info(f"Scraping complete")
        logging.info(f"Total products attempted: {total_attempted}")
        logging.info(f"Total products successfully scraped: {total_successful}")
        if failed_products:
            logging.warning(f"Failed product IDs: {failed_products}")  # Log failed product IDs

    except Exception as e:
        # Log any unexpected errors that occur during the scraping process
        logging.error(f"An unexpected error occurred during scraping: {e}")
        logging.error(traceback.format_exc())  # Log the full traceback for debugging

    finally:
        # Ensure the WebDriver is properly closed at the end of the process
        if driver:
            driver.quit()  # Quit the WebDriver session, closing the browser


if __name__ == "__main__":
    main()
"""
This makes the code reusable by ensuring the script does not execute when imported as a module.
It only runs the `main()` function if the script is executed directly, allowing the functions to be imported elsewhere without triggering the main process.
"""
