import os
import gspread
import json
from datetime import datetime
import base64 

# You'll need to share your Google Sheet with the service account email.

def decode_credentials(base64_string, filename="credentials.json"):
    """
    Decodes a base64 string into a file.
    This file is created temporarily in the GitHub Actions runner.
    """
    try:
        decoded_bytes = base64.b64decode(base64_string)
        with open(filename, "wb") as f:
            f.write(decoded_bytes)
        print(f"Successfully decoded credentials to {filename}")
        return filename
    except Exception as e:
        print(f"Error decoding credentials: {e}")
        raise # Re-raise the exception

def get_sheets_client(credentials_path):
    """Authenticates and returns the gspread client using a service account."""
    try:
        # Load service account credentials from a JSON file
        gc = gspread.service_account(filename=credentials_path)
        return gc
    except Exception as e:
        print(f"Error authenticating with Google Sheets service account: {e}")
        raise

def get_latest_confessions_from_sheet(sheet_url, client, processed_ids_file="processed_confessions.json"):
    """
    Retrieves confessions from a Google Sheet, filtering out already processed ones.
    Assumes:
    - Confessions are in the first worksheet.
    - Column A (index 0) contains a unique identifier (e.g., timestamp, or an ID you assign).
    - Column B (index 1) contains the confession text.
    - Rows are added to the bottom.
    """
    try:
        spreadsheet = client.open_by_url(sheet_url)
        worksheet = spreadsheet.get_worksheet(0) # Get the first worksheet

        # Get all records as a list of dictionaries (using header row as keys)
        # Or as a list of lists if you prefer to access by index
        all_records = worksheet.get_all_values()

        if not all_records:
            print("No data found in the Google Sheet.")
            return []

        # Assuming the first row is headers, adjust if not
        header_row = all_records[0]
        data_rows = all_records[1:] # Skip header row

        # Load processed IDs
        processed_ids = set()
        if os.path.exists(processed_ids_file):
            try:
                with open(processed_ids_file, 'r') as f:
                    processed_ids = set(json.load(f))
            except json.JSONDecodeError:
                print(f"Warning: Could not parse {processed_ids_file}. Starting fresh.")
                processed_ids = set()
        
        confessions = []
        # Assuming ID is in the first column, text in the second. Adjust if needed.
        # It's highly recommended to have a unique ID in your sheet. A timestamp can work.
        # Or even better, if you use Google Forms to populate the sheet,
        # the form response ID or submission timestamp makes a good unique ID.
        
        # Determine column indices dynamically if you have headers
        try:
            id_col_index = header_row.index("ID") if "ID" in header_row else 0 # Assuming 'ID' header or first column
            text_col_index = header_row.index("Confession Text") if "Confession Text" in header_row else 1 # Assuming 'Confession Text' header or second column
            timestamp_col_index = header_row.index("Timestamp") if "Timestamp" in header_row else None
        except ValueError:
            print("Warning: 'ID' or 'Confession Text' headers not found. Using default column indices (0 and 1).")
            id_col_index = 0
            text_col_index = 1
            timestamp_col_index = None

        for i, row in enumerate(data_rows):
            if not row or len(row) <= max(id_col_index, text_col_index):
                continue # Skip empty or malformed rows

            confession_id = row[id_col_index].strip()
            confession_text = row[text_col_index].strip()
            
            # If you don't have a specific ID column, you can generate one
            # e.g., by combining timestamp and row number
            if not confession_id:
                confession_id = f"row_{i+2}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}" # +2 for header and 0-indexing
            
            if confession_id and confession_text and confession_id not in processed_ids:
                confessions.append({
                    'id': confession_id,
                    'text': confession_text,
                    'row_num': i + 2 # Google Sheet row number (1-indexed, +1 for header)
                })
        return confessions
    except Exception as e:
        print(f"Error reading Google Sheet: {e}")
        return []

def mark_confession_as_processed(sheet_url, client, confession_id, row_num, processed_ids_file="processed_confessions.json"):
    """
    Marks a confession as processed (e.g., by updating a column in the sheet).
    Also adds the ID to the local processed_confessions.json.
    """
    try:
        spreadsheet = client.open_by_url(sheet_url)
        worksheet = spreadsheet.get_worksheet(0)
        
        # Option 1: Write "PROCESSED" to a new column (e.g., column C, index 2)
        # Ensure your sheet has this column or gspread will raise an error if out of bounds.
        # You might need to add a "Status" header to your sheet.
        status_col_index = -1 # Find 'Status' column or pick a fixed one
        headers = worksheet.row_values(1)
        try:
            status_col_index = headers.index("Status") + 1 # 1-indexed column number
        except ValueError:
            print("Warning: 'Status' header not found. Cannot update status column in sheet.")
            # Fallback: Just update processed_ids.json
            
        if status_col_index != -1:
            worksheet.update_cell(row_num, status_col_index, "PROCESSED")
            print(f"Marked row {row_num} as PROCESSED in Google Sheet.")

        # Option 2: Add to local processed_ids.json file
        processed_ids = set()
        if os.path.exists(processed_ids_file):
            try:
                with open(processed_ids_file, 'r') as f:
                    processed_ids = set(json.load(f))
            except json.JSONDecodeError:
                pass # Will start fresh if file is corrupt
        
        processed_ids.add(confession_id)
        with open(processed_ids_file, 'w') as f:
            json.dump(list(processed_ids), f)
        print(f"Added confession ID {confession_id} to processed_confessions.json.")

    except Exception as e:
        print(f"Error marking confession {confession_id} as processed: {e}")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    SHEET_URL = os.getenv("GOOGLE_SHEET_URL")
    CREDENTIALS_PATH = decode_credentials(os.getenv("GOOGLE_SHEETS_CREDENTIALS_FILE"), "google_sheets_service_account_key.json")

    if not SHEET_URL or not CREDENTIALS_PATH:
        print("Please set GOOGLE_SHEET_URL and GOOGLE_SHEETS_CREDENTIALS_FILE environment variables.")
    else:
        try:
            sheets_client = get_sheets_client(CREDENTIALS_PATH)
            latest_confessions = get_latest_confessions_from_sheet(SHEET_URL, sheets_client)
            for conf in latest_confessions:
                print(f"ID: {conf['id']}, Text: {conf['text'][:50]}..., Row: {conf['row_num']}")
            
            # Example of marking processed (for first confession)
            if latest_confessions:
                first_conf = latest_confessions[0]
                mark_confession_as_processed(SHEET_URL, sheets_client, first_conf['id'], first_conf['row_num'])

        except Exception as e:
            print(f"An error occurred: {e}")