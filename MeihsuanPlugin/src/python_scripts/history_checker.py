import sys
import json

def get_history():
    
    result = [
        {
            "success": True,
            "name": "Slack #general",
            "processName": "slack",
            "windowTitle": "#general"
        },
        {
            "success": True,
            "name": "Google Meet",
            "processName": "chrome",
            "windowTitle": "Google Meet"
        },
        {
            "success": True,
            "name": "VS Code",
            "processName": "Code",
            "windowTitle": "ExamplePlugin"
        },
        {
            "success": False,
            "name": "Notepad (Test)",
            "processName": "notepad",
            "windowTitle": "Untitled"
        }
    ]
    
    return result

if __name__ == "__main__":
    history= get_history()
    print(json.dumps(history))