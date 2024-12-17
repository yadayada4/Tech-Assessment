
Steps to Run the Program on Your Machine:

1. Ensure Python is installed and up to date. (I am using Python 3.12.4 on my machine.)
2. Create a Virtual Environment ( python -m venv venv )
3. Activate Virtual Environment ( Windows Command --> venv\Scripts\activate || macOS/Linux Command --> source venv/bin/activate ) 
4. Install Dependencies ( pip install selenium , pip install webdriver-manager )
5. Install Google Chrome browser (latest version recommended)
6. Download the Python Program
7. Place the Program in a dedicated project directory
8. Modify code in main() function parameters if needed:

	- Adjust product_id_range for range of product IDs to scrape.
	- Change output_file name
	- Set headless mode (True/False) for browser visibility.

9. Finally, Run the Program 



---------------------------------


Why I Used The Technologies I Did

- I worked in VS Code because the interface is nice and helps me find issues with my code quickly. I chose Python to write the program because of its simplicity, versatility, large ecosystem of libraries, and strong community support. It seemed like the best all around choice for this specific task and I have previous experience with it as well. I chose Selenium because I had prior experience using it for web scraping, which made me comfortable with the tool. Additionally, it provided all the functionality I needed for this assessment and more. JSON was chosen as the output format because it is easy to read/use and perfect for the nested data/reviews underneath each product. I also used ChatGPT to automate repetitive tasks, enhance my code, and to speed up things like generating the correct XPaths, CSS selectors, ect…

---------------------------------


What Went Well

- Overall, I felt like the project went really well! I was able to scrape each element with relative ease. It didn’t feel stressful, but it was more fun than anything! Making multiple versions of the project was fun and challenged the way I think about solving problems in the future.

---------------------------------

What Didn't Go Well

- There wasn’t anything major that didn’t go well. I did end up making too many different versions of the project which was fun at first but it ended up confusing me and diverting time away from perfecting one program. I would approach it differently next time. My workspace and folders also need to be more organized in the future.

---------------------------------

Final Thoughts

- Overall this was a fun assessment! I enjoyed playing around with the different ways I could approach this problem. I took a couple of different approaches to scraping the website. I went with scrapeProductsFinal.py as my preferred project. This version streamlines the process by directly accessing each product's URL, bypassing the need to navigate through intermediate pages. It also is a more complete program in general, including better error handling, reusability, and more. That is why I chose scrapeProductFinal.py as my main submission. The other version (paginatedProject.py) iteratively fetches product listings from paginated results, processing each page sequentially but it has less error handling, less reusability, and is not nearly as robust. 
