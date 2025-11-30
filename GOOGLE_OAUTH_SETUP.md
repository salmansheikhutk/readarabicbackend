# Google OAuth Setup Guide

## Steps to Enable Google Sign-In

### 1. Create Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the **Google+ API** (or Google Identity)
4. Go to **APIs & Services** → **Credentials**
5. Click **Create Credentials** → **OAuth client ID**
6. Choose **Web application**
7. Add authorized JavaScript origins:
   - `http://localhost:3000`
   - Add your production domain when ready
8. Add authorized redirect URIs:
   - `http://localhost:3000`
   - Add your production domain when ready
9. Copy the **Client ID**

### 2. Configure Frontend

Edit `/readarabicfrontend/.env`:
```
REACT_APP_GOOGLE_CLIENT_ID=your-actual-client-id-here.apps.googleusercontent.com
```

### 3. Configure Backend

Edit `/readarabicbackend/.env`:
```
GOOGLE_CLIENT_ID=your-actual-client-id-here.apps.googleusercontent.com
```

**Note:** Use the SAME client ID in both frontend and backend!

### 4. Install Backend Dependencies

```bash
cd readarabicbackend
source venv/bin/activate
pip install google-auth==2.34.0
```

### 5. Create Database Tables

Run the user schema to create the users table:
```bash
psql -U salmansheikh -d readarabic -f user_schema.sql
```

### 6. Restart Services

```bash
# Backend
cd readarabicbackend
source venv/bin/activate
python app.py

# Frontend (in new terminal)
cd readarabicfrontend
npm start
```

## How It Works

1. User selects Arabic text without being logged in
2. Popup shows "Please log in to translate words" with Google sign-in button
3. User clicks "Sign in with Google"
4. Google OAuth popup appears
5. After successful login:
   - User info is saved to database
   - User info is stored in localStorage
   - User can now translate words
6. On future visits, user remains logged in (localStorage)
7. User profile appears in sidebar with logout option

## Database Schema

The `users` table stores:
- `google_id` - Unique Google user ID
- `email` - User email
- `name` - Display name
- `profile_picture` - Google profile image URL
- `created_at` - When user first signed up

User vocabulary and reading history are linked to this user account.
