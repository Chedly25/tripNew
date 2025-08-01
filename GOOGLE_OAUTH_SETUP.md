# Google OAuth Setup Guide

## Prerequisites

To enable Google Sign-In, you need to:

1. **Create a Google Cloud Project**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one

2. **Enable Google+ API**
   - In the Cloud Console, navigate to "APIs & Services" > "Library"
   - Search for "Google+ API" and enable it

3. **Create OAuth 2.0 Credentials**
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth 2.0 Client IDs"
   - Choose "Web application"
   - Add your domain to "Authorized JavaScript origins":
     - For development: `http://localhost:5000`
     - For production: `https://your-app-domain.com`
   - Add redirect URIs:
     - For development: `http://localhost:5000/auth/google/callback`
     - For production: `https://your-app-domain.com/auth/google/callback`

## Environment Variables Setup

### For Heroku Deployment

Set the following environment variables in your Heroku app:

```bash
heroku config:set GOOGLE_CLIENT_ID="your-google-client-id.apps.googleusercontent.com"
heroku config:set GOOGLE_CLIENT_SECRET="your-google-client-secret"
heroku config:set ANTHROPIC_API_KEY="sk-ant-your-anthropic-key-here"
```

### For Local Development

Create a `.env` file in your project root:

```env
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here
```

## Testing

1. Restart your application after setting the environment variables
2. Navigate to the login page
3. The "Continue with Google" button should now work
4. AI features will also work with the Anthropic API key

## Security Notes

- Never commit your actual credentials to version control
- Use different OAuth credentials for development and production
- Keep your client secret secure and never expose it in client-side code