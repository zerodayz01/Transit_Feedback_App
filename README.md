The Public Transit Feedback Collector is a web application designed to allow public transit riders to submit and browse feedback about their experiences with local buses and trains. Users can report issues such as late buses, overcrowded stops, and service disruptions, as well as provide suggestions for improvements. The system is built on Flask and integrates several Azure services to ensure scalability, security, and efficiency.

## Features
- User Feedback Submission: Riders can submit reports detailing their transit experiences.
- Photo Uploads: Users can attach images to their feedback for better context.
- Feedback Browsing: Approved feedback entries are displayed for public viewing.
- Administrator Review: Admins can approve or reject feedback submissions.
- Real-time Transit Status: Integration with an external API to display live transit updates.
- Secure Data Storage: Feedback and images are stored using Azure Cosmos DB and Azure Blob Storage.
- CI/CD Deployment: Automated deployment via GitHub Actions.
- Cost Monitoring & Security: Uses Azure Monitor, Billing Alerts, and Network Security Groups.

## Architecture
This project utilizes several Azure services, including:
- Azure App Service: Hosts the Flask web application.
- Azure Virtual Machine (VM): Provides administrative control and background processing.
- Azure Cosmos DB: Stores structured feedback data.
- Azure Blob Storage: Manages user-uploaded images.
- Azure Virtual Network (VNet): Ensures secure communication between resources.
- Azure Load Balancer: Distributes incoming traffic for high availability.
- GitHub Actions: Automates the CI/CD pipeline.
