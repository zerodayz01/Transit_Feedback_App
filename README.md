# Public Transit Feedback Collector

## Overview
The **Public Transit Feedback Collector** is a web application designed to allow public transit riders to submit and browse feedback about their experiences with local buses and trains. Users can report issues such as late buses, overcrowded stops, and service disruptions, as well as provide suggestions for improvements. The system is built on **Flask** and integrates several **Azure services** to ensure scalability, security, and efficiency.

## Features
- **User Feedback Submission**: Riders can submit reports detailing their transit experiences.
- **Photo Uploads**: Users can attach images to their feedback for better context.
- **Feedback Browsing**: Approved feedback entries are displayed for public viewing.
- **Administrator Review**: Admins can approve or reject feedback submissions.
- **Real-time Transit Status**: Integration with an external API to display live transit updates.
- **Secure Data Storage**: Feedback and images are stored using **Azure Cosmos DB** and **Azure Blob Storage**.
- **CI/CD Deployment**: Automated deployment via **GitHub Actions**.
- **Cost Monitoring & Security**: Uses **Azure Monitor**, **Billing Alerts**, and **Network Security Groups**.

## Architecture
This project utilizes several **Azure services**, including:
- **Azure App Service**: Hosts the Flask web application.
- **Azure Virtual Machine (VM)**: Provides administrative control and background processing.
- **Azure Cosmos DB**: Stores structured feedback data.
- **Azure Blob Storage**: Manages user-uploaded images.
- **Azure Virtual Network (VNet)**: Ensures secure communication between resources.
- **Azure Load Balancer**: Distributes incoming traffic for high availability.
- **GitHub Actions**: Automates the CI/CD pipeline.

## Setup & Installation
### Prerequisites
- Python 3.x installed
- An Azure account
- A GitHub account with repository access
- Azure CLI installed locally

### Steps to Run Locally
1. **Clone the repository:**
   ```bash
   git clone <GITHUB_REPO_URL>
   cd transitfeedbackapp
   ```
2. **Create a virtual environment and activate it:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```
3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Set up environment variables:**
   Create a `.env` file and add the following:
   ```
   FLASK_APP=app.py
   FLASK_ENV=development
   COSMOS_ENDPOINT=<your_cosmos_db_endpoint>
   COSMOS_KEY=<your_cosmos_db_key>
   BLOB_CONNECTION_STRING=<your_blob_storage_connection_string>
   ```
5. **Run the application:**
   ```bash
   flask run
   ```
6. **Access the app** in your browser at `http://127.0.0.1:5000`

## Deployment on Azure
This project is deployed using **Azure App Service** with a CI/CD pipeline through **GitHub Actions**.

### Steps to Deploy
1. **Set up Azure services**
   - Create an **Azure App Service** instance
   - Set up **Azure Cosmos DB** and **Blob Storage**
   - Configure **Virtual Network** and **Network Security Group**
2. **Connect to GitHub for CI/CD**
   - Enable **GitHub Actions** in your repository settings
   - Ensure that the `main_transit-feedback-app.yml` workflow is correctly configured
3. **Push changes to the repository**
   - Once changes are pushed to the `main` branch, **GitHub Actions** will automatically deploy the latest version.
