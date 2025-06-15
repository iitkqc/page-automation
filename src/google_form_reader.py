import os
import gspread
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
        total_rows = len(all_records)

        if not all_records:
            print("No data found in the Google Sheet.")
            return []

        # Assuming the first row is headers, adjust if not
        header_row = all_records[0]
        data_rows = all_records[1:] # Skip header row

        filtered_rows = []
        for i, row in enumerate(reversed(data_rows)):

            if row[2] != '':  # Stop if timestamp is too old
                break
            row.insert(0, total_rows - i)  # Append the row number for later reference
            filtered_rows.append(row)

        return filtered_rows
    
    except Exception as e:
        print(f"Error reading Google Sheet: {e}")
        return []

def mark_confession_as_processed(sheet_url, client, confession_row, status):
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
        status_col_index = 3 # Find 'Status' column or pick a fixed one
            
        worksheet.update_cell(confession_row, status_col_index, status)
        print(f"Marked row {confession_row} as PROCESSED in Google Sheet.")

    except Exception as e:
        print(f"Error marking confession {confession_row} as processed: {e}")

def get_updated_count(sheet_url, client)-> int:
    """
    Updates the confession count in the Google Sheet.
    Assumes the count is stored in a specific cell (e.g., A1).
    """
    try:
        spreadsheet = client.open_by_url(sheet_url)
        worksheet = spreadsheet.get_worksheet(0)

        current_value = int(worksheet.cell(1, 4).value)
        
        # Assuming the count is stored in cell A1
        worksheet.update_cell(1, 4, current_value + 1)
        print(f"Updated confession count to {current_value + 1} in Google Sheet.")

        return current_value + 1
    
    except Exception as e:
        print(f"Error updating confession count: {e}")
        return 0

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
                print(f"Row: {conf[0]}, Timestamp: {conf[1]},  Text: {conf[2][:50]}...")
            
            # Example of marking processed (for first confession)
            if latest_confessions:
                first_conf = latest_confessions[0]
                mark_confession_as_processed(SHEET_URL, sheets_client, first_conf, 1)

        except Exception as e:
            print(f"An error occurred: {e}")