import os
import json
import time
import logging
import argparse
from pathlib import Path
from datetime import datetime

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
SOURCE_DIR = "worldenergydata/data/raw/legacy_safety/source"
OUTPUT_FILE = "worldenergydata/data/legacy_safety_inventory.json"

# Interesting file types for safety/integrity data
DATA_EXTENSIONS = {
    ".pdf": "Report_PDF",
    ".docx": "Report_Word",
    ".doc": "Report_Word_Legacy",
    ".xlsx": "Data_Excel",
    ".xls": "Data_Excel_Legacy",
    ".txt": "Log_Text"
}

def scan_safety_data(root_path: str) -> list:
    logger.info(f"Scanning safety data in: {root_path}")
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
    parser = argparse.ArgumentParser(description="Inventory legacy safety data.")
    parser.add_argument("--source", default=SOURCE_DIR, help="Source directory to scan")
    parser.add_argument("--output", default=OUTPUT_FILE, help="Output JSON file")
    args = parser.parse_args()
    
    inventory = scan_safety_data(args.source)
    
    # Ensure output dir exists
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    
    with open(args.output, "w") as f:
        json.dump(inventory, f, indent=2)
        
    logger.info(f"Inventory saved to {args.output} with {len(inventory)} items.")

if __name__ == "__main__":
    main()
