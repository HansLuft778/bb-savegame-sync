# Bitburner Savegame Sync

Since there seems to be some interest in a tool to sync savefiles across devices, I gave it a shot. This is a very early prototype I hacked together in a day or two, so it's not heavily tested, but given some limitations, seems to work in general.

One goal was to automate the process of getting the savefile in and out of Bitburner automatically, which proved to be more difficult than I thought. Especially the browser version (since Steam has Steam save sync, this is probably what most need this for).

## Features

- **Storage Options**:
  - Sync to any local filesystem folder (e.g., external hard drives, USB drives, network drives)
  - Sync to SFTP servers for remote storage
- Works with both web browser and Electron/Steam versions of Bitburner
- Compares savefiles based on last saved timestamp to determine which save is newer (not sure if this is optimal, probably not)
- Automated Export/Import for the Electron version with Chrome debugging enabled

## Requirements

- Python 3.8+ (tested on Python 3.13)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/HansLuft778/bb-savegame-sync
   cd bb-savegame-sync
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

Stil a somewhat manual process and requires some small codechanges.

### Local Filesystem Storage (Default)

By default, the tool uses local filesystem storage. Files are saved to the `savegames/` folder in the project directory. No additional configuration required.

### SFTP Server Storage
SFTP can be authenticated password or key based. When using a SSH-key, key authentication is infered, when not providing a key, the password is needed.

To use SFTP storage, edit `saveSync.py`:

1. Uncomment the SFTP configuration block (lines ~128-136):
   ```python
   SFTP_CONFIG = { ... }
   model = SFTPCloudServer(**SFTP_CONFIG)
   ```

2. Comment out the LocalSaveServer line:
   ```python
   # model = LocalSaveServer(os.path.join(os.getcwd(), "savegames"))
   ```

## Usage

The tool has two main modes:
- `app` - For Electron/Steam version of Bitburner
- `web` - For web browser version of Bitburner

Note: Both modes can be combined freely, for example, you can have the electron build on device 1 and the browser version on device 2.

### General Help
```bash
python saveSync.py --help
python saveSync.py app --help
python saveSync.py web --help
```

### Web Browser Version

For the web version, you need to manually export saves from Bitburner:

1. Export your savegame from Bitburner (Options -> Export Game)
2. Save the file to the project directory
3. Run the sync command:

```bash
python saveSync.py web --save-file ./bitburnerSave_1752885714_BN3x2.json.gz
```

**Example workflow:**
```bash
# Device 1: Upload your current save to cloud storage
python saveSync.py web --save-file ./device_1_save.json.gz

# Device 2: Download and update with the latest cloud save
python saveSync.py web --save-file ./device_2_save.json.gz
```

### Electron/Steam Version

For the Electron version, you have two options:

#### Manual Mode (same as for web version)
```bash
python saveSync.py app --save-file ./path/to/save.json.gz
```

#### Automatic Mode (Recommended)
For automatic export/import, launch Bitburner with Chrome debugging enabled:

1. Start Bitburner with debugging:
   Execute Bitburner in debug mode by using the following flag:
   `--remote-debugging-port=9222`

2. Run the sync tool:
   ```bash
   python saveSync.py app --auto
   ```

## Limitations

- Web Version Requires manual export/import of saves
- Electron Automation requires Chrome debugging port to be enabled
- Command-line interface only
- very basic conflict resolution 

## Contributing

This is an early prototype. Issues, suggestions, and pull requests are welcome. (Especially if you need more storage options like Google Drive, S3, ...)

## Disclaimer

Even tho this tool does not delete any files or modifies the save file directly, data loss may occur!
