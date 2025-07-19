import argparse
import glob
import os
import time
import gzip
import base64
from typing import Union, Dict
from utils import SaveResult

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def get_driver(target: str):
    """Initializes a robust Chrome driver for the specified target."""
    chrome_options = Options()
    if target == "electron":
        chrome_options.debugger_address = "127.0.0.1:9222"
        # Manually specify the path to chromedriver.exe for the Electron app
        chromedriver_path = os.path.join(
            os.getcwd(), "chromedriver-win64", "chromedriver.exe"
        )
        service = ChromeService(executable_path=chromedriver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        print("Connected to Bitburner")
        return driver

    raise NotImplementedError(
        "Importing saves to the browser-based version does not work yet"
    )
    service = ChromeService(ChromeDriverManager(driver_version="122").install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    print("Navigating to Bitburner (Web)...")
    driver.get("https://bitburner-official.github.io/")

    try:
        print("Waiting for game UI to be ready (max 60s)...")
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "terminal-input"))
        )

        print("Terminal UI is visible")
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script(
                "return typeof window.saveObject !== 'undefined' && "
                "typeof window.saveObject.importGame === 'function'"
            )
        )
        print("window.saveObject.importGame is ready")

    except TimeoutException as e:
        print(
            f"Error: Game did not fully load or window.saveObject.importGame was not found in time. Details: {e}"
        )
        driver.quit()
        raise
    except Exception as e:
        print(f"An unexpected error occurred during setup: {e}")
        driver.quit()
        raise

    return driver


def import_save_game(save: SaveResult):
    driver = None
    try:
        driver = get_driver("electron")

        # Read the save file content as binary and base64 encode it
        gzipped_content = save.get("save")
        assert isinstance(
            gzipped_content, list
        ), f"save_content is of type {type(gzipped_content)}"

        # Base64 encode the gzipped content and then decode to a UTF-8 string
        save_content = base64.b64encode(bytes(gzipped_content)).decode("utf-8")

        print("Executing window.appSaveFns.pushSaveData...")
        result = driver.execute_async_script(
            """
            const callback = arguments[arguments.length - 1];
            const saveDataBase64 = arguments[0];

            if (typeof window.appSaveFns === 'undefined' || typeof window.appSaveFns.pushSaveData === 'undefined') {
                callback({status: 'error', message: 'window.appSaveFns.pushSaveData function not found.'});
                return;
            }

            try {
                // Decode base64 string to a Uint8Array
                const binaryString = atob(saveDataBase64);
                const bytes = new Uint8Array(binaryString.length);
                for (let i = 0; i < binaryString.length; i++) {
                    bytes[i] = binaryString.charCodeAt(i);
                }

                window.appSaveFns.pushSaveData(bytes, false); // not automatic to mimic manual import, not sure what the implications of automatic are
                callback({status: 'success', message: 'Import process initiated.'});
            } catch (error) {
                console.error('JS: Error during base64 decode or pushSaveData:', error);
                callback({status: 'error', message: 'Error decoding or pushing save data: ' + error.message});
            }
            """,
            save_content,
        )

        if result and result.get("status") == "success":
            print(f"Successfully initiated save game import: {result.get('message')}")
            print("Please confirm the import within the Bitburner game window.")
        else:
            error_message = result.get("message", "An unknown error occurred.")
            print(f"Failed to import save game: {error_message}")

        # After sending the file, the game will likely show a confirmation modal.
        # We need to wait for this modal and confirm it.
        print("Waiting for import confirmation modal...")
        confirm_button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(., 'Proceed with import')]")
            )
        )
        confirm_button.click()
        print("Import confirmed. Game should now reload.")

        # Give some time for the game to reload after import
        time.sleep(5)

    except Exception as e:
        print(f"An unexpected error occurred during import: {e}")

    finally:
        if driver:
            if "electron" == "web":
                input("\nPress Enter to close the browser...")
            driver.quit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import Bitburner save game.")
    parser.add_argument(
        "target", choices=["electron", "web"], help="Target environment."
    )
    args = parser.parse_args()
    import_save_game(args.target)
