"""
Module containing utility functions for email notification system.
"""

import os, smtplib, ssl
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from string import Template


def generate_messages(form_data, email_addresses):
    """
    Given form data (dictionary) and sender / receiver email addresses (tuple), 
    generates a plain text and HTML message to be sent over email
    """

    # Get CSS styles for email template
    email_styles = ""
    try:
        email_css_file = os.path.join(Path.cwd(), "assets", "email.style.css")
        with open(email_css_file, encoding='utf-8') as f:
            email_styles = f.read()
    except Exception as e:
        print(e)

    # Get sender and receiver email addresses
    sender, receiver = email_addresses

    # Build message object for sending 
    message = MIMEMultipart("alternative")
    message["Subject"] = "Message from Portfolio"
    message["From"] = sender
    message["To"] = receiver

    # Build messages from template in plain text and html format    
    txt_template = Template("""
    Name: $name
    Email: $email
    Message: $message
    """)
    text_msg = txt_template.substitute(
        name=form_data["name"], email=form_data["email"], message=form_data["message"])

    html_template = Template("""
    <html>
      <head>
        <style> $styles </style>
      </head>
      <body style='border-radius: 2rem;'>
        <h1>New Message from Porfolio</h1>
        <br/>
        <h3>Name:</h3> 
        <p> $name </p>
        
        <h3>Email:</h3> 
        <p> $email </p>

        <h3>Message:</h3> 
        <p> $message </p>
      </body>
    </html>
    """)
    html_msg = html_template.substitute(
        styles=email_styles, name=form_data["name"], email=form_data["email"], message=form_data["message"])

    # Turn messages into plain/html MIMEText objects
    text_mimetext = MIMEText(text_msg, "plain")
    html_mimetext = MIMEText(html_msg, "html")

    # Attach mimtext messages to object
    message.attach(text_mimetext)
    message.attach(html_mimetext)

    return message


def send_email_notification(msg, email_addresses):
    """
    Given a message (MIMEMultipart) and sender / receiver email addresses (tuple), 
    sends a notification to the receiver address with the message as a body.
    """

    # Get relevant environment variables
    smtp_server = os.environ.get("SMTP_SERVER")
    smtp_port = os.environ.get("SMTP_PORT")
    sender_password = os.environ.get("SENDER_PASSWORD")
    
    # Get sender and receiver email addresses
    sender, receiver = email_addresses

    # Create a secure connection context for email server
    context = ssl.create_default_context()

    try:
        # Setup SMTP server
        server = smtplib.SMTP(smtp_server, smtp_port)
        
        # Secure the connection
        server.starttls(context=context) 
        
        # Login to SMTP server
        server.login(sender, sender_password)

        # Send the email
        server.sendmail(sender, receiver, msg.as_string()) 
    except Exception as e:
        # Print error messages
        print("An error has occurred when sending notification...")
    finally:
        # Quit server
        server.quit()
