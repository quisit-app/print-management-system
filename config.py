import os

# Database Configuration
MONGO_URI = "mongodb+srv://test:123password@test.o3j91.mongodb.net/"
MONGODB_DB = "sampleDB"
MONGODB_FORM_COLLECTION = "form"
MONGODB_USER_COLLECTION = 'users'

# Application Configuration
SECRET_KEY = 'your-secret-key-here'  # Change this to a secure secret key
DEBUG = True

# Email Configuration
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = 'quisit.app@gmail.com'  # Your Gmail address
MAIL_PASSWORD = 'ablo wqgw jakq pdge'     # Your Gmail app password

LOGO_LOCATION = os.path.join('static', 'images')


# File Upload Configuration
UPLOAD_FOLDER = 'C:/ProgramData/AccurioPro Flux/server/hotfolder/XML hot folder/'
ALLOWED_EXTENSIONS = {'pdf', 'ps', 'eps', 'csv'}
MAX_CONTENT_LENGTH = 64 * 1024 * 1024  # 16MB max file size

LOGO_LOCATION = os.path.join('static', 'images')

# Pagination Configuration
ITEMS_PER_PAGE = 10 