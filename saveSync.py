import argparse
import os
import time
import re

from CloudModel import CloudModel
from export_game import save_from_electron
from import_game import import_save_game
from models.localServer import LocalSaveServer
from models.sftpServer import SFTPCloudServer
from savegame import Savegame
from typing import Optional


def update_save_file_timestamp(path: str):
    new_time = int(time.time())
    return re.sub(r"(\d+)(?!.*\d)", str(new_time), path)


def replace_unix_timestamp(file_name: str, new_timestamp: int) -> str:
    if not isinstance(new_timestamp, int) or not (1e9 <= new_timestamp < 10e9):
        raise ValueError(
            f"new_timestamp must be a 10-digit integer, got: {new_timestamp}"
        )

    # Replace the 10-digit number not surrounded by digits
    new_file_name, count = re.subn(
        r"(?<!\d)(\d{10})(?!\d)", str(new_timestamp), file_name
    )

    if count == 0:
        raise ValueError(f"no unix timestamp in file name found: {file_name}")

    return new_file_name


def get_local_save(args) -> Optional[Savegame]:
    if args.command == "app" and args.auto:
        save_result = save_from_electron()
        if save_result:
            return Savegame(save_result)
        return None
    elif (args.command == "app" and not args.auto) or args.command == "web":
        return Savegame.from_file(args.save_file)
    else:
        raise ValueError("Invalid command")


def set_local_save(args, cloud_save: Savegame):
    """Set local save from cloud save."""
    if args.command == "app" and args.auto:
        import_save_game(cloud_save.to_save_result())
        print("Successfully imported save game directly into Bitburner")
        return

    if (args.command == "app" and not args.auto) or args.command == "web":
        new_save_path = replace_unix_timestamp(args.save_file, int(time.time()))
        cloud_save.save_to_file(new_save_path)
    else:
        raise ValueError("Invalid command")
    print(
        f"Successfully saved savegame to {new_save_path}. Now you need to import it in Bitburner (Options -> Import Game)"
    )


def main(args, cloud_model: CloudModel):
    print("Retreiving local save from Bitburner")
    local_save = get_local_save(args)
    assert local_save is not None
    local_time = local_save.progression_timestamp

    print("Retreiving latest save from server...")
    cloud_save = cloud_model.get_latest_save()
    if cloud_save:
        cloud_time = cloud_save.progression_timestamp
    else:
        cloud_time = 0  # No cloud save exists

    print(
        f"Local save: {local_save.file_name} (timestamp: {local_save.last_save_readable})"
    )
    if cloud_save:
        print(
            f"Cloud save: {cloud_save.file_name} (timestamp: {cloud_save.last_save_readable})"
        )
    else:
        print("Cloud save: No cloud save found")

    # compare local save with cloud save using Savegame comparison
    if local_time > cloud_time:
        print("Local save is newer, uploading...")
        cloud_model.upload_save(local_save)
    elif local_time < cloud_time and cloud_save is not None:
        print("Cloud save is newer, updating...")
        set_local_save(args, cloud_save)
    else:
        print("Saves are equal according to lastSave timestamp, nothing to do.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bitburner Save Sync")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # app command
    app_parser = subparsers.add_parser("app", help="Use electron/steam version")
    app_parser.add_argument(
        "--auto",
        action="store_true",
        help="Automatically export from running Bitburner (requires to launch Bitburner using --remote-debugging-port=9222)",
    )
    app_parser.add_argument(
        "--save-file",
        type=str,
        dest="save_file",
        help="Path to the local Bitburner save file (required when not using --auto)",
    )

    # browser command
    web_parser = subparsers.add_parser("web", help="Use web version")
    web_parser.add_argument(
        "--save-file",
        type=str,
        dest="save_file",
        required=True,
        help="Path to the local Bitburner save file",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        exit(1)

    if args.command == "app" and not args.auto and not args.save_file:
        parser.error("--save-file is required when using 'app' without --auto")

    if args.command == "web" and not args.save_file:
        parser.error("--save-file is required when using 'web'")

    # Uncomment these lines if you wnat to use SFTP
    # SFTP_CONFIG = {
    #     "hostname": "url-to-server.com",  # SFTP server hostname or IP
    #     "username": "username",  # SSH username
    #     "password": "password",  # SSH password (None if using key)
    #     "private_key_path": None,  # path to SSH private key (None if using password)
    #     "port": 22,  # SSH port (default is 22)
    #     "remote_path": "/bitburner_saves",  # remote directory for saves
    # }
    # model = SFTPCloudModel(**SFTP_CONFIG)

    # and comment this in, so this one is deactivated
    model = LocalSaveServer(os.path.join(os.getcwd(), "savegames"))

    main(args, model)
