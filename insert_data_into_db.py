import mysql.connector as connector
import config
import json
from mysql.connector import Error

configuration = config.mysql_credentials

# Load the JSON file containing car part prices
with open('car_parts_prices.json', 'r') as file:
    car_parts_prices = json.load(file)

try:
    connection = connector.connect(**configuration)
    if connection.is_connected():
        print("Connected to MySQL Database.")
        
        # Use a cursor with context manager
        with connection.cursor() as cursor:
            # Loop through car_models dictionary and insert data
            for brand, models in car_parts_prices.items():
                for model, parts in models.items():
                    for part, price in parts.items():
                        # Optional: check if this entry already exists
                        cursor.execute(
                            "SELECT COUNT(*) FROM car_models WHERE brand=%s AND model=%s AND part=%s",
                            (brand, model, part)
                        )
                        count = cursor.fetchone()[0]
                        if count == 0:
                            cursor.execute(
                                "INSERT INTO car_models (brand, model, part, price) VALUES (%s, %s, %s, %s)",
                                (brand, model, part, price)
                            )
            # Commit all changes
            connection.commit()
        print("Data has been successfully inserted into the MySQL database.")

except Error as e:
    print(f"Error connecting or executing query: {e}")

finally:
    if connection.is_connected():
        connection.close()
        print("MySQL Connection is Closed.")
