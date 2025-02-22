from flask import Flask, render_template, request, url_for, flash, redirect, send_from_directory, session
from bs4 import BeautifulSoup
# from controller.py import *
from bson.objectid import ObjectId
from flask import send_file
from datetime import datetime
from dateutil.relativedelta import relativedelta
import csv
import io
import xml.etree.ElementTree as ET
from flask_mail import Mail, Message
from flask import make_response, render_template  # Add make_response to your imports

from flask import make_response
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib import colors
from io import BytesIO

# from app import db

from math import ceil
import os
from werkzeug.utils import secure_filename
from datetime import date, datetime, timedelta
from flask import Flask, request, jsonify
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from flask import (
    Flask, render_template, request, redirect, 
    url_for, session, flash
)

from config import *
# from app import db
# from app.utils.sequence import get_next_sequence



app = Flask(__name__, static_folder='static')

app.config["MONGO_URI"] = MONGO_URI

# Initialize PyMongo client
client = MongoClient(app.config["MONGO_URI"])

# Access a specific database
db = client[MONGODB_DB]

# Example collection
collection = db[MONGODB_FORM_COLLECTION]

users_collection = db[MONGODB_USER_COLLECTION] 

app.config['SECRET_KEY'] = SECRET_KEY
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
ALLOWED_EXTENSIONS = ALLOWED_EXTENSIONS
app.config['LOGO_LOCATION'] = LOGO_LOCATION

app.secret_key = SECRET_KEY
app.config['MAIL_SERVER'] = MAIL_SERVER
app.config['MAIL_PORT']  = MAIL_PORT
app.config['MAIL_USE_TLS'] = MAIL_USE_TLS
app.config['MAIL_USERNAME'] = MAIL_USERNAME # Your Gmail address
app.config['MAIL_PASSWORD'] = MAIL_PASSWORD


mail = Mail(app)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    if 'username' in session:
        return redirect(url_for('welcome'))
    return redirect(url_for('login'))

messages = []

# @app.route('/form')
# def index():
#     #https://www.digitalocean.com/community/tutorials/how-to-use-web-forms-in-a-flask-application
#     return render_template('index.html', messages=messages)


@app.route('/', methods=['GET'])
def index():
    if 'username' in session:
        return redirect(url_for('welcome'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        return redirect(url_for('welcome'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = users_collection.find_one({'username': username})

        if user and check_password_hash(user['password'], password):
            session['username'] = username
            return redirect(url_for('welcome'))
        
        flash('Invalid username or password')
        return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
     # Check if user is logged in and is admin
    if 'username' not in session or session['username'] != 'admin':
        flash('Only admin can create new accounts.', 'error')
        return redirect(url_for('login'))
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        company = request.form['company']
        telNo = request.form['telNo']
        address = request.form['address']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('Passwords do not match')
            return redirect(url_for('register'))
        
        # if users_collection.find_one({'username': username}):
        #     flash('Username already exists')
        #     return redirect(url_for('register'))
        
        hashed_password = generate_password_hash(password)
        users_collection.insert_one({
            'username': username,
            'email': email,
            'password': hashed_password,
            'company': company,
            'address': address,
            'telNo': telNo

        })

        try:
            msg = Message(
                'Your Account Has Been Created',
                sender=app.config['MAIL_USERNAME'],
                recipients=[email]
            )
            
            msg.html = f"""
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                        <h2 style="color: #1a4d6d;">Welcome to Print Order System</h2>
                        <p>Your account has been successfully created.</p>
                        <p>Here are your login credentials:</p>
                        <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                            <p><strong>Username:</strong> {username}</p>
                            <p><strong>Password:</strong> {password}</p>
                        </div>
                        <p>You can login at: <a href="http://127.0.0.1:8000/login">http://127.0.0.1:8000/login</a></p>
                        <p>Please keep this information secure and change your password upon first login.</p>
                        <p style="color: #666; font-size: 0.9em; margin-top: 30px;">
                            This is an automated message, please do not reply.
                        </p>
                    </div>
                </body>
            </html>
            """
            
            mail.send(msg)
            flash('Account created successfully and email sent to user.', 'success')
            
        except Exception as e:
            print(f"Error sending email: {e}")
            flash('Account created successfully but there was an error sending the email.', 'warning')
        
    
        return redirect(url_for('welcome'))
    
    return render_template('customer/register.html')



@app.route('/guest-login', methods=['POST'])
def guest_login():
    session['guest'] = True
    return redirect(url_for('csrform'))

@app.route('/welcome')
def welcome():
    
    if 'username' not in session:
        return redirect(url_for('login'))


    # Pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = ITEMS_PER_PAGE
    skip = (page - 1) * per_page
    
    # Get username
    username = session.get('username')

    # Get date range from query parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    selected_company = request.args.get('company')
    select_status = request.args.get('status')
    select_jobType = request.args.get('jobType')
    search_query = request.args.get('search')
    # print(search_query)


      # Base query for admin to see all records, others see only their own
    if username == 'admin':
        query = {}
    else:
        query = {"customerInfo.contactPerson": username}
    
    
    # Add date filter if dates are provided
    if start_date and end_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            query['orderInfo.deliveryDate'] = {
                '$gte': start.strftime('%Y-%m-%d'),
                '$lte': end.strftime('%Y-%m-%d')
            }
        except ValueError:
            flash('Invalid date format')
    elif start_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            query['orderInfo.deliveryDate'] = {
                '$gte': start.strftime('%Y-%m-%d'),
            }
        except ValueError:
            flash('Invalid date format')
    elif end_date:
        try:
            end = datetime.strptime(end_date, '%Y-%m-%d')
            query['orderInfo.deliveryDate'] = {
                '$lte': end.strftime('%Y-%m-%d')
            }
        except ValueError:
            flash('Invalid date format')
    
    if search_query:
        # Search in multiple fields using case-insensitive regex
        query['$or'] = [
            {'orderInfo.orderId': {'$regex': search_query, '$options': 'i'}},
            {'customerInfo.contactPerson': {'$regex': search_query, '$options': 'i'}},
            {'company': {'$regex': search_query, '$options': 'i'}},
            {'jobInfo.notes': {'$regex': search_query, '$options': 'i'}},
            {'order.orderInfo.deliveryType': {'$regex': search_query, '$options': 'i'}},
            {'order.orderInfo.orderDate': {'$regex': search_query, '$options': 'i'}},
            {'order.orderInfo.deliveryDate': {'$regex': search_query, '$options': 'i'}},
            {'status': {'$regex': search_query, '$options': 'i'}},
            
        ]
                  
    
     # If company is selected, get all users from that company
    if selected_company:
        users_with_company = list(db.users.find(
            {'company': selected_company}, 
            {'_id': 1, 'username': 1}
        ))
        user_ids = [str(user['username']) for user in users_with_company]
        query['customerInfo.contactPerson'] = {'$in': user_ids}

    if select_status:
        query['status'] = select_status  
    # Get paginated orders
    page = request.args.get('page', 1, type=int)
    per_page = ITEMS_PER_PAGE
    skip = (page - 1) * per_page
    
    total_orders = db.form.count_documents(query)
    total_pages = ceil(total_orders / per_page)
    
    orders = list(db.form.find(query)
                 .sort('_id', -1)
                 .skip(skip)
                 .limit(per_page))
    
    # Get companies for the filter dropdown
    companies = db.users.distinct('company')
    company_list = []
    for company in companies:
        if company:  # Skip empty values
            company_list.append({
                'id': company,
                'name': company
            })
    company_list.sort(key=lambda x: x['name'])

    for order in orders:
        user = db.users.find_one(
            {'username': order['customerInfo']['contactPerson']},
            {'username': 1, 'company': 1, '_id': 0}
        )
        # print(user)

        if user and 'company' in user:
            order['company'] = user['company']
        else:
            order['company'] = 'N/A'
            print(f"No company found for user: {order['customerInfo']['contactPerson']}")
    
  

    template = 'admin/admin.html' if username == 'admin' else 'user/welcome.html'
    return render_template(template, 
                         username=username,
                         orders=orders,
                         page=page,
                         total_pages=total_pages,
                         start_date=start_date,
                         end_date=end_date,
                         selected_company = selected_company,
                         companies=company_list,
                         selected_status=select_status,
                         search_query = search_query)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))



def get_next_sequence(sequence_name):
    sequence_document = db.sequences.find_one_and_update(
        {'_id': sequence_name},
        {'$inc': {'seq': 1}},
        upsert=True,
        return_document=True
    )
    
    # If it's a new sequence, initialize it
    if not sequence_document:
        sequence_document = {'seq': 1}
    
    # Format the number to 7 digits with leading zeros
    return f"{sequence_document['seq']:07d}"

@app.route('/view-order/<order_id>', methods=['GET', 'POST'])
def view_order(order_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    try:
        order = db.form.find_one({"_id": ObjectId(order_id)})
        if not order:
            flash('Order not found')
            return redirect(url_for('welcome'))
            
        if request.method == 'POST':
            new_status = request.form.get('status')
            if new_status:
                db.form.update_one(
                    {"_id": ObjectId(order_id)},
                    {"$set": {"status": new_status}}
                )
                flash('Status updated successfully')
                return redirect(url_for('welcome', order_id=order_id))
        
        return render_template('view_order_page1.html', order=order,order_id=order_id)
        
    except Exception as e:
        print(e)
        # flash('Error loading order')
        return redirect(url_for('welcome'))


@app.route('/view-order2/<order_id>/<page>')
def view_order2(order_id, page):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    try:
        # Convert string ID to ObjectId
        order = db.form.find_one({"_id": ObjectId(order_id)})
        if not order:
            flash('Order not found')
            return redirect(url_for('welcome'))
        
        if (page == "2"):
            return render_template('view_order_page2.html', order=order, order_id=order_id)
        else:
            return render_template('view_order_page3.html', order=order, order_id=order_id)
    except Exception as e:
        flash('Error loading order')
        return redirect(url_for('welcome'))

   

@app.route('/view-production/<order_id>', methods=['GET', 'POST'])
def view_production(order_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    try:
        order = db.form.find_one({"_id": ObjectId(order_id)})
        if not order:
            flash('Order not found')
            return redirect(url_for('welcome'))
            
        if request.method == 'POST':
            new_status = request.form.get('status')
            if new_status:
                db.form.update_one(
                    {"_id": ObjectId(order_id)},
                    {"$set": {"status": new_status}}
                )
                flash('Status updated successfully')
                return redirect(url_for('view_production', order_id=order_id))
        
        # return render_template('view_production.html', order=order)
        response = make_response(render_template('view_production.html', order=order))
    
        # Add headers for PDF generation
        response.headers['Content-Security-Policy'] = "default-src 'self' 'unsafe-inline' 'unsafe-eval' data: cdnjs.cloudflare.com *.jquery.com *.bootstrapcdn.com;"
        
        return response
        
    except Exception as e:
        print(e)
        # flash('Error loading order')
        return redirect(url_for('welcome'))


@app.route('/csrform', methods=['GET', 'POST'])
def csrform():
    if 'username' not in session and 'guest' not in session:
        return redirect(url_for('login'))

    username = session.get('username', '')
    email = ''

    
    # If user is logged in, get their email from the database
    if username:
        user = db.users.find_one({'username': username})
        if user:
            email = user.get('email', '')
    
      # Check if this is a repeat order
    order_id = request.args.get('order_id')
    past_order = {}

    if order_id:
        # print(order_id)
        try:
            past_order = db.form.find_one({'_id': ObjectId(order_id)})
            # print(past_order)
        except Exception as e:
            print(f"Error fetching past order: {e}")
            past_order = {}

    today_date = date.today().strftime('%Y-%m-%d')
    # print('reached here')
    # print(request.method )


      # Ensure step 1 is completed
    if 'form_data_step1' not in session:
        flash('Please fill in the customer information first.')
        return redirect(url_for('csrform_step1'))
    # print('this is session')
    # print(session['form_data_step1'])

    
                
    if request.method == 'POST':
        # Get the orderID
        # print('reached here 2')
        order_id = request.form.get('orderId', 'default')

        generatedId = get_next_sequence('order_id')
        
        # Customer Information
        customer_info = {
            "contactPerson": request.form.get('contactPerson'),
            "address": request.form.get('address'),
            "email": request.form.get('email'),
            "telNo": request.form.get('telNo')
        }

        # Billing Information
        billing_info = {
            "contactPerson": request.form.get('billingContactPerson'),
            "address": request.form.get('billingAddress'),
            "email": request.form.get('billingEmail'),
            "telNo": request.form.get('billingTelNo')
        }

        # Order Information
        order_info = {
            "orderName": request.form.get('orderName'),
            "orderId": generatedId,
            "productName": request.form.get('productName'),
            "deliveryDate": request.form.get('deliveryDate'),
            "deliveryType": request.form.get('deliveryType'),
            "quantity": request.form.get('quantity'),
            "orderDate": today_date
        }

        # Job Information
        job_info = {
            "name": request.form.get('name'),
            "id": request.form.get('id'),
            "productType": request.form.get('productType'),
            "numberOfPages": request.form.get('numberOfPages'),
            "notes": request.form.get('notes'),
            "proofing": request.form.get('proofing'),
            "bleedAmount": request.form.get('bleedAmount'),
            "prepressNotes": request.form.get('prepressNotes')
        }

        # Output Information
        output_info = {
            "outputType": request.form.get('outputType'),
            "option": request.form.get('options')
        }

        # Handle file uploads
        uploaded_files = []
        file_paths = []
        
        if 'files' in request.files:
            files = request.files.getlist('files')
            for file in files:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    uploaded_files.append(filename)
                    file_paths.append(file_path)

        # Update files_info to include both filenames and paths
        files_info = {
            "uploadedFiles": uploaded_files,
            "filePaths": file_paths,
            "fileName": (", ".join(str(file).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;') 
                                                    for file in data['filesInfo']['uploadedFiles']))[0],
            "format": (", ".join(str(file).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;') 
                                                    for file in data['filesInfo']['uploadedFiles']))[1],


        }

        # Update service settings to handle all services with option IDs and names
        service_settings = {
            "COLORPRINT": {
                "optionId": request.form.get('colorprint_optionid'),
                "optionName": request.form.get('colorprint_optionname')
            },
            "DUPLEX": {
                "optionId": request.form.get('duplex_optionid'),
                "optionName": request.form.get('duplex_optionname')
            },
            "BINDINGPOSITION": {
                "optionId": request.form.get('bindingposition_optionid'),
                "optionName": request.form.get('bindingposition_optionname')
            },
            "PAGEFITTING": {
                "optionId": request.form.get('pagefitting_optionid'),
                "optionName": request.form.get('pagefitting_optionname')
            },
            "PAPERTYPE": {
                "optionId": request.form.get('papertype_optionid'),
                "optionName": request.form.get('papertype_optionname')
            },
            "PUNCH": {
                "optionId": request.form.get('punch_optionid'),
                "optionName": request.form.get('punch_optionname')
            },
            "STAPLE": {
                "optionId": request.form.get('staple_optionid'),
                "optionName": request.form.get('staple_optionname')
            },
            "FOLD": {
                "optionId": request.form.get('fold_optionid'),
                "optionName": request.form.get('fold_optionname')
            }
        }

        prod_details = {
            "substrate": request.form.get('substrate'),
            "trimSize": request.form.get('trimSize'),
            "layoutSheet": request.form.get('layoutSheet'),
            "layoutSize":request.form.get('layoutSize'),
            "color":request.form.get('colorSpecs')

        }

        # Delivery Information
        delivery_info = {
            "contactPerson": request.form.get('deliveryContactPerson'),
            "address": request.form.get('deliveryAddress'),
            "email": request.form.get('deliveryEmail'),
            "telNo": request.form.get('deliveryTelNo')
        }

        # Combine all data
        form_data = {
            **session['form_data_step1'],
            "orderInfo": order_info,
            "jobInfo": job_info,
            "outputInfo": output_info,
            "prodDetails": prod_details,
            "filesInfo": files_info,
            "serviceSettings": service_settings,
        }

        # Generate XML filename using orderID
        xml_filename = UPLOAD_FOLDER + generatedId + ".xml"
        print(xml_filename)

        print(form_data)
        
        # Save data to XML
        save_data_to_xml(form_data, xml_filename)

        database_data = {
            **session['form_data_step1'],
            "orderInfo": order_info,
            "jobInfo": job_info,
            "outputInfo": output_info,
            "prodDetails": prod_details,
            "filesInfo": files_info,
            "serviceSettings": service_settings,
            "status": "",
        }

        print(database_data)

        collection.insert_one(database_data)

        # Redirect to acknowledgment page with order_id
        return redirect(url_for('acknowledgment', order_id=generatedId))
    # print('printing past')
    # print(past_order)
    return render_template('csrform2new.html', today_date=today_date, username=username, email=email, past_order = past_order)

@app.route('/acknowledgment/<order_id>')
def acknowledgment(order_id):
    return render_template('form/acknowledgment.html', order_id=order_id)

def save_data_to_xml(data, filename):
    """
    Saves form data to an XML file with specific structure.
    """
    root = ET.Element("order")
    
    # Create orderInformation section
    order_information = ET.SubElement(root, "orderInformation")
    
    # Add prefix element
    prefix = ET.SubElement(order_information, "prefix")
    prefix.text = ""  # Empty prefix for now
    
    # Add orderId element
    order_id = ET.SubElement(order_information, "orderId")
    order_id.text = data['orderInfo']['orderId']

    creationDate = ET.SubElement(order_information, "creationDate")
    creationDate.text = date.today().strftime('%Y-%m-%d')

    submitterNote = ET.SubElement(order_information, "submitterNote")
    submitterNote.text = data['jobInfo']['notes']

    projectName = ET.SubElement(order_information, "projectName")
    projectName.text = data['orderInfo']['orderId']

    delivery = ET.SubElement(order_information, "delivery")
    deliveryId = ET.SubElement(delivery, "id")
    deliveryId.text =  ""

    deliveryName = ET.SubElement(delivery, "name")
    deliveryName.text = data['orderInfo']['deliveryType']

    deliveryDate = ET.SubElement(delivery, "date")
    deliveryDate.text = data['orderInfo']['deliveryDate']

    deliveryText = ET.SubElement(delivery, "text")
    deliveryText.text = ""

    days = ET.SubElement(delivery, "days")
    days.text = ""

    price = ET.SubElement(order_information, "price")
    subTotal = ET.SubElement(price, "subtotal")
    subTotal.text = ""

    priceDelivery = ET.SubElement(price, "priceDelivery")
    priceDelivery.text = ""

    totalNet = ET.SubElement(price, "totalNet")
    totalNet.text = ""

    priceTotal = ET.SubElement(price, "total")
    priceTotal.text = ""

    deliveryVat = ET.SubElement(price, "deliveryVat")
    deliveryVat.text = ""

    currency = ET.SubElement(price, "currency")
    currency.text = ""

    customerAccountId = ET.SubElement(order_information, "customerAccountId")
    customerAccountId.text = ""  
    
    billingAddressId = ET.SubElement(order_information, "billingAddressId")
    billingAddressId.text = ""  

    deliveryAddressId = ET.SubElement(order_information, "deliveryAddressId")
    deliveryAddressId.text = ""  

    addresses = ET.SubElement(order_information, "addresses")
    addressesSubmitter = ET.SubElement(addresses, "submitter")

    addressesSubmitterName= ET.SubElement(addressesSubmitter, "name")
    addressesSubmitterName.text = data['customerInfo']['contactPerson']

    addressesSubmitterShortName= ET.SubElement(addressesSubmitter, "shortName")
    addressesSubmitterShortName.text = ""
    
    addressesSubmitterOrganization= ET.SubElement(addressesSubmitter, "organization")
    addressesSubmitterOrganization.text = ""

    addressesSubmitterStreet= ET.SubElement(addressesSubmitter, "street")
    addressesSubmitterStreet.text = data['customerInfo']['address']

    addressesSubmitterPostalCode= ET.SubElement(addressesSubmitter, "postalCode")
    addressesSubmitterPostalCode.text = ""

    addressesSubmitterCity= ET.SubElement(addressesSubmitter, "city")
    addressesSubmitterCity.text = ""

    addressesSubmitterRegion= ET.SubElement(addressesSubmitter, "region")
    addressesSubmitterRegion.text = ""

    addressesSubmitterState= ET.SubElement(addressesSubmitter, "state")
    addressesSubmitterState.text = ""

    addressesSubmitterTel1= ET.SubElement(addressesSubmitter, "tel1")
    addressesSubmitterTel1.text = data['customerInfo']['telNo']

    addressesSubmitterTel2= ET.SubElement(addressesSubmitter, "tel2")
    addressesSubmitterTel2.text = ""

    addressesSubmitterTelFax= ET.SubElement(addressesSubmitter, "telfax")
    addressesSubmitterTelFax.text = ""

    addressesSubmitterEmail= ET.SubElement(addressesSubmitter, "email")
    addressesSubmitterEmail.text = data['customerInfo']['email']

    addressesSubmitterProject = ET.SubElement(addressesSubmitter, "project")
    addressesSubmitterProject.text = ""

    addressesSubmitterProjectNumber = ET.SubElement(addressesSubmitter, "projectNumber")
    addressesSubmitterProjectNumber.text = ""

    addressesSubmitterCustom1 = ET.SubElement(addressesSubmitter, "custom1")
    addressesSubmitterCustom1.text = ""

    addressesSubmitterCustom2 = ET.SubElement(addressesSubmitter, "custom2")
    addressesSubmitterCustom2.text = ""
    
    addressesSubmitterCustom3 = ET.SubElement(addressesSubmitter, "custom2")
    addressesSubmitterCustom3.text = ""

    addressesSubmitter = ET.SubElement(addresses, "billing")

    addressesSubmitterName= ET.SubElement(addressesSubmitter, "name")
    addressesSubmitterName.text = data['billingInfo']['contactPerson']

    addressesSubmitterShortName= ET.SubElement(addressesSubmitter, "shortName")
    addressesSubmitterShortName.text = ""
    
    addressesSubmitterOrganization= ET.SubElement(addressesSubmitter, "organization")
    addressesSubmitterOrganization.text = ""

    addressesSubmitterStreet= ET.SubElement(addressesSubmitter, "street")
    addressesSubmitterStreet.text = data['billingInfo']['address']

    addressesSubmitterPostalCode= ET.SubElement(addressesSubmitter, "postalCode")
    addressesSubmitterPostalCode.text = ""

    addressesSubmitterCity= ET.SubElement(addressesSubmitter, "city")
    addressesSubmitterCity.text = ""

    addressesSubmitterRegion= ET.SubElement(addressesSubmitter, "region")
    addressesSubmitterRegion.text = ""

    addressesSubmitterState= ET.SubElement(addressesSubmitter, "state")
    addressesSubmitterState.text = ""

    addressesSubmitterTel1= ET.SubElement(addressesSubmitter, "tel1")
    addressesSubmitterTel1.text = data['billingInfo']['telNo']

    addressesSubmitterTel2= ET.SubElement(addressesSubmitter, "tel2")
    addressesSubmitterTel2.text = ""

    addressesSubmitterTelFax= ET.SubElement(addressesSubmitter, "telfax")
    addressesSubmitterTelFax.text = ""

    addressesSubmitterEmail= ET.SubElement(addressesSubmitter, "email")
    addressesSubmitterEmail.text = data['billingInfo']['email']

    addressesSubmitterProject = ET.SubElement(addressesSubmitter, "project")
    addressesSubmitterProject.text = ""

    addressesSubmitterProjectNumber = ET.SubElement(addressesSubmitter, "projectNumber")
    addressesSubmitterProjectNumber.text = ""

    addressesSubmitterCustom1 = ET.SubElement(addressesSubmitter, "custom1")
    addressesSubmitterCustom1.text = ""

    addressesSubmitterCustom2 = ET.SubElement(addressesSubmitter, "custom2")
    addressesSubmitterCustom2.text = ""
    
    addressesSubmitterCustom3 = ET.SubElement(addressesSubmitter, "custom2")
    addressesSubmitterCustom3.text = ""

    addressesSubmitter = ET.SubElement(addresses, "delivery")

    addressesSubmitterName= ET.SubElement(addressesSubmitter, "name")
    addressesSubmitterName.text = data['deliveryInfo']['contactPerson']

    addressesSubmitterShortName= ET.SubElement(addressesSubmitter, "shortName")
    addressesSubmitterShortName.text = ""
    
    addressesSubmitterOrganization= ET.SubElement(addressesSubmitter, "organization")
    addressesSubmitterOrganization.text = ""

    addressesSubmitterStreet= ET.SubElement(addressesSubmitter, "street")
    addressesSubmitterStreet.text = data['deliveryInfo']['address']

    addressesSubmitterPostalCode= ET.SubElement(addressesSubmitter, "postalCode")
    addressesSubmitterPostalCode.text = ""

    addressesSubmitterCity= ET.SubElement(addressesSubmitter, "city")
    addressesSubmitterCity.text = ""

    addressesSubmitterRegion= ET.SubElement(addressesSubmitter, "region")
    addressesSubmitterRegion.text = ""

    addressesSubmitterState= ET.SubElement(addressesSubmitter, "state")
    addressesSubmitterState.text = ""

    addressesSubmitterTel1= ET.SubElement(addressesSubmitter, "tel1")
    addressesSubmitterTel1.text = data['deliveryInfo']['telNo']

    addressesSubmitterTel2= ET.SubElement(addressesSubmitter, "tel2")
    addressesSubmitterTel2.text = ""

    addressesSubmitterTelFax= ET.SubElement(addressesSubmitter, "telfax")
    addressesSubmitterTelFax.text = ""

    addressesSubmitterEmail= ET.SubElement(addressesSubmitter, "email")
    addressesSubmitterEmail.text = data['deliveryInfo']['email']

    addressesSubmitterProject = ET.SubElement(addressesSubmitter, "project")
    addressesSubmitterProject.text = ""

    addressesSubmitterProjectNumber = ET.SubElement(addressesSubmitter, "projectNumber")
    addressesSubmitterProjectNumber.text = ""

    addressesSubmitterCustom1 = ET.SubElement(addressesSubmitter, "custom1")
    addressesSubmitterCustom1.text = ""

    addressesSubmitterCustom2 = ET.SubElement(addressesSubmitter, "custom2")
    addressesSubmitterCustom2.text = ""
    
    addressesSubmitterCustom3 = ET.SubElement(addressesSubmitter, "custom2")
    addressesSubmitterCustom3.text = ""

    

    order_Items = ET.SubElement(root, "orderItems")

    orderItem = ET.SubElement(order_Items, "orderItem")
    orderItemTitle = ET.SubElement(orderItem, "title")
    orderItemTitle.text = ""

    orderItemPrice = ET.SubElement(orderItem, "price")
    orderItemPriceCopy = ET.SubElement(orderItemPrice, "copy")
    orderItemPriceCopy.text = ""

    orderItemPriceAuxiliary = ET.SubElement(orderItemPrice, "auxiliary")
    orderItemPriceAuxiliary.text = ""

    orderItemPriceSum = ET.SubElement(orderItemPrice, "sum")
    orderItemPriceSum.text = ""

    orderItemPriceVAT = ET.SubElement(orderItemPrice, "vat")
    orderItemPriceSum.text = ""

    orderItemCopies = ET.SubElement(orderItem, "copies")
    orderItemCopies.text = data['orderInfo']['quantity']
    
    orderItemSubmitterNote = ET.SubElement(orderItem, "submitterNote")
    orderItemSubmitterNote.text = data['jobInfo']['prepressNotes']
    

    quantity = ET.SubElement(orderItem, "quatity")
    quantity.text = ""

    document = ET.SubElement(orderItem, "document")
    documentProd = ET.SubElement(document, "product")
    documentProd.text = ""

    documentName = ET.SubElement(documentProd, "name")
    documentName.text = data['orderInfo']['productName']

    documentDescription = ET.SubElement(documentProd, "description")
    documentDescription.text = ""

    documentPage = ET.SubElement(documentProd, "pageSize")

    documentPageSizeName = ET.SubElement(documentPage, "name")
    documentPageSizeName.text = ""

    documentPageSizeWidth = ET.SubElement(documentPage, "width")
    documentPageSizeWidth.text = ""

    documentPageSizeHeight= ET.SubElement(documentPage, "heighy")
    documentPageSizeWidth.text = ""

    documentServices = ET.SubElement(documentProd, "services")
    
    # Loop through all services in service_settings
    for service_id, settings in data['serviceSettings'].items():
        documentServicesId = ET.SubElement(documentServices, 'service')
        documentServicesId.set('id', service_id)

        documentServicesName = ET.SubElement(documentServicesId, "name")
        documentServicesId.text = ""
        
        documentServicesOption = ET.SubElement(documentServicesId, 'option')
        documentServicesOption.set('id', settings['optionId'])

        documentServicesOptionName = ET.SubElement(documentServicesOption, "name")
        documentServicesOptionName.text = settings['optionName']

    documentPrinter = ET.SubElement(documentProd, "printer")
    documentPrinterName = ET.SubElement(documentPrinter, "name")
    documentPrinterName.text = ""

    documentPrinterSettings = ET.SubElement(documentPrinter, "settings")
    documentPrinterSettings.text = ""

    documentAutoPrint = ET.SubElement(documentPrinter, "autoPrint")
    documentAutoPrint.text = ""

    documentCluster = ET.SubElement(documentProd, "cluster")
    documentClusterName = ET.SubElement(documentCluster, "name")
    documentClusterName.text = ""

    documentClusterAutoPrint = ET.SubElement(documentCluster, "autoPrint")
    documentClusterAutoPrint.text = ""

    documentClusterPrinters = ET.SubElement(documentCluster, "printers")
    documentClusterPrinter = ET.SubElement(documentClusterPrinters, "printer")

    documentClusterPrinterName = ET.SubElement(documentClusterPrinter, "name")
    documentClusterPrinterName.text = ""

    documentClusterPrinterSettings = ET.SubElement(documentClusterPrinters, "settings")
    documentClusterPrinterSettings.text = ""

    documentPageSources = ET.SubElement(document, "pageSources")
    documentPageSource = ET.SubElement(documentPageSources, "pageSource")

    documentPageSourceFileName = ET.SubElement(documentPageSource, "fileName")
 
    documentPageOriginalFileName = ET.SubElement(documentPageSource, "originalFileName")
    if isinstance(data['filesInfo']['uploadedFiles'], list):
        # documentPageOriginalFileName.text = ", ".join(str(file).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;') 
        #                                             for file in data['filesInfo']['uploadedFiles'])
        documentPageOriginalFileName.text = data['jobInfo']['name']
        documentPageSourceFileName.text = ", ".join(str(file).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;') 
                                                    for file in data['filesInfo']['uploadedFiles'])
    else:
        documentPageOriginalFileName.text = data['jobInfo']['name']
        # documentPageOriginalFileName.text = str(data['filesInfo']['uploadedFiles']).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        documentPageSourceFileName.text = str(data['filesInfo']['uploadedFiles']).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    documentPagekeepFile = ET.SubElement(documentPageSource, "keepFile")
    documentPagekeepFile.text = "true"

    documentPagetotalPageCount = ET.SubElement(documentPageSource, "totalPageCount")
    documentPagetotalPageCount.text = ""



    # Create XML tree and save
    tree = ET.ElementTree(root)
    tree.write(filename, encoding="utf-8", xml_declaration=True)

# Add these debug routes
@app.route('/check-image')
def check_image():
    image_path = os.path.join(app.static_folder, 'images', 'Konica_Minolta_logo.png')
    return {
        'exists': os.path.exists(image_path),
        'absolute_path': os.path.abspath(image_path),
        'static_folder': app.static_folder,
        'listdir': os.listdir(os.path.join(app.static_folder, 'images')) if os.path.exists(os.path.join(app.static_folder, 'images')) else []
    }

# Add a direct serve route for testing
@app.route('/direct-image')
def direct_image():
    return send_from_directory(
        os.path.join(app.static_folder, 'images'),
        'Konica_Minolta_logo.png'
    )

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if session['username'] != 'admin':
        flash('Access denied. Admin privileges required.')
        return redirect(url_for('welcome'))

    todos = db.form.find()
    print(todos)
    print("test")

    # Get total orders from form collection
    total_orders = db.form.count_documents({})  # Changed from csr to form

    # Get orders from this month
    current_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_orders = db.form.count_documents({})  # We'll need to add timestamp field to track this

    # Get active orders (assuming all orders are active for now)
    active_orders = db.form.count_documents({})

    # Get product type distribution
    pipeline = [
        {
            '$group': {
                '_id': '$orderInfo.productName',  # Changed to match your document structure
                'count': {'$sum': 1}
            }
        }
    ]
    product_stats = list(db.form.aggregate(pipeline))
    
    product_types = [stat['_id'] for stat in product_stats if stat['_id']]  # Filter out None values
    product_counts = [stat['count'] for stat in product_stats if stat['_id']]

    return render_template('dashboard.html',
                         total_orders=total_orders,
                         monthly_orders=monthly_orders,
                         active_orders=active_orders,
                         product_types=product_types,
                         product_counts=product_counts)
@app.route('/export-csv')
def export_csv():
    if 'username' not in session or session['username'] != 'admin':
        flash('Access denied. Admin privileges required.')
        return redirect(url_for('welcome'))

    # Get date range from query parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    selected_company = request.args.get('company')

    
    # Base query
    query = {}
    
     # Add date filter if dates are provided
    if start_date and end_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            query['orderInfo.deliveryDate'] = {
                '$gte': start.strftime('%Y-%m-%d'),
                '$lte': end.strftime('%Y-%m-%d')
            }
        except ValueError:
            flash('Invalid date format')
    elif start_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            query['orderInfo.deliveryDate'] = {
                '$gte': start.strftime('%Y-%m-%d'),
            }
        except ValueError:
            flash('Invalid date format')
    elif end_date:
        try:
            end = datetime.strptime(end_date, '%Y-%m-%d')
            query['orderInfo.deliveryDate'] = {
                '$lte': end.strftime('%Y-%m-%d')
            }
        except ValueError:
            flash('Invalid date format')

    if selected_company:
        users_with_company = list(db.users.find(
            {'company': selected_company}, 
            {'_id': 1, 'username': 1}
        ))
        user_ids = [str(user['username']) for user in users_with_company]
        query['customerInfo.contactPerson'] = {'$in': user_ids}
    

    print(selected_company)
    # Get all filtered orders (no pagination for export)
    orders = list(db.form.find(query).sort('orderInfo.deliveryDate', -1))

    # print(orders)

    # Create CSV in memory
    si = io.StringIO()
    cw = csv.writer(si)
    
    # Write headers
    headers = [
        'Order ID',
        'Delivery Date',
        'Product Name',
        'Job Name',
        'Contact Person',
        'Email',
        'Tel No',
        'Address',
        'Quantity',
        'Notes'
    ]
    cw.writerow(headers)
    
    # Write data
    for order in orders:
        row = [
            order.get('orderInfo', {}).get('orderId', ''),
            order.get('orderInfo', {}).get('deliveryDate', ''),
            order.get('orderInfo', {}).get('productName', ''),
            order.get('jobInfo', {}).get('name', ''),
            order.get('customerInfo', {}).get('contactPerson', ''),
            order.get('customerInfo', {}).get('email', ''),
            order.get('customerInfo', {}).get('telNo', ''),
            order.get('customerInfo', {}).get('address', ''),
            order.get('orderInfo', {}).get('quantity', ''),
            order.get('jobInfo', {}).get('notes', '')
        ]
        cw.writerow(row)
    
    output = si.getvalue()
    si.close()
    
    # Generate filename with date range
    if start_date and end_date:
        filename = f'orders_{start_date}_to_{end_date}.csv'
    else:
        filename = f'orders_all.csv'

    return send_file(
        io.BytesIO(output.encode('utf-8-sig')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )

@app.route('/customers')
def customers():
    if 'username' not in session:
        return redirect(url_for('login'))
        
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('search', '')
    per_page = ITEMS_PER_PAGE  # Number of customers per page
    
    # Base query
    query = {}
    
    # Add search filter if search query exists
    if search_query:
        # Search in multiple fields using case-insensitive regex
        query['$or'] = [
            {'username': {'$regex': search_query, '$options': 'i'}},
            {'email': {'$regex': search_query, '$options': 'i'}},
            {'company': {'$regex': search_query, '$options': 'i'}},
            {'contact_person': {'$regex': search_query, '$options': 'i'}},
            {'phone': {'$regex': search_query, '$options': 'i'}}
        ]
    
    # Get total count for pagination
    total_customers = db.users.count_documents(query)
    
    # Get paginated and filtered customers
    customers = list(db.users.find(query)
                    .skip((page - 1) * per_page)
                    .limit(per_page))
    
    total_pages = (total_customers + per_page - 1) // per_page
    
    return render_template('customers.html', 
                         customers=customers,
                         page=page,
                         total_pages=total_pages,
                         search_query=search_query)


@app.route('/export-customers-csv')
def export_customers_csv():
    if 'username' not in session:
        return redirect(url_for('login'))

    # Get search query if exists
    search_query = request.args.get('search', '')
    
    # Base query
    query = {}
    
    # Add search filter if search query exists
    if search_query:
        query['$or'] = [
            {'username': {'$regex': search_query, '$options': 'i'}},
            {'email': {'$regex': search_query, '$options': 'i'}},
            {'company': {'$regex': search_query, '$options': 'i'}},
            {'contact_person': {'$regex': search_query, '$options': 'i'}},
            {'phone': {'$regex': search_query, '$options': 'i'}}
        ]

    # Get all matching customers
    customers = list(db.users.find(query))

    # Create CSV in memory
    si = io.StringIO()
    cw = csv.writer(si)
    
    # Write headers
    cw.writerow([
        'Username',
        'Email',
        'Company',
        'Contact Person',
        'Phone',
        'Status'
    ])
    
    # Write data
    for customer in customers:
        cw.writerow([
            customer.get('username', ''),
            customer.get('email', ''),
            customer.get('company', ''),
            customer.get('contact_person', ''),
            customer.get('phone', ''),
            customer.get('status', 'Active')
        ])
    
    output = si.getvalue()
    si.close()
    
    # Generate filename
    if search_query:
        filename = f'customers_search_{search_query}.csv'
    else:
        filename = 'customers_all.csv'

    return send_file(
        io.BytesIO(output.encode('utf-8-sig')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )

@app.route('/management')
def management():
    
    if 'username' not in session:
        return redirect(url_for('login'))


    # Pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = ITEMS_PER_PAGE
    skip = (page - 1) * per_page
    
    # Get username
    username = session.get('username')

    # Get date range from query parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    if username == 'admin':
        query = {}
    else:
        query = {"customerInfo.contactPerson": username}
    
    # Add date filter if dates are provided
    if start_date and end_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            query['orderInfo.deliveryDate'] = {
                '$gte': start.strftime('%Y-%m-%d'),
                '$lte': end.strftime('%Y-%m-%d')
            }
        except ValueError:
            flash('Invalid date format')
    # Get paginated orders
    page = request.args.get('page', 1, type=int)
    per_page = ITEMS_PER_PAGE
    skip = (page - 1) * per_page
    
    total_orders = db.form.count_documents(query)
    total_pages = ceil(total_orders / per_page)
    
    orders = list(db.form.find(query)
                 .sort('_id', -1)
                 .skip(skip)
                 .limit(per_page))

    return render_template('management.html', 
                         username=username,
                         orders=orders,
                         page=page,
                         total_pages=total_pages,
                         start_date=start_date,
                         end_date=end_date)


@app.route('/csrform-step1', methods=['GET', 'POST'])
def csrform_step1():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session.get('username', '')
    email = ''

    
    # If user is logged in, get their email from the database
    if username:
        user = db.users.find_one({'username': username})
        if user:
            email = user.get('email', '')
            
    
      # Check if this is a repeat order
    order_id = request.args.get('order_id')
    past_order = {}

    if order_id:
        print(order_id)
        try:
            past_order = db.form.find_one({'_id': ObjectId(order_id)})
            print(past_order)
        except Exception as e:
            print(f"Error fetching past order: {e}")
            past_order = {}

    today_date = date.today().strftime('%Y-%m-%d')
    print('reached here')
    print(request.method )


    if request.method == 'POST':
        # Store step 1 data in session
        session['form_data_step1'] = {
            'customerInfo': {
                'contactPerson': request.form.get('contactPerson'),
                'address': request.form.get('address'),
                'email': request.form.get('email'),
                'telNo': request.form.get('telNo')
            },
            'billingInfo': {
                'contactPerson': request.form.get('billingContactPerson'),
                'address': request.form.get('billingAddress'),
                'email': request.form.get('billingEmail'),
                'telNo': request.form.get('billingTelNo')
            },
            'deliveryInfo': {
                'contactPerson': request.form.get('deliveryContactPerson'),
                'address': request.form.get('deliveryAddress'),
                'email': request.form.get('deliveryEmail'),
                'telNo': request.form.get('deliveryTelNo')
            }
        }
        if order_id:
            return redirect(url_for('csrform', order_id=order_id)) #include order id in get req
        else:
            return redirect(url_for('csrform'))

    # Pre-fill form if coming back from step 2
    form_data = session.get('form_data_step1', {})
    
    # Clear session if starting fresh
    if request.args.get('clear'):
        session.pop('form_data_step1', None)
        form_data = {}

    return render_template('csrform1.html', today_date=today_date, username=username, email=email, past_order = past_order, form_data=form_data, user = user)

@app.route('/csrform-step2', methods=['GET', 'POST'])
def csrform_step2():
    if 'username' not in session:
        return redirect(url_for('login'))

    # Ensure step 1 is completed
    if 'form_data_step1' not in session:
        flash('Please fill in the customer information first.')
        return redirect(url_for('csrform_step1'))

    if request.method == 'POST':
        try:
            # Generate new order ID
            order_id = get_next_sequence('order_id')

            # Combine data from both steps
            form_data = {
                **session['form_data_step1'],
                'orderInfo': {
                    'orderId': order_id,
                    'productName': request.form.get('productName'),
                    'deliveryDate': request.form.get('deliveryDate'),
                    'quantity': request.form.get('quantity')
                },
                'jobInfo': {
                    'name': request.form.get('jobName'),
                    'id': request.form.get('jobId'),
                    'productType': request.form.get('productType'),
                    'numberOfPages': request.form.get('numberOfPages'),
                    'notes': request.form.get('notes')
                },
                'serviceSettings': {
                    'COLORPRINT': {'optionId': request.form.get('COLORPRINT')},
                    'DUPLEX': {'optionId': request.form.get('DUPLEX')},
                    'BINDINGPOSITION': {'optionId': request.form.get('BINDINGPOSITION')},
                    'PAGEFITTING': {'optionId': request.form.get('PAGEFITTING')},
                    'PAPERTYPE': {'optionId': request.form.get('PAPERTYPE')},
                    'PUNCH': {'optionId': request.form.get('PUNCH')},
                    'STAPLE': {'optionId': request.form.get('STAPLE')},
                    'FOLD': {'optionId': request.form.get('FOLD')}
                },
                'status': 'Pending',
                'createdBy': session['username'],
                'createdAt': datetime.utcnow()
            }

            # Save to database
            db.form.insert_one(form_data)
            
            # Clear session data
            session.pop('form_data_step1', None)
            
            flash('Order submitted successfully!')
            return redirect(url_for('welcome'))

        except Exception as e:
            flash(f'Error submitting form: {str(e)}')
            return render_template('csrform_step2.html')

    return render_template('csrform2new.html')

@app.route('/reports')
def reports():
       
    # Get unique companies from the database
    companies = users_collection.distinct('company')
    
    # Sort companies alphabetically
    companies = sorted(companies)

    print(companies)
    
    # Remove None or empty values if they exist
    companies = [company for company in companies if company]
    
    return render_template('reports.html', companies=companies)
    


@app.route('/quarterly-volume')
def quarterly_volume():
    # Get current quarter dates
    today = datetime.now()
    
    # Calculate the start of each month in the quarter
    month3_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month2_start = (month3_start - timedelta(days=1)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month1_start = (month2_start - timedelta(days=1)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Debug prints
    print("Date ranges:")
    print(f"Month 1: {month1_start.strftime('%Y-%m-%d')} to {month2_start.strftime('%Y-%m-%d')}")
    print(f"Month 2: {month2_start.strftime('%Y-%m-%d')} to {month3_start.strftime('%Y-%m-%d')}")
    print(f"Month 3: {month3_start.strftime('%Y-%m-%d')} to {today.strftime('%Y-%m-%d')}")

    def get_monthly_quantity(start_date, end_date):
        try:
            pipeline = [
                {
                    '$match': {
                        'orderInfo.deliveryDate': {
                            '$gte': start_date.strftime('%Y-%m-%d'),
                            '$lt': end_date.strftime('%Y-%m-%d')
                        }
                    }
                },
                {
                    '$addFields': {
                        'convertedQuantity': {
                            '$convert': {
                                'input': '$orderInfo.quantity',
                                'to': 'int',
                                'onError': 0,
                                'onNull': 0
                            }
                        }
                    }
                },
                {
                    '$group': {
                        '_id': None,
                        'total': {'$sum': '$convertedQuantity'}
                    }
                }
            ]
            
            result = list(db.form.aggregate(pipeline))
            return result[0]['total'] if result else 0
        except Exception as e:
            print(f"Error calculating quantity: {e}")
            return 0

    # Get quantities for each month
    month1_quantity = get_monthly_quantity(month1_start, month2_start)
    month2_quantity = get_monthly_quantity(month2_start, month3_start)
    month3_quantity = get_monthly_quantity(month3_start, today)

    # Debug prints
    print("Quantities:")
    print(f"Month 1: {month1_quantity}")
    print(f"Month 2: {month2_quantity}")
    print(f"Month 3: {month3_quantity}")
    
    # Create labels for months
    month_labels = [
        month1_start.strftime('%B'),
        month2_start.strftime('%B'),
        month3_start.strftime('%B')
    ]
    
    data = {
        'labels': month_labels,
        'datasets': [{
            'label': 'Total Print Quantity',
            'data': [month1_quantity, month2_quantity, month3_quantity],
            'borderColor': '#1a4d6d',
            'backgroundColor': 'rgba(26, 77, 109, 0.2)',
            'tension': 0.1,
            'fill': True
        }]
    }
    
    return jsonify(data)

@app.route('/monthly-volume')
def monthly_volume():
    # Get current date and calculate dates for the last 12 months
    today = datetime.now()
    
    # Calculate the start of each month for the past 12 months
    months = []
    month_starts = []
    
    for i in range(12):
        month_date = today.replace(day=1) - relativedelta(months=i)
        months.append(month_date)
        month_starts.append(month_date.strftime('%Y-%m-%d'))
    
    # Add one more date for the end of the range
    next_month = months[0] + relativedelta(months=1)
    month_starts.insert(0, next_month.strftime('%Y-%m-%d'))
    
    # Debug prints
    print("Month ranges:")
    for i in range(12):
        print(f"Month {i+1}: {month_starts[i+1]} to {month_starts[i]}")

    def get_monthly_quantity(start_date, end_date):
        try:
            pipeline = [
                {
                    '$match': {
                        'orderInfo.deliveryDate': {
                            '$gte': start_date,
                            '$lt': end_date
                        }
                    }
                },
                {
                    '$addFields': {
                        'convertedQuantity': {
                            '$convert': {
                                'input': '$orderInfo.quantity',
                                'to': 'int',
                                'onError': 0,
                                'onNull': 0
                            }
                        }
                    }
                },
                {
                    '$group': {
                        '_id': None,
                        'total': {'$sum': '$convertedQuantity'}
                    }
                }
            ]
            
            result = list(db.form.aggregate(pipeline))
            return result[0]['total'] if result else 0
        except Exception as e:
            print(f"Error calculating quantity: {e}")
            return 0

    # Query MongoDB for quantities in each month
    monthly_quantities = []
    for i in range(12):
        quantity = get_monthly_quantity(month_starts[i+1], month_starts[i])
        monthly_quantities.append(quantity)
    
    # Create labels for months (in reverse order to show oldest to newest)
    month_labels = [month.strftime('%B %Y') for month in reversed(months)]
    
    data = {
        'labels': month_labels,
        'datasets': [{
            'label': 'Total Print Quantity',
            'data': list(reversed(monthly_quantities)),  # Reverse to match labels
            'borderColor': '#1a4d6d',
            'backgroundColor': 'rgba(26, 77, 109, 0.2)',
            'tension': 0.1,
            'fill': True
        }]
    }
    
    return jsonify(data)

@app.route('/substrate-consumption')
def substrate_consumption():
    # Query all orders
     # Aggregate substrate usage from MongoDB
    pipeline = [
        {
            '$group': {
                '_id': '$prodDetails.substrate',
                'count': {'$sum': 1}
            }
        }
    ]
    
    substrate_data = list(db.form.aggregate(pipeline))
    
    # Prepare data for chart
    labels = [item['_id'] for item in substrate_data if item['_id']]  # Filter out None values
    counts = [item['count'] for item in substrate_data if item['_id']]
    
    data = {
        'labels': labels,
        'datasets': [{
            'data': counts,
            'backgroundColor': ['#1a4d6d', '#2c7da0', '#468faf', '#61a5c2', '#89c2d9']
        }]
    }
    
    return jsonify(data)

@app.route('/weekly-volume')
def weekly_volume():
    # Get current date and calculate dates for the last 4 weeks
    today = datetime.now()
    
    # Calculate the start of each week
    week4_start = today.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=today.weekday())
    week3_start = week4_start - timedelta(days=7)
    week2_start = week3_start - timedelta(days=7)
    week1_start = week2_start - timedelta(days=7)
    
    # Debug prints
    print("Week ranges:")
    print(f"Week 1: {week1_start.strftime('%Y-%m-%d')} to {week2_start.strftime('%Y-%m-%d')}")
    print(f"Week 2: {week2_start.strftime('%Y-%m-%d')} to {week3_start.strftime('%Y-%m-%d')}")
    print(f"Week 3: {week3_start.strftime('%Y-%m-%d')} to {week4_start.strftime('%Y-%m-%d')}")
    print(f"Week 4: {week4_start.strftime('%Y-%m-%d')} to {today.strftime('%Y-%m-%d')}")

    def get_weekly_quantity(start_date, end_date):
        try:
            pipeline = [
                {
                    '$match': {
                        'orderInfo.deliveryDate': {
                            '$gte': start_date.strftime('%Y-%m-%d'),
                            '$lt': end_date.strftime('%Y-%m-%d')
                        }
                    }
                },
                {
                    '$addFields': {
                        'convertedQuantity': {
                            '$convert': {
                                'input': '$orderInfo.quantity',
                                'to': 'int',
                                'onError': 0,
                                'onNull': 0
                            }
                        }
                    }
                },
                {
                    '$group': {
                        '_id': None,
                        'total': {'$sum': '$convertedQuantity'}
                    }
                }
            ]
            
            result = list(db.form.aggregate(pipeline))
            return result[0]['total'] if result else 0
        except Exception as e:
            print(f"Error calculating quantity: {e}")
            return 0

    # Get quantities for each week
    week1_quantity = get_weekly_quantity(week1_start, week2_start)
    week2_quantity = get_weekly_quantity(week2_start, week3_start)
    week3_quantity = get_weekly_quantity(week3_start, week4_start)
    week4_quantity = get_weekly_quantity(week4_start, today)

    # Create labels for weeks
    week_labels = [
        f"Week {week1_start.strftime('%d %b')} - {(week2_start - timedelta(days=1)).strftime('%d %b')}",
        f"Week {week2_start.strftime('%d %b')} - {(week3_start - timedelta(days=1)).strftime('%d %b')}",
        f"Week {week3_start.strftime('%d %b')} - {(week4_start - timedelta(days=1)).strftime('%d %b')}",
        f"Week {week4_start.strftime('%d %b')} - {today.strftime('%d %b')}"
    ]
    
    data = {
        'labels': week_labels,
        'datasets': [{
            'label': 'Total Print Quantity',
            'data': [week1_quantity, week2_quantity, week3_quantity, week4_quantity],
            'borderColor': '#1a4d6d',
            'backgroundColor': 'rgba(26, 77, 109, 0.2)',
            'tension': 0.1,
            'fill': True
        }]
    }
    
    return jsonify(data)

@app.route('/yearly-volume')
def yearly_volume():
    # Get current date and calculate dates for the last 5 years
    today = datetime.now()
    
    # Calculate the start of each year for the past 5 years
    years = []
    year_starts = []
    
    for i in range(5):
        year_date = today.replace(month=1, day=1) - relativedelta(years=i)
        years.append(year_date)
        year_starts.append(year_date.strftime('%Y-%m-%d'))
    
    # Add one more date for the end of the range
    next_year = years[0].replace(year=years[0].year + 1)
    year_starts.insert(0, next_year.strftime('%Y-%m-%d'))
    
    # Debug prints
    print("Year ranges:")
    for i in range(5):
        print(f"Year {i+1}: {year_starts[i+1]} to {year_starts[i]}")

    def get_yearly_quantity(start_date, end_date):
        try:
            pipeline = [
                {
                    '$match': {
                        'orderInfo.deliveryDate': {
                            '$gte': start_date,
                            '$lt': end_date
                        }
                    }
                },
                {
                    '$addFields': {
                        'convertedQuantity': {
                            '$convert': {
                                'input': '$orderInfo.quantity',
                                'to': 'int',
                                'onError': 0,
                                'onNull': 0
                            }
                        }
                    }
                },
                {
                    '$group': {
                        '_id': None,
                        'total': {'$sum': '$convertedQuantity'}
                    }
                }
            ]
            
            result = list(db.form.aggregate(pipeline))
            return result[0]['total'] if result else 0
        except Exception as e:
            print(f"Error calculating quantity: {e}")
            return 0

    # Query MongoDB for quantities in each year
    yearly_quantities = []
    for i in range(5):
        quantity = get_yearly_quantity(year_starts[i+1], year_starts[i])
        yearly_quantities.append(quantity)
    
    # Create labels for years (in reverse order to show oldest to newest)
    year_labels = [year.strftime('%Y') for year in reversed(years)]
    
    data = {
        'labels': year_labels,
        'datasets': [{
            'label': 'Total Print Quantity',
            'data': list(reversed(yearly_quantities)),  # Reverse to match labels
            'borderColor': '#1a4d6d',
            'backgroundColor': 'rgba(26, 77, 109, 0.2)',
            'tension': 0.1,
            'fill': True
        }]
    }
    
    return jsonify(data)

@app.route('/cancelled-jobs')
def cancelled_jobs():
    # Get current date and calculate dates for the last 4 weeks
    today = datetime.now()
    
    # Calculate the start of each week
    week4_start = today.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=today.weekday())
    week3_start = week4_start - timedelta(days=7)
    week2_start = week3_start - timedelta(days=7)
    week1_start = week2_start - timedelta(days=7)
    
    # Debug prints
    print("Week ranges:")
    print(f"Week 1: {week1_start.strftime('%Y-%m-%d')} to {week2_start.strftime('%Y-%m-%d')}")
    print(f"Week 2: {week2_start.strftime('%Y-%m-%d')} to {week3_start.strftime('%Y-%m-%d')}")
    print(f"Week 3: {week3_start.strftime('%Y-%m-%d')} to {week4_start.strftime('%Y-%m-%d')}")
    print(f"Week 4: {week4_start.strftime('%Y-%m-%d')} to {today.strftime('%Y-%m-%d')}")

    # Query MongoDB for both cancelled and completed orders in each week
    weeks_data = []
    week_starts = [week1_start, week2_start, week3_start, week4_start]
    week_ends = [week2_start, week3_start, week4_start, today]

    for start, end in zip(week_starts, week_ends):
        cancelled = db.form.count_documents({
            'orderInfo.deliveryDate': {
                '$gte': start.strftime('%Y-%m-%d'),
                '$lt': end.strftime('%Y-%m-%d')
            },
            'status': 'Cancelled'
        })
        
        completed = db.form.count_documents({
            'orderInfo.deliveryDate': {
                '$gte': start.strftime('%Y-%m-%d'),
                '$lt': end.strftime('%Y-%m-%d')
            },
            'status': 'Completed'
        })
        
        weeks_data.append({
            'cancelled': cancelled,
            'completed': completed
        })

    # Create labels for weeks
    week_labels = [
        f"Week {week1_start.strftime('%d %b')} - {(week2_start - timedelta(days=1)).strftime('%d %b')}",
        f"Week {week2_start.strftime('%d %b')} - {(week3_start - timedelta(days=1)).strftime('%d %b')}",
        f"Week {week3_start.strftime('%d %b')} - {(week4_start - timedelta(days=1)).strftime('%d %b')}",
        f"Week {week4_start.strftime('%d %b')} - {today.strftime('%d %b')}"
    ]
    
    data = {
        'labels': week_labels,
        'datasets': [
            {
                'label': 'Completed Orders',
                'data': [week['completed'] for week in weeks_data],
                'backgroundColor': '#28a745',  # Green for completed
                'borderColor': '#28a745',
                'borderWidth': 1
            },
            {
                'label': 'Cancelled Orders',
                'data': [week['cancelled'] for week in weeks_data],
                'backgroundColor': '#dc3545',  # Red for cancelled
                'borderColor': '#dc3545',
                'borderWidth': 1
            }
        ]
    }
    
    return jsonify(data)

@app.route('/digital-vs-offset')
def digital_vs_offset():
    # Get current date and calculate dates for the last 4 weeks
    today = datetime.now()
    
    # Calculate the start of each week
    week4_start = today.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=today.weekday())
    week3_start = week4_start - timedelta(days=7)
    week2_start = week3_start - timedelta(days=7)
    week1_start = week2_start - timedelta(days=7)
    
    # Debug prints
    print("Week ranges:")
    print(f"Week 1: {week1_start.strftime('%Y-%m-%d')} to {week2_start.strftime('%Y-%m-%d')}")
    print(f"Week 2: {week2_start.strftime('%Y-%m-%d')} to {week3_start.strftime('%Y-%m-%d')}")
    print(f"Week 3: {week3_start.strftime('%Y-%m-%d')} to {week4_start.strftime('%Y-%m-%d')}")
    print(f"Week 4: {week4_start.strftime('%Y-%m-%d')} to {today.strftime('%Y-%m-%d')}")

    weeks_data = []
    week_starts = [week1_start, week2_start, week3_start, week4_start]
    week_ends = [week2_start, week3_start, week4_start, today]

    digital_data = []
    digital2_data = []
    offset_data = []

    for start, end in zip(week_starts, week_ends):
        # Count digital jobs
        digital = db.form.count_documents({
            'orderInfo.deliveryDate': {
                '$gte': start.strftime('%Y-%m-%d'),
                '$lt': end.strftime('%Y-%m-%d')
            },
            'orderInfo.outputType': 'Digital - C4070'
        })
        digital_data.append(digital)

        digital2 = db.form.count_documents({
            'orderInfo.deliveryDate': {
                '$gte': start.strftime('%Y-%m-%d'),
                '$lt': end.strftime('%Y-%m-%d')
            },
            'orderInfo.outputType': 'Digital - C1400'
        })
        digital2_data.append(digital2)
        
        # Count offset jobs
        offset = db.form.count_documents({
            'orderInfo.deliveryDate': {
                '$gte': start.strftime('%Y-%m-%d'),
                '$lt': end.strftime('%Y-%m-%d')
            },
            'outputInfo.outputType': 'Offset - SM74'
        })
        offset_data.append(offset)

    # Create labels for weeks
    week_labels = [
        f"Week {week1_start.strftime('%d %b')} - {(week2_start - timedelta(days=1)).strftime('%d %b')}",
        f"Week {week2_start.strftime('%d %b')} - {(week3_start - timedelta(days=1)).strftime('%d %b')}",
        f"Week {week3_start.strftime('%d %b')} - {(week4_start - timedelta(days=1)).strftime('%d %b')}",
        f"Week {week4_start.strftime('%d %b')} - {today.strftime('%d %b')}"
    ]
    
    data = {
        'labels': week_labels,
        'datasets': [
            {
                'label': 'Digital - C4070',
                'data': digital_data,
                'borderColor': '#1a4d6d',
                'backgroundColor': 'rgba(26, 77, 109, 0.2)',
                'tension': 0.1,
                'fill': True
            },
            {
                'label': 'Offset - SM74',
                'data': offset_data,
                'borderColor': '#28a745',
                'backgroundColor': 'rgba(40, 167, 69, 0.2)',
                'tension': 0.1,
                'fill': True
            },
            {
                'label': 'Digital - C1400',
                'data': digital2_data,
                'borderColor': '#dc3545',  # Dark red (Bootstrap's danger color)
                'backgroundColor': 'rgba(220, 53, 69, 0.2)',  # Lighter red with opacity
                'tension': 0.1,
                'fill': True
            },

        ]
    }
    
    return jsonify(data)

@app.route('/custom-report', methods=['POST'])
def custom_report():
    data = request.get_json()
    date_start = datetime.strptime(data['dateStart'], '%Y-%m-%d')
    date_end = datetime.strptime(data['dateEnd'], '%Y-%m-%d')
    company = data['company']
    interval = data['interval']

    # Initialize lists for dates and order counts
    labels = []
    order_counts = []

    users_with_company = list(db.users.find(
        {'company': company}, 
    ))
    user_ids = [str(user['username']) for user in users_with_company]
    print(user_ids)

    if interval == 'daily':
        # Generate daily data points
        current_date = date_start
        while current_date <= date_end:
            next_date = current_date + timedelta(days=1)
            count = db.form.count_documents({
                'orderInfo.deliveryDate': {
                    '$gte': current_date.strftime('%Y-%m-%d'),
                    '$lt': next_date.strftime('%Y-%m-%d')
                },
                'customerInfo.contactPerson': {'$in': user_ids}  # Check against list of user IDs
                # 'orderInfo.company': company
            })
            labels.append(current_date.strftime('%Y-%m-%d'))
            order_counts.append(count)
            current_date = next_date

    elif interval == 'weekly':
        # Generate weekly data points
        current_date = date_start
        while current_date <= date_end:
            next_date = current_date + timedelta(days=7)
            count = db.form.count_documents({
                'orderInfo.deliveryDate': {
                    '$gte': current_date.strftime('%Y-%m-%d'),
                    '$lt': next_date.strftime('%Y-%m-%d')
                },
                'orderInfo.company': company
            })
            labels.append(f"Week {current_date.strftime('%d %b')} - {(next_date - timedelta(days=1)).strftime('%d %b')}")
            order_counts.append(count)
            current_date = next_date

    elif interval == 'monthly':
        # Generate monthly data points
        current_date = date_start.replace(day=1)
        while current_date <= date_end:
            if current_date.month == 12:
                next_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                next_date = current_date.replace(month=current_date.month + 1)
            
            count = db.form.count_documents({
                'orderInfo.deliveryDate': {
                    '$gte': current_date.strftime('%Y-%m-%d'),
                    '$lt': next_date.strftime('%Y-%m-%d')
                },
                'orderInfo.company': company
            })
            labels.append(current_date.strftime('%B %Y'))
            order_counts.append(count)
            current_date = next_date

    # Prepare the response data
    data = {
        'labels': labels,
        'datasets': [{
            'label': 'Number of Orders',
            'data': order_counts,
            'borderColor': '#1a4d6d',
            'backgroundColor': 'rgba(26, 77, 109, 0.2)',
            'tension': 0.1,
            'fill': True
        }]
    }

    return jsonify(data)



# Optional: Add a cancel endpoint to clear session data
@app.route('/csrform-cancel')
def csrform_cancel():
    session.pop('form_data_step1', None)
    return redirect(url_for('welcome'))

@app.route('/customer/<username>', methods=['GET', 'POST'])
def customer_details(username):
    if 'username' not in session or (session['username'] != 'admin' and session['username'] != username):
        flash('Unauthorized access', 'error')
        return redirect(url_for('login'))
    
    user = users_collection.find_one({'username': username})
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('welcome'))
    
    if request.method == 'POST':
        if 'delete' in request.form:
            # Handle delete
            users_collection.delete_one({'username': username})
            flash('User deleted successfully', 'success')
            return redirect(url_for('welcome'))
        
        # Handle update
        try:
            updates = {
                'email': request.form['email'],
                'company': request.form['company'],
                'telNo': request.form['telNo'],
                'address': request.form['address']
            }
            print(updates)
            # Only update password if a new one is provided
            if request.form['password']:
                updates['password'] = generate_password_hash(request.form['password'])
            
            users_collection.update_one(
                {'username': username},
                {'$set': updates}
            )
            flash('User details updated successfully', 'success')
            return redirect(url_for('customer_details', username=username))
            
        except Exception as e:
            flash('Error updating user details', 'error')
            print(f"Error updating user: {e}")
    
    return render_template('customer/update_customer.html', user=user, activeUser = session['username'])

@app.route('/download_pdf/<order_id>')
def download_pdf(order_id):
    order = db.form.find_one({'orderInfo.orderId': order_id})
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    
    def draw_table(data, x, y, col_widths, row_height=20, header=False):
        for row_idx, row in enumerate(data):
            current_x = x
            for col_idx, (cell, width) in enumerate(zip(row, col_widths)):
                if header and row_idx == 0:
                    p.setFillColor(colors.HexColor('#005aab'))
                    p.rect(current_x, y - row_height, width, row_height, fill=1)
                    p.setFillColor(colors.white)
                else:
                    p.setFillColor(colors.black)
                    if row_idx % 2 == 1:
                        p.setFillColor(colors.HexColor('#f5f5f5'))
                        p.rect(current_x, y - row_height, width, row_height, fill=1)
                        p.setFillColor(colors.black)
                
                p.setStrokeColor(colors.HexColor('#e0e0e0'))
                p.rect(current_x, y - row_height, width, row_height)
                
                if header and row_idx == 0:
                    p.setFont("Helvetica-Bold", 9)
                else:
                    p.setFont("Helvetica", 7)
                text_y = y - row_height + 8
                p.drawString(current_x + 5, text_y, str(cell))
                
                current_x += width
            y -= row_height
        return y
    
    def draw_table2(data, x, y, col_widths, row_height=20, header=False):
        for row_idx, row in enumerate(data):
            current_x = x
            for col_idx, (cell, width) in enumerate(zip(row, col_widths)):
                if header and row_idx == 0:
                    pass
                else:
                    p.setFillColor(colors.black)
                    if row_idx % 2 == 1:
                        p.setFillColor(colors.HexColor('#f5f5f5'))
                        p.rect(current_x, y - row_height, width, row_height, fill=1)
                        p.setFillColor(colors.black)
                
                p.setStrokeColor(colors.HexColor('#e0e0e0'))
                p.rect(current_x, y - row_height, width, row_height)
                
                if header and row_idx == 0:
                    p.setFont("Helvetica-Bold", 9)
                else:
                    p.setFont("Helvetica", 7)
                text_y = y - row_height + 8
                p.drawString(current_x + 5, text_y, str(cell))
                
                current_x += width
            y -= row_height
        return y

    # Constants for margins and positioning
    LEFT_MARGIN = 40
    RIGHT_MARGIN = 535
    TOP_MARGIN = 800
    TABLE_WIDTH = 230  # Width for each table
    COLUMN_GAP = 30   # Gap between columns

    # Logo
    logo_path = os.path.join(app.static_folder, 'images', 'logo.png')
    logo_width = 35
    logo_height = 35
    logo_x = RIGHT_MARGIN - logo_width
    logo_y = TOP_MARGIN - logo_height + 20
    p.drawImage(logo_path, logo_x, logo_y, width=logo_width, height=logo_height, mask='auto')

    # Main Title
    p.setFillColor(colors.HexColor('#005aab'))
    p.setFont("Helvetica-Bold", 18)
    p.drawString(LEFT_MARGIN, TOP_MARGIN, f"MAIN DOCKER: {order['orderInfo']['orderId']}")

    # Order & Shipping Information
    y_position = TOP_MARGIN - 50
    
    # Order Information
    p.setFillColor(colors.black)
    p.setFont("Helvetica-Bold", 12)
    p.drawString(LEFT_MARGIN, y_position, "Order Information")
    
    order_data = [
        # ["Field", "Value"],
        ["Date Received:", order['orderInfo']['orderDate']],
        ["Due Date:", order['orderInfo']['deliveryDate']],
        ["Invoice No:", order.get('invoiceNo', 'N/A')],
        ["Client:", order['customerInfo']['contactPerson']],
        ["Company:", order.get('company', 'N/A')],
        ["PO#:", order.get('poNumber', 'N/A')]
    ]
    
    # Shipping Information (aligned with Order Information)
    p.drawString(LEFT_MARGIN + TABLE_WIDTH + COLUMN_GAP, y_position, "Shipping Information")
    
    shipping_data = [
        # ["Field", "Value"],
        ["Shipping Date:", order['orderInfo']['deliveryDate']],
        ["Contact:", order['deliveryInfo']['contactPerson']],
        ["Email:", order['deliveryInfo']['email']],
        ["Address:", order['deliveryInfo']['address']],
        ["Phone:", order['deliveryInfo']['telNo']]
    ]

    # Draw both tables at the same y-position
    table_start_y = y_position - 10
    y_position = draw_table(order_data, LEFT_MARGIN, table_start_y, [100, 130], header=False)
    draw_table(shipping_data, LEFT_MARGIN + TABLE_WIDTH + COLUMN_GAP, table_start_y, [100, 130], header=False)

    y_position -= 30
    p.setFont("Helvetica", 9)
    p.drawString(LEFT_MARGIN, y_position, "Product Name: " +  order['orderInfo']['deliveryDate'])

    y_position -= 10
    p.setFont("Helvetica", 9)
    p.drawString(LEFT_MARGIN, y_position, "Order ID: " +  order['orderInfo']['deliveryDate'])

    # Product Summary
    y_position -= 30
    p.setFont("Helvetica-Bold", 12)
    p.drawString(LEFT_MARGIN, y_position, "Job Specification")

    # Printing and Finishing summaries side by side
    y_position -= 20
    p.setFont("Helvetica", 9)
    p.drawString(LEFT_MARGIN, y_position, "Printing Summary")
    p.drawString(LEFT_MARGIN + TABLE_WIDTH + COLUMN_GAP, y_position, "Finishing Summary")
    
    # Printing & Finishing tables side by side
    y_position -= 5
    printing_data = [
        # ["Printing", ""],
        ["Sheet Size:", order['prodDetails']['layoutSize'] ],
        ["Finish Page Size:", order['prodDetails']['trimSize']],
        ["Substrate:", order['prodDetails']['substrate']],
        ["Quantity:", str(order['orderInfo']['quantity'])]
    ]
    
    finishing_data = [
        # ["Finishing", ""],
        ["Folding:", order['serviceSettings']['FOLD']['optionId']],
        ["Staple:", order['serviceSettings']['STAPLE']['optionId']],
        ["Punch:", order['serviceSettings']['PUNCH']['optionId']],
        ["Die Cut:", "N/A"],
        ["UV:", "N/A"],
        ["Lamination:", "N/A"],
        ["Flood Coat:", "N/A"],
        ["Emblishment Coat:", "N/A"],
        ["Instruction Coat:", "N/A"],
        ["Adhesive:", "N/A"],
    ]
    
    # Draw Printing and Finishing tables side by side
    y_position = draw_table(printing_data, LEFT_MARGIN, y_position, [100, 130], header=False)
    draw_table(finishing_data, LEFT_MARGIN + TABLE_WIDTH + COLUMN_GAP, y_position + (len(printing_data) * 20), [100, 130], header=False)

    # Press table below
    # y_position -= 15
    # p.setFont("Helvetica-Bold", 12)
    # p.drawString(LEFT_MARGIN, y_position, "Press")

    y_position -= 20
    p.setFont("Helvetica", 9)
    p.drawString(LEFT_MARGIN, y_position, "Press Summary")
    
    y_position -= 5
    press_data = [
        # ["Press", ""],
        ["Plates:", ""],
        ["Ink:", ""],
        ["Paper:", ""],
        ["Film:", ""]
    ]
    y_position = draw_table(press_data, LEFT_MARGIN, y_position, [100, 130], header=False)

    # Notes sections
    y_position -= 30
    p.setFont("Helvetica-Bold", 12)
    p.drawString(LEFT_MARGIN, y_position, "Order Notes:")
    p.setFont("Helvetica", 10)
    p.drawString(LEFT_MARGIN + 10, y_position - 20, order.get('jobInfo', {}).get('notes', 'N/A'))

    y_position -= 50
    p.setFont("Helvetica-Bold", 12)
    p.drawString(LEFT_MARGIN, y_position, "Prepress Notes:")
    p.setFont("Helvetica", 10)
    p.drawString(LEFT_MARGIN + 10, y_position - 20, order.get('jobInfo', {}).get('prepressNotes', 'N/A'))

    # Footer
    p.setFont("Helvetica", 8)
    p.drawString(LEFT_MARGIN, 30, f"Generated on: {order['orderInfo']['orderDate']}")
    p.drawString(RIGHT_MARGIN - 60, 30, "Page 1 of 1")

    p.save()
    pdf = buffer.getvalue()
    buffer.close()
    
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=order_{order["orderInfo"]["orderId"]}.pdf'
    
    return response

if (__name__ == '__main__'):
    app.run()