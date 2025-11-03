# AgroAdvisor: ML-Powered Agricultural Advisor

This project is a web application, **AgroAdvisor**, built to assist farmers by providing machine learning-based predictions for crop prices and recommendations for planting. It also includes a marketplace for farmers to sell their products.

## Author

* **AKASH G V**
* **Email:** `akashgveerabhadrappa@gmail.com`
* **LinkedIn:** [linkedin.com/in/akashgveerabhadrappa](https://linkedin.com/in/akashgveerabhadrappa)
* **GitHub:** [github.com/Akashgveerabhadrappa](https://github.com/Akashgveerabhadrappa)

## Project Description

AgroAdvisor is a backend-focused service that ingests and validates market and weather data from various sources (including public APIs and local CSV files) to power its prediction models. These models engineer features to serve predictions and recommendations to users via REST endpoints and a user-friendly web interface.

The application is structured with different portals for farmers and administrators, and it includes robust user authentication.

## Key Features

* **User Authentication:** Secure registration and login system for users (farmers) and administrators.
* **Farmer Dashboard:** A personalized dashboard for farmers to access predictions and recommendations.
* **Crop Recommendation:** Utilizes ML models (`recommender.py`) to suggest optimal crops to plant based on various parameters.
* **Price Prediction:** Uses ML models (`predictor.py`, `yield_model.joblib`) to forecast crop prices, helping farmers make informed decisions.
* **Marketplace:** A platform allowing farmers to add and list their products for sale, viewable by other users.
* **Admin Panel:** A dashboard for administrators to manage the application.

## Technology Stack

* **Backend:** Python, Flask
* **Machine Learning:** Pandas, scikit-learn
* **Frontend:** HTML, CSS, JavaScript
* **Database:** (As per resume skills: PostgreSQL, MySQL, MongoDB)
* **APIs:** REST
* **DevOps Concepts Used:** Structured logging, containerization (Docker basics)

## How to Run (PowerShell on Windows)

1.  **Set Execution Policy (if needed):**
    * This allows the virtual environment activation script to run. You only need to do this once per session.
    ```powershell
    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
    ```

2.  **Activate Virtual Environment:**
    * This isolates the project's dependencies from other Python projects on your system.
    ```powershell
    .\venv\Scripts\activate
    ```

3.  **Install Dependencies:**
    * This will install all the required libraries listed in `requirements.txt`.
    ```powershell
    pip install -r requirements.txt
    ```

4.  **Set Flask App Environment Variable:**
    * This tells Flask where your application's entry point is.
    ```powershell
    $env:FLASK_APP = "run.py"
    ```

5.  **Initialize and Upgrade the Database:**
    * These commands create the initial database structure based on your models.
    ```powershell
    flask db init
    flask db migrate -m "Initial setup"
    flask db upgrade
    ```

6.  **Run the Application:**
    * This will start the development server.
    ```powershell
    flask run
    ```
    * You can now access the application in your web browser, usually at `http://127.0.0.1:5000`.

---

### Create an Admin User

* To create an admin user, you'll need to open a **new, separate PowerShell terminal** and run the following commands while the application is still running in your first terminal.

1.  **Activate the virtual environment in the new terminal:**
    ```powershell
    .\venv\Scripts\activate
    ```

2.  **Set the `FLASK_APP` environment variable:**
    ```powershell
    $env:FLASK_APP = "run.py"
    ```

3.  **Open the Flask Shell:**
    ```powershell
    flask shell
    ```

4.  **Inside the `flask shell`, run the following Python code:**
    * This will find the user with the email 'owner@gmail.com', assign them the 'Admin' role, and save the changes to the database.
    ```python
    from agroadvisor.models import User, Role, db
    u = User.query.filter_by(email='owner@gmail.com').first()
    admin_role = Role.query.filter_by(name='Admin').first()
    u.role = admin_role
    db.session.commit()
    exit()
    ```

## Contact

For any inquiries or collaboration, please feel free to connect with me:

* **Email:** `akashgveerabhadrappa@gmail.com`
* **LinkedIn:** [linkedin.com/in/akashgveerabhadrappa](https://linkedin.com/in/akashgveerabhadrappa)