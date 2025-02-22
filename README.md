# Print Order System Setup

## Make an mongodb account
1. Register/Login to https://www.mongodb.com/

2. Create a new Project 'company-name-csrform'

3. Create a new Cluster. 
Cluster name: cluster0
Provider" AWS
Select Free Tier.

4. Configure your ip address and db password.

5. Select your preferred connection type



## Configuration
1. Copy `config.template.py` to `config.py`:

bash
cp config.template.py config.py


2. Edit `config.py` with your settings:
- MongoDB connection details
- Email credentials
- Secret key
- Hot folder path
- Other configuration options

## Required Settings

### MongoDB
- `MONGODB_HOST`: MongoDB server address
- `MONGODB_PORT`: MongoDB server port
- `MONGODB_DB`: Database name

### Email
- `MAIL_USERNAME`: Gmail address
- `MAIL_PASSWORD`: Gmail App Password

### Security
- `SECRET_KEY`: Generate a unique secret key
python
import os
import secrets
secret_key = secrets.token_hex(16)

### File Paths
- `UPLOAD_FOLDER`: Path for temporary file uploads
- `HOT_FOLDER_PATH`: Path to printer hot folder