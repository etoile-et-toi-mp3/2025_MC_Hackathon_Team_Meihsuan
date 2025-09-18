import sys
import json
import platform
import pywinctl as pwc

if __name__ == "__main__":
    apps = pwc.getAllTitles()
    print(apps)
    print(json.dumps(apps))