import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Load JSON file containing scraped product data
with open('products1.json', 'r') as f:
    data = json.load(f)

# Convert JSON data into a pandas DataFrame
df = pd.DataFrame(data)

# Analyze products
print("Total number of products scraped:", len(df))
print("\nProduct Titles:")
print(df['Product Title']) # Print all product titles from the DataFrame

# Cleaning and analyzing prices
print("\nPrice Statistics:")
df['Price'] = df['Price'].str.replace('$', '').astype(float) # Remove dollar sign and convert to float to clean for analysis
print(df['Price'].describe()) # Print descriptive statistics of product prices

# Analyze categories
print("\nCategories:")
all_categories = [cat for cats in df['Categories'] for cat in cats] # Extract all categories from nested lists and create a Series
print(pd.Series(all_categories).value_counts()) # Count the number of products in each category
category_counts = pd.Series(all_categories).value_counts()  # Count the number of products in each category

# Analyze ratings
print("\nOverall Ratings:")
# Extract the rating value (before the slash) and convert to float
df['Rating'] = df['Overall Rating'].str.split('/').str[0].astype(float)
print(df['Rating'].describe()) # Print descriptive statistics of overall ratings

# Analyze reviews -- # Combine all reviews from each product into a single list
all_reviews = [review for product in data for review in product['Customer Reviews']]
review_df = pd.DataFrame(all_reviews)


print("\nReview Statistics:")
print("Total Reviews:", len(review_df)) # Count the total number of reviews
print("\nRating Distribution:")
print(review_df['Rating'].value_counts()) # Count the number of reviews for each rating value

print("\nMost Common Reviewers:")
print(review_df['Name'].value_counts().head()) # Count reviewer occurrences (top 5)





# Visualize Price Statistics
plt.figure(figsize=(10, 6))
sns.histplot(df['Price'], kde=True, bins=20)
plt.title('Distribution of Prices')
plt.xlabel('Price')
plt.ylabel('Frequency')
plt.show()


#Visualize Category Distribution
plt.figure(figsize=(10, 6))
sns.barplot(x=category_counts.index, y=category_counts.values, palette='viridis')
plt.title('Distribution of Product Categories')
plt.xlabel('Category')
plt.ylabel('Count')
plt.xticks(rotation=45)  # Rotate x-axis labels for better readability
plt.show()


# Visualize the distribution of product ratings
plt.figure(figsize=(8, 8))
review_df['Rating'].value_counts().plot.pie(autopct='%1.1f%%', startangle=140, colors=sns.color_palette('viridis'))
plt.title('Distribution of Product Ratings')
plt.ylabel('')  # Remove the ylabel for a cleaner look
plt.show()


# Visualize Most Common Reviewers
plt.figure(figsize=(10, 6)) # Set figure size for better visualization
sns.countplot(y=review_df['Name'], order=review_df['Name'].value_counts().iloc[:10].index) # Plot a count plot of the top 10 most common reviewers
plt.title('Top 10 Most Common Reviewers')
plt.show() # Display the plot