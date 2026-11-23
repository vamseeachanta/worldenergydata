import os
import json
import time
import logging
from pathlib import Path
from datetime import datetime

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
SOURCE_DIR = "worldenergydata/data/raw/legacy_production/source"
OUTPUT_FILE = "worldenergydata/data/modules/bsee/legacy/production_inventory.json"

# Interesting file types for production data
DATA_EXTENSIONS = {
    ".xlsx": "Excel",
    ".xls": "Excel_Legacy",
    ".csv": "CSV",
    ".las": "Well_Log",
    ".pptx": "Presentation"  # Often contains summary tables
}

def scan_production_data(root_path):
    logger.info(f"Scanning production data in: {root_path}")
    inventory = []
    stats = {k: 0 for k in DATA_EXTENSIONS.values()}
    stats["Other"] = 0
    
    start_time = time.time()
    
    # Resolve symlink if needed
    real_path = os.path.realpath(root_path)
    logger.info(f"Resolving to: {real_path}")
    
    for root, _, files in os.walk(real_path):
        for file in files:
            file_path = Path(root) / file
            ext = file_path.suffix.lower()
            
            file_type = DATA_EXTENSIONS.get(ext, "Other")
            
            # We are primarily interested in data files, but we'll count others
            if file_type != "Other":
                stats[file_type] += 1
                
                try:
                    stat = file_path.stat()
                    item = {
                        "name": file,
                        "rel_path": str(file_path.relative_to(real_path)),
                        "full_path": str(file_path),
                        "type": file_type,
                        "size_bytes": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                    }
                    inventory.append(item)
                except Exception as e:
                    logger.error(f"Error processing {file}: {e}")
            else:
                stats["Other"] += 1

    duration = time.time() - start_time
    logger.info(f"Scan complete in {duration:.2f} seconds.")
    
    print("\nFile Statistics:")
    for ftype, count in stats.items():
        print(f"  {ftype}: {count}")
        
    return inventory

def main():
    inventory = scan_production_data(SOURCE_DIR)
    
    # Ensure output dir exists
    Path(OUTPUT_FILE).parent.mkdir(parents=True, exist_ok=True)
    
    with open(OUTPUT_FILE, "w") as f:
        json.dump(inventory, f, indent=2)
        
    logger.info(f"Inventory saved to {OUTPUT_FILE} with {len(inventory)} items.")

if __name__ == "__main__":
    main()
