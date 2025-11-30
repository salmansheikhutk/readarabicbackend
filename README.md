# ReadArabic Backend (Flask)

A Flask API server for serving PDF files from Google Cloud Storage.

## Setup

1. **Create a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On macOS/Linux
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Google Cloud credentials:**
   - Download your service account key from Google Cloud Console
   - Save it as `service-account-key.json` in this directory (it's gitignored)
   - Or set the environment variable:
     ```bash
     export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
     ```

4. **Run the server:**
   ```bash
   python app.py
   ```

The API will be available at `http://localhost:5000`

## API Endpoints

- `GET /api/health` - Health check
- `GET /api/pdfs` - List all PDF files in the bucket
- `GET /api/pdf/<filename>` - Retrieve a specific PDF file

## Notes

- Make sure your Google Cloud service account has the necessary permissions to read from the bucket
- The bucket name and project ID are configured in `app.py`
