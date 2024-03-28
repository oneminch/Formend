import os, smtplib, ssl
import psycopg2
from pathlib import Path
from string import Template
from flask import Flask, redirect, request
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


app = Flask(__name__)


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


@app.route("/")
def index():
    """
    Render basic home page specifying what the project is. 
    """
    
    html = """
    <html>
        <head>
            <title>Form Backend</title>
            <script src="https://cdn.tailwindcss.com"></script>
            <link rel="preconnect" href="https://fonts.bunny.net">
            <link href="https://fonts.bunny.net/css?family=ibm-plex-mono:400" rel="stylesheet" />
            <style>
                * { font-family: "IBM Plex Mono", monospace; }
            </style>
        </head>
        <body class="bg-gray-800">
            <section 
                class="mx-auto w-11/12 mt-10 max-w-[56rem] border-2 border-gray-600 rounded-xl bg-gray-700  text-gray-50 px-10 py-12">
                <h2 
                    class="text-center mb-8 text-2xl">
                    This project is a serverless backend that handles form submissions for my projects.
                </h2>
                <h3 
                    class="text-center font-mono my-10 text-8xl font-bold">
                    📋
                </h3>
                <!-- 
                <a 
                    class='text-center inline-block mx-auto py-3 px-5 rounded-lg bg-gray-600' 
                    href='/form'>
                    Go to form
                </a>
                -->
            </section>
        </body>
    </html>
    """

    return html


@app.post("/submit/<string:table_name>")
def submit(table_name):
    """
    Handles form submission by sending form data to an SQL database.
    Stores data in a table provided by the route parameter 'table_name'
    """

    # Get relevant environment variables
    sender_email = os.environ.get("SENDER_EMAIL")
    receiver_email = os.environ.get("RECEIVER_EMAIL")
    
    # referrer_name -> url mappings for redirections
    referrers = { 
        "portfolio": "https://minch.dev/contact",
        "test": "/form"
    }
        
    # Create a tuple of email addresses
    email_addresses = (sender_email, receiver_email)
    
    # Get current table name from route
    table = table_name.lower().strip()

    # Get form data
    form_data = {
        "name": request.form.get("name") or "None",
        "email": request.form.get("email") or "None",
        "message": request.form.get("message").strip()
    }

    # Build redirection URL template
    redirect_url_template = Template("$base_url?status=$status")

    # If empty message, redirect with a 'failure' status url parameter
    if len(form_data["message"]) == 0:
        redirect_url = redirect_url_template.substitute(
            base_url=referrers[table], status="failure")
        
        return redirect(redirect_url, code=302)

    # Get database environment variables
    pg_db = {
        "dbname": os.environ.get("DB_DATABASE"),
        "host": os.environ.get("DB_HOST"),
        "user": os.environ.get("DB_USER"),
        "password": os.environ.get("DB_PASSWORD"),
        "port": os.environ.get("DB_PORT")
    }

    # Connect to SQL database
    conn = psycopg2.connect(**pg_db)

    # Open a cursor to perform database operations
    cursor = conn.cursor()

    # Create table for initializing one database table (demo)
    create_table_sql = """
        CREATE TABLE IF NOT EXISTS {table} (
    	    entry_id serial PRIMARY KEY,
    	    name VARCHAR ( 50 ),
    	    email VARCHAR ( 50 ),
    	    message TEXT NOT NULL,
    	    created_on TIMESTAMP default current_timestamp
        );
    """.format(table=table)

    # if table is available in database
    if table in referrers:
        # SQL query for inserting entries
        insert_values_sql = """
            INSERT INTO {table} (name, email, message)
            VALUES 
                (%s, %s, %s);
        """.format(table=table)

        # Try inserting new form entry
        try:
            cursor.execute(
                insert_values_sql, 
                (form_data["name"], form_data["email"], form_data["message"])
            )
        except Exception as e:
            # Print error message
            print("An error has occurred when inserting into database...")

            # Close communication with the database
            cursor.close()
            conn.close()

            # Redirect with a 'failure' status url parameter
            redirect_url = redirect_url_template.substitute(
                base_url=referrers[table], status="failure")
                
            return redirect(redirect_url, code=302)

        # Make the changes to the database persistent
        conn.commit()

        # Close communication with the database
        cursor.close()
        conn.close()

        # Generate message & send email notification
        message = generate_messages(form_data, email_addresses)
        send_email_notification(message, email_addresses)

        # If successful, redirect with a 'success' status url parameter
        print("Redirecting...")
        
        redirect_url = redirect_url_template.substitute(
            base_url=referrers[table], status="success")
        
        return redirect(redirect_url, code=302)
    
    return "Form endpoint doesn't exist"


# @app.route('/form')
# def form():
#     """
#     Renders a basic form demo page for testing purposes
#     """

#     return """
#       <html>
#         <link rel="stylesheet" href="https://unpkg.com/sakura.css/css/sakura.css" type="text/css">
#       </html>
#       <h1>Form Submission Demo</h1>
#       <br />
#       <form method="post" action="http://localhost:3000/submit/test">
#         <input
#           name="name"
#           type="text"
#           value="Test"
#           placeholder="enter some text"
#         />
#         <input
#           name="email"
#           type="email"
#           value="test@example.com"
#           placeholder="enter some text"
#         />
#         <textarea 
#           name="message"
#           placeholder="Enter message">Hello, world!</textarea>

#         <button type="submit">Submit</button>
#       </form>
#     """


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    """
    Catch all route / 404
    """
    return redirect("/", code=302)
