import os
import psycopg2
from string import Template
from flask import Flask, redirect, request, render_template
from api.utils.email import generate_messages, send_email_notification
from api.utils.config import get_config


app = Flask(__name__)


@app.route("/")
def index():
    """
    Render project's homepage. 
    """
    
    return render_template("index.html")


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
    config = get_config()
    referrers = config["referrers"]
        
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


@app.route('/form')
def form():
    """
    Renders a basic form demo page for testing purposes
    """

    return render_template("form.html")


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    """
    Catch all route / 404
    """
    return redirect("/", code=302)
