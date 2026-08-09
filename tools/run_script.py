import asyncio
import sys
import os

# Ensure the project root is in the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.populate_metadata import populate_metadata

async def main():
    """
    Script runner to execute standalone tasks within the application context.
    """
    if len(sys.argv) < 2:
        print("Usage: python run_script.py <script_name>")
        print("Available scripts: populate_metadata")
        return

    script_name = sys.argv[1]

    if script_name == "populate_metadata":
        print("Starting metadata population...")
        try:
            await populate_metadata()
            print("Metadata population complete.")
        except Exception as e:
            print(f"An error occurred during metadata population: {e}")
    else:
        print(f"Unknown script: {script_name}")

if __name__ == "__main__":
    asyncio.run(main())
