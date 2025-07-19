import os
import paramiko
from typing import Optional
from io import BytesIO
from CloudModel import CloudModel
from savegame import Savegame
from utils import get_time_from_save_file


class SFTPCloudServer(CloudModel):
    """
    CloudModel implementation using SFTP for network drive access.

    Supports both password and key-based authentication.
    """

    def __init__(
        self,
        hostname: str,
        username: str,
        password: Optional[str] = None,
        private_key_path: Optional[str] = None,
        port: int = 22,
        remote_path: str = "/bitburner_saves",
    ):
        """
        Initialize SFTP connection parameters.

        Args:
            hostname: SFTP server hostname or IP
            username: Username for authentication
            password: Password (if using password auth)
            private_key_path: Path to private key file (if using key auth)
            port: SSH port (default 22)
            remote_path: Remote directory path for save files
        """
        super().__init__()
        self.hostname = hostname
        self.username = username
        self.password = password
        self.private_key_path = private_key_path
        self.port = port
        self.remote_path = remote_path

    def _get_sftp_client(self) -> tuple[paramiko.SFTPClient, paramiko.SSHClient]:
        """Create and return an SFTP client connection with SSH client."""
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        if self.private_key_path:
            # key-based authentication
            private_key = paramiko.RSAKey.from_private_key_file(self.private_key_path)
            ssh.connect(
                self.hostname, port=self.port, username=self.username, pkey=private_key
            )
        else:
            # password-based authentication
            ssh.connect(
                self.hostname,
                port=self.port,
                username=self.username,
                password=self.password,
            )

        sftp = ssh.open_sftp()
        return sftp, ssh

    def _ensure_remote_directory(self, sftp: paramiko.SFTPClient):
        try:
            sftp.stat(self.remote_path)
        except FileNotFoundError:
            # directory does not exist, create it
            try:
                sftp.mkdir(self.remote_path)
                print(f"Created remote directory: {self.remote_path}")
            except Exception as e:
                print(f"Failed to create remote directory {self.remote_path}: {e}")
                raise

    def upload_save(self, save: Savegame):
        """
        Upload a save file to the SFTP server.

        Args:
            save: Savegame object to upload
        """
        remote_file_path = os.path.join(self.remote_path, save.file_name).replace(
            "\\", "/"
        )

        sftp = None
        ssh = None
        try:
            sftp, ssh = self._get_sftp_client()
            self._ensure_remote_directory(sftp)

            print(f"Uploading save to SFTP: {self.hostname}:{remote_file_path}")

            save_bytes = bytes(save.save_data_bytes)
            with BytesIO(save_bytes) as file_obj:
                sftp.putfo(file_obj, remote_file_path)

            print(f"Successfully uploaded {save.file_name} ({len(save_bytes)} bytes)")

        except Exception as e:
            print(f"Failed to upload save file: {e}")
            raise
        finally:
            if sftp:
                sftp.close()
            if ssh:
                ssh.close()

    def get_latest_save(self) -> Optional[Savegame]:
        """
        Retrieve the latest save file from the SFTP server.

        Returns:
            Savegame object, or None if no saves found
        """
        sftp = None
        ssh = None
        try:
            sftp, ssh = self._get_sftp_client()

            # get files from remote directory
            try:
                files = sftp.listdir(self.remote_path)
            except FileNotFoundError:
                print(f"Remote directory {self.remote_path} not found.")
                return None

            save_files = [
                f
                for f in files
                if f.startswith("bitburnerSave_") and f.endswith(".json.gz")
            ]

            if not save_files:
                print("No Bitburner save files found on SFTP server.")
                return None

            # filter latest save
            latest_file_name = max(save_files, key=lambda f: get_time_from_save_file(f))
            remote_file_path = os.path.join(self.remote_path, latest_file_name).replace(
                "\\", "/"
            )

            print(f"Downloading latest save: {latest_file_name}")

            with BytesIO() as file_obj:
                sftp.getfo(remote_file_path, file_obj)
                file_content = file_obj.getvalue()

            # Create Savegame object from downloaded data
            save_content = list(file_content)
            save_result = {"fileName": latest_file_name, "save": save_content}
            savegame = Savegame(save_result)

            print(
                f"Successfully downloaded {latest_file_name} ({len(save_content)} bytes)"
            )
            return savegame

        except Exception as e:
            print(f"Failed to retrieve latest save: {e}")
            return None
        finally:
            if sftp:
                sftp.close()
            if ssh:
                ssh.close()
