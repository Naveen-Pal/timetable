import os
import base64
from dotenv import load_dotenv
import pandas as pd
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pickle

# Load environment variables from .env file
load_dotenv()

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

def restore_token_from_env():
    b64_token = os.environ.get('GOOGLE_TOKEN_B64')
    if b64_token:
        # Add padding if necessary
        padding = 4 - (len(b64_token) % 4)
        if padding != 4:
            b64_token += '=' * padding
        with open('token.pickle', 'wb') as f:
            f.write(base64.b64decode(b64_token))

def get_google_sheets_data():
    restore_token_from_env()
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            print("Token invalid or missing. Manual auth required.")
            return None

    try:
        service = build('sheets', 'v4', credentials=creds)
        spreadsheet_id = os.environ.get('SPREADSHEET_ID')
        sheet_name = os.environ.get('SHEET_NAME')
        if not spreadsheet_id or not sheet_name:
            print('Missing env variables.')
            return None

        sheet = service.spreadsheets()
        result = sheet.values().get(
            spreadsheetId=spreadsheet_id,
            range=sheet_name
        ).execute()

        values = result.get('values', [])
        if not values:
            print('No data found.')
            return None
        max_len = len(values[0])
        normalized = [row + [''] * (max_len - len(row)) for row in values[1:]]
        df = pd.DataFrame(normalized, columns=values[0])

        # df = pd.DataFrame(values[1:], columns=values[0])
        return df

    except HttpError as error:
        print(f'An error occurred: {error}')
        return None


def main():
    """Main function to update timetable data."""
    print('Fetching data from Google Sheets...')
    df = get_google_sheets_data()
    
    if df is not None:
        print('Updating CSV files...')
        df.to_csv('Timetable.csv', index=False)
        print('Successfully updated timetable data.')

    else:
        print('Failed to fetch data from Google Sheets.')

if __name__ == '__main__':
    main() 