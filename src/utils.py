import cloudinary
import cloudinary.api
from cloudinary.exceptions import Error
import os
import time

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

def delete_all_cloudinary_assets():
    """
    Deletes all assets (images, videos, raw files) from your Cloudinary account.
    WARNING: This action is irreversible. All assets will be permanently deleted.
    """
    print("WARNING: This will permanently delete ALL assets from your Cloudinary account.")
    print("Please ensure you have backups if needed.")

    resource_types = ['image', 'video', 'raw'] # Add or remove types as needed

    for r_type in resource_types:
        print(f"\n--- Deleting {r_type.upper()} resources ---")
        next_cursor = None
        has_more = True
        total_deleted = 0

        while has_more:
            try:
                # Use list_resources to get a batch of resource IDs
                # max_results can be up to 500
                response = cloudinary.api.resources(
                    type="upload", # 'upload', 'private', 'authenticated'
                    resource_type=r_type,
                    max_results=500,
                    next_cursor=next_cursor
                )

                resources = response.get('resources', [])
                if not resources:
                    print(f"No more {r_type} resources found.")
                    has_more = False
                    continue

                public_ids = [res['public_id'] for res in resources]

                if public_ids:
                    print(f"Found {len(public_ids)} {r_type} resources to delete. Deleting...")
                    # Delete the resources
                    delete_result = cloudinary.api.delete_resources(
                        public_ids,
                        resource_type=r_type,
                        invalidate=True # Invalidate CDN cache for these assets
                    )
                    total_deleted += len(public_ids)
                    print(f"Deletion status for current batch: {delete_result}")
                else:
                    print(f"No {r_type} public IDs to delete in this batch.")

                next_cursor = response.get('next_cursor')
                if not next_cursor:
                    has_more = False
                    print(f"Finished processing all {r_type} resources.")
                else:
                    print(f"Proceeding to next batch of {r_type} resources...")
                    # Small delay to respect API rate limits, especially for very large accounts
                    time.sleep(1)

            except Error as e:
                print(f"Cloudinary API Error while deleting {r_type}: {e}")
                has_more = False # Stop on error
            except Exception as e:
                print(f"An unexpected error occurred while deleting {r_type}: {e}")
                has_more = False # Stop on error

        print(f"--- Total {r_type.upper()} resources deleted: {total_deleted} ---")

    print("\n--- All specified resource types have been processed. ---")
    print("It may take some time for changes to propagate and for CDN caches to clear.")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    delete_all_cloudinary_assets()