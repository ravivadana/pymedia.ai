import re
from pathlib import Path
import unicodedata


class FolderSanitizer:
    MAX_FILENAME_LENGTH = 50  # max safe length

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        # Normalize unicode
        filename = unicodedata.normalize('NFKD', filename).encode('ascii', 'ignore').decode('ascii')
        # Replace unsafe chars with underscore
        sanitized = re.sub(r'[^a-zA-Z0-9\-_.]+', '_', filename)
        sanitized = re.sub(r'_+', '_', sanitized).strip("_.")
        # Limit length
        if len(sanitized) > FolderSanitizer.MAX_FILENAME_LENGTH:
            base, ext = Path(sanitized).stem[:FolderSanitizer.MAX_FILENAME_LENGTH], Path(sanitized).suffix
            sanitized = f"{base}{ext}"
        return sanitized or "file"

    @classmethod
    def sanitize_folder(cls, folder: str):
        folder_path = Path(folder)
        if not folder_path.exists() or not folder_path.is_dir():
            raise ValueError(f"Folder does not exist: {folder}")

        existing_names = set(f.name for f in folder_path.iterdir() if f.is_file())

        sanitized_files = []
        for f in folder_path.iterdir():
            if not f.is_file():
                continue

            new_name = cls.sanitize_filename(f.name)

            # Handle collisions
            counter = 1
            base, ext = Path(new_name).stem, Path(new_name).suffix
            while new_name in existing_names:
                suffix = f"_{counter}"
                trim_len = cls.MAX_FILENAME_LENGTH - len(suffix) - len(ext)
                new_name = f"{base[:trim_len]}{suffix}{ext}"
                counter += 1

            new_path = folder_path / new_name
            try:
                if f != new_path:
                    f.rename(new_path)
                    existing_names.add(new_name)
            except Exception as e:
                print(f"Failed to rename {f.name}: {e}")
            sanitized_files.append(new_path)
        return sorted(sanitized_files)