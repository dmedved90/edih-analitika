"""
Configuration validation script
Run before deployment to check all settings
"""
import sys
from config import config
from logger import get_logger
import os

logger = get_logger()

def test_config():
    """Test configuration"""
    print("=" * 50)
    print("EDIH Analytics - Configuration Test")
    print("=" * 50)
    
    errors = config.validate()
    
    if errors:
        print("\n❌ Configuration Errors:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    print("\n✅ Configuration Valid")
    
    # Check paths
    print("\n📁 Path Validation:")
    paths_to_check = [
        ("App Folder", config.APP_FOLDER),
        ("Data Folder", config.DATA_FOLDER),
        ("Images Folder", config.IMAGES_FOLDER),
    ]
    
    all_paths_exist = True
    for name, path in paths_to_check:
        exists = os.path.exists(path)
        status = "✅" if exists else "❌"
        print(f"  {status} {name}: {path}")
        if not exists:
            all_paths_exist = False
    
    # Check data files
    print("\n📄 Data Files:")
    files_to_check = [
        ("Services", config.FILE_SERVICES),
        ("SME", config.FILE_SME),
        ("PSO", config.FILE_PSO),
    ]
    
    all_files_exist = True
    for name, path in files_to_check:
        exists = os.path.exists(path)
        status = "✅" if exists else "❌"
        print(f"  {status} {name}: {path}")
        if not exists:
            all_files_exist = False
    
    # Check API keys (masked)
    print("\n🔑 API Keys:")
    api_keys = [
        ("OpenAI", config.OPENAI_API_KEY),
        ("DeepSeek", config.DEEPSEEK_API_KEY),
    ]
    
    all_keys_present = True
    for name, key in api_keys:
        present = bool(key and len(key) > 10)
        status = "✅" if present else "❌"
        masked = f"{key[:8]}..." if present else "Not set"
        print(f"  {status} {name}: {masked}")
        if not present:
            all_keys_present = False
    
    # Summary
    print("\n" + "=" * 50)
    if all_paths_exist and all_files_exist and all_keys_present:
        print("✅ All checks passed - Ready for deployment!")
        return True
    else:
        print("❌ Some checks failed - Fix issues before deployment")
        return False

if __name__ == "__main__":
    success = test_config()
    sys.exit(0 if success else 1)
