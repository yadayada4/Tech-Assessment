
Steps to Run Program on Your Machine:

1. Ensure Python is installed and up to date. (I am using Python 3.12.4 on my machine.)
2. Create and Activate Virtual Environment (To Create: python -m venv venv , To Activate: Windows - venv\Scripts\activate  macOS/Linux - source venv/bin/activate ) 
3. Install Dependencies ( pip install selenium , pip install webdriver-manager )
4. Install Google Chrome browser (latest version recommended)
5. Download the Python script
6. Place the script in a dedicated project directory
7. Modify code if needed. (Set current_page variable near top of code to the page number you want to start at. At the end of the program choose file you want to write to. )

8. Finally, Run the Script 

Program Summary:
---------------------------------------------------------------------------
Web Scraper for Product and Review Data

This script uses Selenium WebDriver to scrape product and review information
from a specified e-commerce website. It performs the following key actions:

- Navigates through multiple pages of product listings
- Extracts detailed information for each product, including:
  * Product title, price, categories
  * Product images
  * Description
  * Overall rating and review count
  * Stock status and availability
  * SKU and product checksum

- For each product, it also scrapes individual customer reviews, capturing:
  * Reviewer name
  * Review rating
  * Review title
  * Review date
  * Review body
  * Review checksum

Output:
- Saves scraped data to a JSON file named 'productsPaginated.json'


