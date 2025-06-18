import os
import gspread
import base64 

# You'll need to share your Google Sheet with the service account email.

class GoogleFormReader:
    def __init__(self, sheet_url, credentials_path=None):
        """
        Initialize the Google Form Reader with sheet URL and optional credentials path.
        If credentials_path is not provided, it will try to decode from environment variable.
        """
        self.sheet_url = sheet_url
        self.client = None
        self.credentials_path = credentials_path
        
        if not self.credentials_path:
            self.credentials_path = self.decode_credentials(
                os.getenv("GOOGLE_SHEETS_CREDENTIALS_FILE"), 
                "google_sheets_credentials.json"
            )
        
        self.client = self.get_sheets_client(self.credentials_path)

    def decode_credentials(self, base64_string, filename="credentials.json"):
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

    def get_sheets_client(self, credentials_path):
        """Authenticates and returns the gspread client using a service account."""
        try:
            # Load service account credentials from a JSON file
            gc = gspread.service_account(filename=credentials_path)
            return gc
        except Exception as e:
            print(f"Error authenticating with Google Sheets service account: {e}")
            raise

    def get_latest_confessions_from_sheet(self, processed_ids_file="processed_confessions.json"):
        """
        Retrieves confessions from a Google Sheet, filtering out already processed ones.
        Assumes:
        - Confessions are in the first worksheet.
        - Column A (index 0) contains a unique identifier (e.g., timestamp, or an ID you assign).
        - Column B (index 1) contains the confession text.
        - Rows are added to the bottom.
        """
        try:
            spreadsheet = self.client.open_by_url(self.sheet_url)
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

    def mark_confession_as_processed(self, confession_row, status):
        """
        Marks a confession as processed (e.g., by updating a column in the sheet).
        Also adds the ID to the local processed_confessions.json.
        """
        try:
            spreadsheet = self.client.open_by_url(self.sheet_url)
            worksheet = spreadsheet.get_worksheet(0)
            
            # Option 1: Write "PROCESSED" to a new column (e.g., column C, index 2)
            # Ensure your sheet has this column or gspread will raise an error if out of bounds.
            # You might need to add a "Status" header to your sheet.
            status_col_index = 3 # Find 'Status' column or pick a fixed one
                
            worksheet.update_cell(confession_row, status_col_index, status)
            print(f"Marked row {confession_row} as PROCESSED in Google Sheet.")

        except Exception as e:
            print(f"Error marking confession {confession_row} as processed: {e}")

    def get_count(self) -> int:
        """
        Updates the confession count in the Google Sheet.
        Assumes the count is stored in a specific cell (e.g., A1).
        """
        try:
            spreadsheet = self.client.open_by_url(self.sheet_url)
            worksheet = spreadsheet.get_worksheet(0)
            return int(worksheet.cell(1, 4).value)
        
        except Exception as e:
            print(f"Error getting confession count: {e}")
            return 0
        
    def increment_count(self) -> None:
        """
        Updates the confession count in the Google Sheet.
        Assumes the count is stored in a specific cell (e.g., A1).
        """
        try:
            spreadsheet = self.client.open_by_url(self.sheet_url)
            worksheet = spreadsheet.get_worksheet(0)

            current_value = int(worksheet.cell(1, 4).value)
            
            # Assuming the count is stored in cell A1
            worksheet.update_cell(1, 4, current_value + 1)
            print(f"Updated confession count to {current_value + 1} in Google Sheet.")
        
        except Exception as e:
            print(f"Error incrementing confession count: {e}")
            return
        
    def get_instagram_access_token(self) -> str:
        """Fetches the Instagram access token from the Google Sheet."""
        try:
            spreadsheet = self.client.open_by_url(self.sheet_url)
            token = spreadsheet.get_worksheet(0).cell(1, 5).value
            return token if token else ""
        except Exception as e:
            print(f"Error getting Instagram access token: {e}")
            return ""

    def set_instagram_access_token(self, token):
        """Sets the Instagram access token in the Google Sheet."""
        try:
            spreadsheet = self.client.open_by_url(self.sheet_url)
            worksheet = spreadsheet.get_worksheet(0)
            worksheet.update_cell(1, 5, token)  # Assuming token is stored in cell E1
            print("Instagram access token updated successfully.")
        except Exception as e:
            print(f"Error updating Instagram access token: {e}")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    SHEET_URL = os.getenv("GOOGLE_SHEET_URL")

    if not SHEET_URL:
        print("Please set GOOGLE_SHEET_URL environment variables.")
    else:
        try:
            reader = GoogleFormReader(SHEET_URL)
            latest_confessions = reader.get_latest_confessions_from_sheet()
            for conf in latest_confessions:
                print(f"Row: {conf[0]}, Timestamp: {conf[1]},  Text: {conf[2][:50]}...")
            
            # Example of marking processed (for first confession)
            if latest_confessions:
                first_conf = latest_confessions[0]
                reader.mark_confession_as_processed(first_conf[0], 1)

        except Exception as e:
            print(f"An error occurred: {e}")