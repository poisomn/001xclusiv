import os
import json
import glob
from pathlib import Path

history_dir = r"C:\Users\chris\AppData\Roaming\Code\User\History"
search_files = ["home.html", "styles.css", "product_list.html", "product-card.css"]

results = []

for entry_file in glob.glob(os.path.join(history_dir, "*", "entries.json")):
    try:
        with open(entry_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        if 'resource' in data:
            resource = data['resource']
            for sf in search_files:
                if sf in resource:
                    folder = os.path.dirname(entry_file)
                    entries = data.get('entries', [])
                    if entries:
                        latest_entry = entries[-1]
                        latest_file = os.path.join(folder, latest_entry['id'])
                        timestamp = latest_entry.get('timestamp', 0)
                        
                        results.append({
                            'original_file': resource,
                            'backup_file': latest_file,
                            'timestamp': timestamp
                        })
    except Exception as e:
        pass

# Sort by timestamp descending
results.sort(key=lambda x: x['timestamp'], reverse=True)

print("FOUND RECENT BACKUPS:")
for res in results[:20]:
    print(f"Original: {res['original_file']}")
    print(f"Backup: {res['backup_file']}")
    print(f"Timestamp: {res['timestamp']}")
    print("---")
