# Database Configuration
MONGODB_HOST = 'localhost'
MONGODB_PORT = 27017
MONGODB_DB = 'printorder'

# Email Configuration
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = ''  # Add your email
MAIL_PASSWORD = ''  # Add your app password

# Application Configuration
SECRET_KEY = ''  # Generate a unique secret key
DEBUG = False

# File Upload Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}

# Hot Folder Configuration
HOT_FOLDER_PATH = ''  # Add your hot folder path

# Pagination Configuration
ITEMS_PER_PAGE = 10 