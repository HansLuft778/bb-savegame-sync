import os
import time
from typing import Dict, Optional, Union
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from utils import SaveResult


def save_from_web(save_to_disk: bool = True) -> Optional[Dict[str, Union[str, bytes]]]:
    """
    Launches the Bitburner web game, exports the save file, and optionally saves to disk.

    Args:
        save_to_disk (bool): Whether to save the data to disk. Defaults to True.

    Returns:
        dict or None: Returns a dict with save data if successful, otherwise None.
                     The dict contains 'fileName' and 'save' keys.
                     If save_to_disk is True, the file is also saved to disk.
    """
    raise NotImplementedError(
        "Extracting saves from the browser-based version does not work yet"
    )

    download_path = os.getcwd()
    print(f"Starting web save process...")
    print(f"Download directory set to: {download_path}")

    options = Options()
    options.binary_location = "path/to/browser.exe"
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--log-level=3")
    options.add_argument("--user-data-dir=path/to/User Data")
    # options.add_argument("--headless")

    prefs = {
        "download.default_directory": download_path,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
    }
    options.add_experimental_option("prefs", prefs)

    driver = None
    try:
        print("Launching browser and navigating to Bitburner...")
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.get("https://bitburner-official.github.io/")

        print("Waiting for the game's UI to be rendered...")
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.ID, "terminal-input"))
        )
        print("Game UI is ready.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        return None
    finally:
        if driver:
            print("Closing browser.")
            driver.quit()


def save_from_electron(
    save_to_disk: bool = True,
) -> Optional[SaveResult]:
    """
    Connects to a running Bitburner Electron instance and exports the save file.
    NOTE: The Electron game must be launched with the --remote-debugging-port=9222 flag.

    Args:
        save_to_disk (bool): Whether to save the data to disk. Defaults to True.

    Returns:
        dict or None: Returns a dict with save data if successful, otherwise None.
                     The dict contains 'fileName' and 'save' keys.
                     If save_to_disk is True, the file is also saved to disk.
    """
    print("Starting Electron save process...")
    debugger_address = "127.0.0.1:9222"
    chrome_options = Options()
    chrome_options.debugger_address = debugger_address

    driver = None
    try:
        print(f"Connecting to Bitburner instance at {debugger_address}...")

        # manually load chromedriver version 122
        chromedriver_path = os.path.join(
            os.getcwd(), "chromedriver-win64", "chromedriver.exe"
        )
        service = ChromeService(executable_path=chromedriver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        print("Connected to Bitburner.")

        # This script calls getSaveData() which returns a promise.
        # execute_async_script waits for the promise to resolve by using the callback.
        script = """
            const callback = arguments[arguments.length - 1];
            if (typeof window.appSaveFns !== 'undefined' && 
                typeof window.appSaveFns.getSaveData === 'function') {
                
                window.appSaveFns.getSaveData()
                    .then(result => callback({status: 'success', data: result}))
                    .catch(error => callback({status: 'error', message: error.message}));
            } else {
                callback({status: 'error', message: 'getSaveData function not found. Is this the Electron version?'});
            }
        """
        print("Executing Export Script...")
        result = driver.execute_async_script(script)
        print("done")

        if result and result.get("status") == "success":
            save_data_obj = result.get("data", {})
            file_name = save_data_obj.get("fileName")
            save_content = save_data_obj.get("save")

            if not file_name or save_content is None:
                print(
                    "Error: Could not retrieve valid save data or filename from the game."
                )
                return None

            if save_to_disk:
                file_path = os.path.join(os.getcwd(), file_name)
                print(f"Saving game to: {file_path}")

                with open(file_path, "wb") as f:
                    f.write(bytes(save_content))

                print("Save game exported successfully!")

            return save_data_obj

        else:
            error_message = result.get("message", "An unknown error occurred.")
            print(f"Failed to export save game: {error_message}")
            return None

    except Exception as e:
        print(f"An error occurred: {e}")
        print(
            "Please ensure the Bitburner Electron app is running with the flag: --remote-debugging-port=9222"
        )
        return None

    finally:
        if driver:
            driver.quit()
