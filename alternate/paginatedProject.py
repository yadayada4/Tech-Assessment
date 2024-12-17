import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import re
import time



# List to store all the scraped product data
data = []

# Initialize the WebDriver
driver = webdriver.Chrome()

# Set the initial page number
current_page = 1
while True:

    # Construct URL for the current page
    url = f"https://hiring-xry4.onrender.com/products?page={current_page}"
    driver.get(url)
    time.sleep(2)  # Wait for the page to load

    # Get all product links on the current page
    product_links = driver.find_elements(By.XPATH, "//a[@class='group']")
    # Extract the href attributes (URLs) from the product links
    product_urls = [link.get_attribute("href") for link in product_links]

    # If no product links are found, break the loop to stop scraping
    if not product_urls:
        break

    # Loop through each product URL
    for url in product_urls:
        
        row = {}  # Dictionary to store data for the current product
        driver.get(url)  # Navigate to the product page
        print(f"Scraping details from: {url}")
        time.sleep(2)  # Wait for the page to load
        
        # Scrape product title
        row["Product Title"] = driver.find_element(By.XPATH, "//h1[contains(@class, 'text-3xl') and contains(@class, 'font-bold')]").text
        # Scrape product price
        row["Price"] = driver.find_element(By.XPATH, "//p[contains(@class, 'text-3xl') and contains(@class, 'tracking-tight') and contains(@class, 'text-gray-900')]").text
        # Scrape product categories
        row["Categories"] = [category.text for category in driver.find_elements(By.XPATH, "//a[contains(@class, 'bg-primary-100') and contains(@class, 'text-primary-800')]")]
        # Scrape product image URLs
        row["Product Image URLs"] = [img.get_attribute('src') for img in driver.find_elements(By.XPATH, "//img[@class='h-full w-full object-cover object-center']")]
        # Scrape product description
        row["Description"] = driver.find_element(By.XPATH, "//p[@class='text-base text-gray-700']").text
        
        # Scrape overall product rating and review count
        overall_rating_element = driver.find_element(By.XPATH, "//div[@class='flex items-center']/p[@class='ml-3 text-sm text-gray-700']")
        overall_rating_text = overall_rating_element.text
        overall_rating_match = re.search(r'(\d+(\.\d+)?) out of 5 stars', overall_rating_text)
        row["Overall Rating"] = f"{overall_rating_match.group(1)}/5 Stars" if overall_rating_match else "N/A"
        row["Total Reviews"] = int(re.search(r'(\d+) reviews', overall_rating_text).group(1)) if re.search(r'(\d+) reviews', overall_rating_text) else "N/A"
        
        # Scrape stock status and availability
        row["Stock Status"] = driver.find_element(By.XPATH, "//div[contains(@class, 'inline-flex items-center') and (contains(text(), 'In stock') or contains(text(), 'Out of stock'))]").text
        stock_status_text = driver.find_element(By.XPATH, "//div[contains(@class, 'inline-flex items-center') and (contains(text(), 'In stock') or contains(text(), 'Out of stock'))]").text

        # Determine available stock count based on status
        if "Out of stock" in stock_status_text:
            row["Stock Available"] = 0
        elif "In stock" in stock_status_text:
            text = driver.find_element(By.XPATH, "//p[@class='ml-2 text-sm text-gray-500']").text
            number = int(re.search(r'(\d+)', text).group(1))
            row["Stock Available"] = number
        else:
            row["Stock Available"] = "N/A"  # Fallback for missing data

        # Scrape SKU (Stock Keeping Unit)
        sku_text = driver.find_element(By.XPATH, "//p[@class='text-sm text-gray-500']").text
        row["SKU"] = re.sub(r"SKU:\s*", "", sku_text)  # Remove the "SKU:" prefix
        
        # Scrape product checksum if available
        product_checksum = driver.find_element(By.XPATH, ".//code[contains(@class, 'text-xs') and contains(@class, 'font-mono')]").text if driver.find_elements(By.XPATH, ".//code[contains(@class, 'text-xs') and contains(@class, 'font-mono')]") else "N/A"
        row["Product Checksum"] = product_checksum

        ############
        reviews = []  # List to store review data for the current product
        review_elements = driver.find_elements(By.CSS_SELECTOR, 'div.border-b.border-gray-200.pb-8')  # Locate reviews on the product page

        reviewID = 0  # Initialize unique ID counter for reviews
        # Loop through all reviews for the current product
        for review in review_elements:
            review_data = {}  # Dictionary to store individual review data

            try:
                reviewID += 1
                review_data["Review ID"] = reviewID

                # Extract reviewer name and date
                reviewer_info = review.find_element(By.XPATH, ".//p[@class='text-sm text-gray-500']").text
                name_match = re.search(r'By (.+?) on', reviewer_info)
                review_data["Reviewer Name"] = name_match.group(1) if name_match else "N/A"

                # Count the number of yellow stars (rating)
                yellow_stars = review.find_elements(By.CSS_SELECTOR, 'svg.text-yellow-400')
                num_stars = len(yellow_stars)
                review_data["Rating"] = f"{num_stars}/5 Stars"
                
                # Extract review title
                review_title = driver.find_element(By.XPATH, "//p[@class='ml-3 text-sm font-medium text-gray-900']").text
                review_data["Review Title"] = review_title

                # Try to extract the review date
                review_p_elements = review.find_elements(By.XPATH, ".//p")
                if len(review_p_elements) > 1:
                    review_date_text = review_p_elements[-1].text  # Assume the last <p> contains the date
                    match = re.search(r'on (\d{1,2}/\d{1,2}/\d{4})', review_date_text)
                    review_data["Review Date"] = match.group(1) if match else "N/A"
                else:
                    review_data["Review Date"] = "N/A"

                # Extract the review body text
                review_data["Review Body"] = review.find_element(By.XPATH, ".//p[contains(@class, 'text-base') and contains(@class, 'text-gray-900')]").text if len(review.find_elements(By.XPATH, ".//p[contains(@class, 'text-base') and contains(@class, 'text-gray-900')]")) > 0 else "N/A"

                # Extract review checksum if available
                review_data["Review Checksum"] = review.find_element(By.XPATH, ".//code[contains(@class, 'text-xs') and contains(@class, 'font-mono')]").text if review.find_elements(By.XPATH, ".//code[contains(@class, 'text-xs') and contains(@class, 'font-mono')]") else "N/A"

            except Exception as e:
                print(f"Error processing review: {e}")  # Log any error encountered while scraping reviews

            reviews.append(review_data)

        # Add the reviews data to the product row
        row["Customer Reviews"] = reviews
        # Append the product data to the overall data list
        data.append(row)
    
    # Move to the next page
    current_page += 1

# Write the collected data to a JSON file
with open('productsPaginated.json', 'w') as json_file:
    json.dump(data, json_file, indent=4)

# Close the browser window
time.sleep(2)
driver.close()
