# TradeGuard

TradeGuard is a database-driven stock trading platform that identifies potentially risky trading behaviour. It uses PostgreSQL triggers and configurable risk rules to detect behavioural patterns and generate explainable alerts.

## Features

- Trader registration and login
- Stock buying and selling
- Automatic portfolio and holdings updates
- Revenge-trading detection
- Over-leveraging detection
- Portfolio concentration monitoring
- Pre-trade risk warnings
- Behavioural alert management
- Administrator review of alerts

## Technologies Used

- Python
- Flask
- PostgreSQL
- SQL and PL/pgSQL
- HTML, CSS, and JavaScript
- psycopg2

## Project Setup

Follow these steps to run TradeGuard on your local machine.

### 1. Clone the Repository

Clone this repository and open the project folder in VS Code.

### 2. Create a PostgreSQL Database

Open pgAdmin and create a new PostgreSQL database named `tradeguard`.

### 3. Create the Database Schema

Open the Query Tool for the `tradeguard` database.

Execute the SQL commands in:

`sql/01_schema.sql`

This creates the database tables and their constraints.

**Important:** Running `python app.py` does not automatically execute this SQL file. The database schema must be created separately before starting the application.

### 4. Import the CSV Files

Import the supplied CSV datasets into their corresponding PostgreSQL tables.

Ensure that the correct database and table are selected for each file. Complete the imports before proceeding to the next step.

Do not import the CSV files again if the database already contains the dataset.

### 5. Configure Environment Variables

A file named `.env.example` is included in the repository as a configuration template.

Create your own `.env` file by copying `.env.example` and renaming the copy to `.env`.

For example, on Windows PowerShell:

```powershell
Copy-Item .env.example .env

Open the newly created `.env` file and update the placeholder values with your local PostgreSQL credentials and a secret key.

For example:

```env
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/tradeguard
SECRET_KEY=your_own_secret_key
```

Replace `YOUR_PASSWORD` with your PostgreSQL password and set `SECRET_KEY` to a randomly generated secret value. Ensure that the variable names match those expected by `config.py`.

**Important:** Never commit your actual `.env` file or database credentials to GitHub. The `.env.example` file should contain placeholder values only.

### 6. Create a Virtual Environment

Open a terminal in the project directory and create a Python virtual environment:

```bash
python -m venv .venv
```

Activate the virtual environment on Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

If activation is successful, `(.venv)` should appear at the beginning of your terminal prompt.

### 7. Install Dependencies

With the virtual environment activated, install the required packages:

```bash
pip install -r requirements.txt
```

This installs the Python dependencies required by TradeGuard.

### 8. Run the Application

Ensure that:

- PostgreSQL is running.
- The `tradeguard` database has been created and populated.
- The database triggers and views have been installed.
- The `.env` file contains the correct database connection details.
- The virtual environment is activated.

Start the Flask application:

```bash
python app.py
```

Once the server starts, open the local address displayed in the terminal. It is usually:

http://127.0.0.1:5000

You can now register a trader account, log in, place trades, monitor your portfolio, and view behavioural risk warnings and alerts.

### 9. Database Setup Order

For a fresh installation, perform the database setup in this order:

1. Create the `tradeguard` PostgreSQL database.
2. Execute `sql/01_schema.sql` to create the tables.
3. Import the supplied CSV files into their corresponding tables.
4. Execute `sql/02_triggers.sql` to install the triggers.
5. Execute `sql/03_views.sql` to create the database views.
6. Configure the `.env` file.
7. Create and activate the Python virtual environment.
8. Install dependencies using `requirements.txt`.
9. Start the application using `python app.py`.

**Note:** The SQL scripts must be executed separately in PostgreSQL. Running `python app.py` does not automatically create the tables or import the CSV datasets. Do not repeat the CSV imports if the database is already populated.

## Security Considerations

- Passwords are stored as hashes rather than plaintext.
- Database credentials and the Flask secret key are configured through environment variables.
- The `.env` file should remain excluded from version control.
- Never publish database passwords or other sensitive credentials in the repository.

## Project Scope

TradeGuard demonstrates how database triggers and configurable risk rules can be used to monitor trading behaviour and generate explainable alerts.

The application supports simulated stock trading, portfolio management, pre-trade validation, and behavioural risk monitoring through a Flask interface connected to PostgreSQL.

It is intended for educational and demonstration purposes. It does not connect to a live brokerage or execute real stock-market transactions.