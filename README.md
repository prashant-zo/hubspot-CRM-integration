# VectorShift - Integrations Technical Assessment

A full-stack application that demonstrates integration with various third-party services (Airtable, Notion, and HubSpot) using OAuth2 authentication.

## Project Structure

```
.
├── backend/
│   ├── integrations/
│   │   ├── airtable.py
│   │   ├── notion.py
│   │   └── hubspot.py
│   ├── main.py
│   ├── redis_client.py
│   ├── requirements.txt
│   └── test_auth.html
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── integrations/
│   │   │   ├── airtable.js
│   │   │   ├── notion.js
│   │   │   └── hubspot.js
│   │   ├── App.js
│   │   ├── data-form.js
│   │   ├── integration-form.js
│   │   ├── index.js
│   │   └── index.css
│   ├── package.json
│   └── README.md
└── README.md
```

## Features

- OAuth2 integration with multiple services:
  - Airtable
  - Notion
  - HubSpot
- Secure credential management using Redis
- Modern React frontend with Material-UI
- FastAPI backend with comprehensive API documentation
- Real-time data loading and display

## Prerequisites

- Python 3.11
- Node.js and npm
- Redis
- Git

## Backend Setup

1. **Python Environment Setup**:
   ```bash
   brew install python@3.11
   cd backend
   python3.11 -m venv venv
   source venv/bin/activate
   ```

2. **Install Dependencies**:
   ```bash
   pip install --upgrade pip setuptools wheel
   pip install -r requirements.txt
   ```

3. **Redis Setup**:
   ```bash
   brew services start redis
   ```

4. **Configure Integration Credentials**:
   - Update the integration files in `backend/integrations/` with your service credentials
   - For HubSpot:
     - Add your HubSpot Client ID and Client Secret
     - Configure the redirect URI in HubSpot
     - Set up required scopes

5. **Run the Backend Server**:
   ```bash
   uvicorn main:app --reload
   ```
   The API will be available at http://127.0.0.1:8000
   API documentation: http://127.0.0.1:8000/docs

## Frontend Setup

1. **Install Dependencies**:
   ```bash
   cd frontend
   rm -rf node_modules package-lock.json
   npm cache clean --force
   npm install
   ```

2. **Start the Development Server**:
   ```bash
   npm start
   ```
   The application will be available at http://localhost:3000

## Integration Flow

### HubSpot Integration (Example)

1. **Authorization**:
   - User selects HubSpot from the integration dropdown
   - Clicks "Connect to HubSpot"
   - Authenticates with HubSpot Test Account
   - OAuth2 callback processes the authorization

2. **Data Loading**:
   - After successful connection, the "LOAD DATA" button appears
   - Clicking loads HubSpot contacts data
   - Data is displayed in a formatted JSON view

## API Endpoints

### HubSpot Integration

- `POST /integrations/hubspot/authorize` - Initiate OAuth2 flow
- `GET /integrations/hubspot/oauth2callback` - OAuth2 callback handler
- `POST /integrations/hubspot/credentials` - Retrieve stored credentials
- `POST /integrations/hubspot/load` - Load HubSpot data

### Airtable Integration

- `POST /integrations/airtable/authorize` - Initiate OAuth2 flow
- `GET /integrations/airtable/oauth2callback` - OAuth2 callback handler
- `POST /integrations/airtable/credentials` - Retrieve stored credentials
- `POST /integrations/airtable/load` - Load Airtable data

### Notion Integration

- `POST /integrations/notion/authorize` - Initiate OAuth2 flow
- `GET /integrations/notion/oauth2callback` - OAuth2 callback handler
- `POST /integrations/notion/credentials` - Retrieve stored credentials
- `POST /integrations/notion/load` - Load Notion data

## Troubleshooting

### Common Issues

1. **Redis Connection Issues**:
   - Ensure Redis server is running
   - Check Redis connection settings in `redis_client.py`

2. **OAuth2 Flow Issues**:
   - Verify correct redirect URIs in service configurations
   - Check scopes and permissions
   - Ensure proper state parameter handling

3. **Frontend Connection Issues**:
   - Verify CORS settings in backend
   - Check API endpoint URLs in frontend code
   - Ensure proper credential handling

## Development Notes

- The project uses Python 3.11 for better package compatibility
- Redis is used for secure credential storage
- The frontend uses React with Material-UI for a modern UI
- FastAPI provides automatic API documentation
- OAuth2 flow includes state parameter validation for security

## Author

Prashant 
Email: prashantkd010@gmail.com

## License

This project is part of a technical assessment and is not licensed for public use. 
