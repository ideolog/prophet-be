Prophet
=======

This is the backend for the Prophet project, a Django-based application that provides APIs for narrative analysis and claim validation.

Project structure
-----------------

The project is structured as follows:

├── manage.py # Django management script

├── prophet\_be/ # Core Django project files

│ ├── settings.py # Project settings

│ ├── urls.py # Root URL configuration

│ └── wsgi.py # WSGI application entry point

├── narratives/ # Main app for narrative and claim management

│ ├── models.py # Database models

│ ├── views.py # API views

│ ├── serializers.py # API serializers

│ ├── linguistic\_module.py # Claim validation logic

│ ├── migrations/ # Database migrations

│ └── management/ # Custom management commands

├── sms/ # Placeholder app (optional)

├── csv/ # CSV files for data import/export

├── .env # Environment variables (not included in the repo)

├── requirements.txt # Python dependencies

└── README.md # Project documentation

Features
--------

*   **API for Narrative Management**: Manage narratives and claims with rich features.
    
*   **Claim Validation**: Built-in linguistic validation for claim submission.
    
*   **Support for Spacy**: Leverages spaCy for text processing and similarity checks.
    

Setup Instructions
------------------

### 1\. Prerequisites

*   Python 3.10+
    
*   PostgreSQL (optional, depending on your setup)
    
*   pip or pipenv for package management
    

### 2\. Installation

Clone the repository and navigate to the project directory:

git clone https://github.com/your-username/prophet-be.git

cd prophet-be

Create a virtual environment and install dependencies:

python -m venv env

source env/bin/activate # On Windows, use \`env\\Scripts\\activate\`

pip install -r requirements.txt

### 3\. Configuration

Create a .env file in the root directory and add your environment variables:

SECRET_KEY=your-secret-key

DEBUG=True

DATABASE_URL=your-database-url

### 4\. Run migrations

Apply database migrations:

python manage.py migrate

### 5\. Start Development Server

Run the server locally:

python manage.py runserver

### 6\. Test API

Visit http://127.0.0.1:8000/api/ in your browser or use tools like Postman to test endpoints.

License
-------

This project is licensed under the [MIT License](LICENSE).