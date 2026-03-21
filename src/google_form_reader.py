import base64
import os
import re
from dataclasses import dataclass
from typing import List

import gspread

from model import Confession

# You'll need to share your Google Sheet with the service account email.

MANUAL_POST_HEADER_ALIASES = {
    "post",
    "manual post",
    "manual_post",
    "force post",
    "force_post",
    "priority post",
    "priority_post",
    "bypass ai",
    "bypass_ai",
}


@dataclass
class SheetLayout:
    status_col_index: int
    manual_post_col_index: int | None
    count_col_index: int
    token_col_index: int


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
                "google_sheets_credentials.json",
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
            raise

    def get_sheets_client(self, credentials_path):
        """Authenticates and returns the gspread client using a service account."""
        try:
            gc = gspread.service_account(filename=credentials_path)
            return gc
        except Exception as e:
            print(f"Error authenticating with Google Sheets service account: {e}")
            raise

    def _get_worksheet(self):
        spreadsheet = self.client.open_by_url(self.sheet_url)
        return spreadsheet.get_worksheet(0)

    def _normalize_header(self, value: str | None) -> str:
        return re.sub(r"[^a-z0-9]+", " ", (value or "").strip().lower()).strip()

    def _find_named_column(self, header_row: list[str], names: set[str]) -> int | None:
        for index, value in enumerate(header_row, start=1):
            if self._normalize_header(value) in names:
                return index
        return None

    def _resolve_layout(self, worksheet) -> SheetLayout:
        header_row = worksheet.row_values(1)
        status_col_index = self._find_named_column(header_row, {"status"}) or 3
        manual_post_col_index = self._find_named_column(header_row, MANUAL_POST_HEADER_ALIASES)

        search_start = max(status_col_index, manual_post_col_index or 0) + 1

        count_col_index = 4
        for index in range(search_start, len(header_row) + 1):
            value = (header_row[index - 1] or "").strip()
            if value.isdigit():
                count_col_index = index
                break

        token_col_index = max(count_col_index + 1, 5)
        reserved_headers = {
            "timestamp",
            "your confession",
            "confession",
            "confession text",
            "status",
            *MANUAL_POST_HEADER_ALIASES,
        }
        for index in range(count_col_index + 1, len(header_row) + 1):
            value = (header_row[index - 1] or "").strip()
            normalized = self._normalize_header(value)
            if not value or value.isdigit() or normalized in reserved_headers:
                continue
            token_col_index = index
            break

        return SheetLayout(
            status_col_index=status_col_index,
            manual_post_col_index=manual_post_col_index,
            count_col_index=count_col_index,
            token_col_index=token_col_index,
        )

    def get_latest_confessions_from_sheet(self) -> List[Confession]:
        """
        Retrieves confessions from a Google Sheet, filtering out already processed ones.
        """
        try:
            worksheet = self._get_worksheet()
            all_records = worksheet.get_all_values()
            total_rows = len(all_records)

            if not all_records:
                print("No data found in the Google Sheet.")
                return []

            layout = self._resolve_layout(worksheet)
            required_columns = max(
                layout.status_col_index,
                layout.manual_post_col_index or 0,
                2,
            )
            data_rows = all_records[1:]

            filtered_confessions = []
            for reverse_index, row in enumerate(reversed(data_rows), start=1):
                padded_row = row + [""] * max(0, required_columns - len(row))
                status_value = padded_row[layout.status_col_index - 1].strip()

                if status_value != "":
                    break

                force_post = False
                if layout.manual_post_col_index:
                    force_post = (
                        padded_row[layout.manual_post_col_index - 1].strip() == "1"
                    )

                confession = Confession(
                    timestamp=padded_row[0],
                    row_num=total_rows - reverse_index + 1,
                    text=padded_row[1],
                    summary_caption=None,
                    sentiment=None,
                    category=None,
                    sigma_reply=None,
                    pinned_comments=None,
                    force_post=force_post,
                )
                filtered_confessions.append(confession)

            return filtered_confessions

        except Exception as e:
            print(f"Error reading Google Sheet: {e}")
            return []

    def mark_confession_as_processed(self, confession_row, status, clear_manual_post=False):
        """
        Marks a confession as processed by updating the sheet status column.
        When requested, it also clears the manual-post override cell.
        """
        try:
            worksheet = self._get_worksheet()
            layout = self._resolve_layout(worksheet)

            worksheet.update_cell(confession_row, layout.status_col_index, status)
            if clear_manual_post and layout.manual_post_col_index:
                worksheet.update_cell(confession_row, layout.manual_post_col_index, "")

            print(f"Marked row {confession_row} as PROCESSED in Google Sheet.")

        except Exception as e:
            print(f"Error marking confession {confession_row} as processed: {e}")

    def get_count(self) -> int:
        """
        Reads the confession count from the first row metadata cells.
        """
        try:
            worksheet = self._get_worksheet()
            layout = self._resolve_layout(worksheet)
            return int((worksheet.cell(1, layout.count_col_index).value or "0").strip())

        except Exception as e:
            print(f"Error getting confession count: {e}")
            return 0

    def increment_count(self) -> None:
        """
        Increments the confession count stored in the first row metadata cells.
        """
        try:
            worksheet = self._get_worksheet()
            layout = self._resolve_layout(worksheet)

            current_value = int((worksheet.cell(1, layout.count_col_index).value or "0").strip())
            worksheet.update_cell(1, layout.count_col_index, current_value + 1)
            print(f"Updated confession count to {current_value + 1} in Google Sheet.")

        except Exception as e:
            print(f"Error incrementing confession count: {e}")

    def get_instagram_access_token(self) -> str:
        """Fetches the Instagram access token from the Google Sheet."""
        try:
            worksheet = self._get_worksheet()
            layout = self._resolve_layout(worksheet)
            token = worksheet.cell(1, layout.token_col_index).value
            return token if token else ""
        except Exception as e:
            print(f"Error getting Instagram access token: {e}")
            return ""

    def set_instagram_access_token(self, token):
        """Sets the Instagram access token in the Google Sheet."""
        try:
            worksheet = self._get_worksheet()
            layout = self._resolve_layout(worksheet)
            worksheet.update_cell(1, layout.token_col_index, token)
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
                print(f"Row: {conf.row_num}, Timestamp: {conf.timestamp}, Text: {conf.text[:50]}...")

            if latest_confessions:
                first_conf = latest_confessions[0]
                reader.mark_confession_as_processed(first_conf.row_num, 1)

        except Exception as e:
            print(f"An error occurred: {e}")
