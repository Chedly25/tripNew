# 🔧 Fix Google OAuth Error 400: redirect_uri_mismatch

## Problem
Google OAuth is showing: "Erreur 400 : redirect_uri_mismatch"

## Root Cause
The redirect URI in your Google Cloud Console doesn't match what your app is sending.

## Step-by-Step Fix

### 1. Find Your App URL
First, determine where your app is running:
- **Heroku**: `https://your-app-name.herokuapp.com`
- **Local**: `http://localhost:5000`
- **Custom domain**: `https://your-domain.com`

### 2. Configure Google Cloud Console

#### A. Go to Google Cloud Console
1. Visit: https://console.cloud.google.com/
2. Select your project (or create one)

#### B. Create/Edit OAuth Credentials
1. Go to: **APIs & Services** → **Credentials**
2. Click **"+ CREATE CREDENTIALS"** → **"OAuth 2.0 Client ID"**
3. Choose **"Web application"**
4. Name it: **"Travel Planner App"**

#### C. Add Authorized Redirect URIs
In the "Authorized redirect URIs" section, add:

**For Heroku (replace with your actual app name):**
```
https://your-app-name.herokuapp.com/auth/google/callback
```

**For local testing:**
```
http://localhost:5000/auth/google/callback
```

**Important**: Use the EXACT URL format above!

### 3. Copy Your Credentials
After saving, you'll get:
- **Client ID**: `123456789-abcdef.apps.googleusercontent.com`
- **Client Secret**: `GOCSPX-abcdefghijk`

### 4. Set Heroku Environment Variables

#### Option A: Heroku Dashboard
1. Go to your Heroku app dashboard
2. Settings → Config Vars
3. Add:
   - `GOOGLE_CLIENT_ID` = `your-client-id.apps.googleusercontent.com`
   - `GOOGLE_CLIENT_SECRET` = `your-client-secret`

#### Option B: Heroku CLI
```bash
heroku config:set GOOGLE_CLIENT_ID="your-client-id.apps.googleusercontent.com"
heroku config:set GOOGLE_CLIENT_SECRET="your-client-secret"
```

### 5. Test the Fix
1. Redeploy your app (if needed)
2. Go to your app's login page
3. Click "Continue with Google"
4. Should now work without errors!

## Common Issues & Solutions

### Issue: "This app isn't verified"
**Solution**: This is normal for new apps. Click "Advanced" → "Go to [app name] (unsafe)" for testing.

### Issue: Still getting redirect_uri_mismatch
**Solution**: Double-check that:
- URI in Google Console EXACTLY matches your app URL
- No typos in the redirect URI
- Using `https://` for production, `http://localhost:5000` for local

### Issue: "access_denied"
**Solution**: User cancelled the OAuth flow. This is normal.

## Example Working Configuration

**If your Heroku app is**: `https://my-travel-app.herokuapp.com`

**Google Console Redirect URI should be**: 
```
https://my-travel-app.herokuapp.com/auth/google/callback
```

**Heroku Config Vars**:
```
GOOGLE_CLIENT_ID=123456789-abc123.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-abc123def456
```

## Need Help?
If you're still getting errors, please share:
1. Your app's URL (e.g., `https://your-app.herokuapp.com`)
2. The exact redirect URI you added in Google Console
3. Any error messages you're seeing

The OAuth should work perfectly once the redirect URIs match exactly!