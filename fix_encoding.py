import os

def convert_utf16_to_utf8(file_path):
    # Create a backup of the original file
    backup_path = file_path + '.bak'
    if not os.path.exists(backup_path):
        with open(file_path, 'rb') as src:
            with open(backup_path, 'wb') as dst:
                dst.write(src.read())
        print(f"Backup created at {backup_path}")
    
    try:
        # Read the file as UTF-16
        with open(file_path, 'r', encoding='utf-16') as f:
            content = f.read()
        
        # Write the file as UTF-8
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Successfully converted {file_path} from UTF-16 to UTF-8")
        return True
    except Exception as e:
        print(f"Error converting file: {e}")
        return False

if __name__ == "__main__":
    file_path = r"d:\CodeAnalzyer\Test.py"
    convert_utf16_to_utf8(file_path)
