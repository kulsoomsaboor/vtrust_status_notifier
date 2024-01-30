import logging
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
import time

import os
import smtplib
from email.message import EmailMessage
import ssl

# Configure logging
logging.basicConfig(level=logging.INFO)

# Retrieve email credentials from environment variables
sender_email = os.environ.get('SENDER-EMAIL')
receiver_emails = os.environ.get('RECEIVER-EMAIL')  # Comma-separated list of email addresses
email_password = os.environ.get('EMAIL-PASSWORD')

print(receiver_emails)

if not sender_email or not receiver_emails or not email_password:
    logging.error("Email credentials not provided. Please set the SENDER_EMAIL, RECEIVER_EMAILS, and EMAIL_PASSWORD environment variables.")
    exit()

# Convert the comma-separated string of email addresses to a list
receiver_email_list = [email.strip() for email in receiver_emails.split(',')]

def check_vtrust_and_notify():
    while True:
        # Initialize the WebDriver
        driver = webdriver.Chrome()

        # Navigate to the webpage
        driver.get('https://taostats.io/validators/neural-internet/')

        # Adding a delay after the page loads
        time.sleep(2)

        # Wait for the elements to be present on the page
        try:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'staking_data_block')))
        except Exception as e:
            logging.error(f"Error waiting for elements: {e}")
            driver.quit()
            continue  # Continue to the next iteration of the loop

        # locate the data_block
        data_block = driver.find_elements(By.CLASS_NAME, 'staking_data_block')

        # Lists
        SN = []
        Updated = []
        Vtrust = []
        vtrust_below_threshold = []  

        # Process the found elements as needed
        for block in data_block:
            try:
                #SN.append(block.find_element(By.XPATH, './/div[1]/div/small').text)
                SN.append(block.find_element(By.XPATH, './/div[1]/div[@class="stake_val"]/small').text)
                updated_value = block.find_element(By.XPATH, './/div[6]/div/small').text
                Updated.append(updated_value)
                vtrust_value = float(block.find_element(By.XPATH, './/div[7]/div/small').text)
                Vtrust.append(vtrust_value)

                logging.info(f"Data extracted for SN: {SN[-1]}, Updated: {updated_value}, VTrust: {vtrust_value}")

                # Check if Vtrust is below 0.90 and store the information
                if vtrust_value < 0.90:
                    vtrust_below_threshold.append((SN[-1], updated_value, vtrust_value))

            except NoSuchElementException as e:
                logging.error(f"Error extracting data: {e}. Skipping this validator.")
                continue  # Skip to the next iteration if an element is not found
            except ValueError as e:
                logging.error(f"Error converting Vtrust value to float: {e}. Skipping this validator.")
                continue  # Skip to the next iteration if the Vtrust value cannot be converted to float

        # Close the WebDriver
        driver.quit()

        # Check if there are instances where Vtrust is below 0.90 and send a single email to multiple receivers
        if vtrust_below_threshold:
            # Email configuration
            email_subject = 'Vtrust Drop Notification'
            
            # Create EmailMessage object
            msg = EmailMessage()
            
            # Compose email body
            email_body = "The following validators have Vtrust values below 0.90:\n\n"
            for sn, updated_value, vtrust_value in vtrust_below_threshold:
                email_body += f"SN: {sn},    Updated: {updated_value},    Vtrust: {vtrust_value}\n"

            msg.set_content(email_body)
            msg['Subject'] = email_subject
            msg['From'] = sender_email
            msg['To'] = ', '.join(receiver_email_list)  # Join the list of receivers into a comma-separated string

            # Send email using SMTP
            try:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as server:
                    server.login(sender_email, email_password)
                    server.send_message(msg)
                    logging.info("Email notification sent successfully")
            
            except Exception as e:
                logging.error(f"Error sending email notification: {e}")

        # Sleep for 3 hours before the next iteration
        time.sleep(10800)

if __name__ == "__main__":
    check_vtrust_and_notify()
