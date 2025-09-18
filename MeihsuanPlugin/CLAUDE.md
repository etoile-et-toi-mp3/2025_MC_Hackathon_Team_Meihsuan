# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Loupedeck plugin** called "MeihsuanPlugin" that provides smart screenshot functionality. It's a C# .NET 8.0 project that integrates with the Loupedeck/Logi Plugin Service ecosystem to create custom controls for Loupedeck devices.

## Architecture

### Core Components

- **MeihsuanPlugin.cs**: Main plugin class that inherits from `Plugin`. This is an API-only plugin (`UsesApplicationApiOnly = true`) that doesn't tie to a specific application (`HasNoApplication = true`).
- **MeihsuanApplication.cs**: ClientApplication implementation (currently minimal/placeholder).
- **SmartScreenShot.cs**: Contains the main functionality including:
  - `PythonHelper`: Static class for executing Python scripts and parsing JSON responses
  - `PythonResponse`: Data model for Python script results
  - `SmartScreenshotAction`: Main plugin command (currently commented out/in development)

### Python Integration

The plugin integrates with Python scripts located in `src/python_scripts/`:
- **history_checker.py**: Returns mock data for window/application history
- Python scripts are executed via `PythonHelper.RunScript()` and return JSON data

### Directory Structure

```
src/
├── Actions/           # Plugin commands and adjustments
├── Helpers/          # Utility classes (PluginLog, PluginResources)
├── python_scripts/   # Python integration scripts
├── MeihsuanPlugin.cs # Main plugin class
├── MeihsuanApplication.cs
└── SmartScreenShot.cs # Core functionality
```

## Development Commands

### Build Commands
```bash
# Debug build
dotnet build -c Debug

# Release build
dotnet build -c Release
```

### Plugin Management (via logiplugintool)
```bash
# Package the plugin
logiplugintool pack ./bin/Release ./Meihsuan.lplug4

# Install plugin
logiplugintool install ./Meihsuan.lplug4

# Uninstall plugin
logiplugintool uninstall Meihsuan
```

### Development Workflow

The project uses automatic plugin reloading during development:
- Building creates a `.link` file in the Logi Plugin Service directory
- Automatically sends reload command to the service
- On macOS: Uses `open loupedeck:plugin/Meihsuan/reload`
- On Windows: Uses `start loupedeck:plugin/Meihsuan/reload`

## Key Configuration

- **Target Framework**: .NET 8.0
- **Plugin API**: References `PluginApi.dll` from Logi Plugin Service installation
- **External Dependencies**: Newtonsoft.Json for JSON serialization
- **Plugin Name**: "Meihsuan" (configured in `PluginShortName`)
- **Namespace**: `Loupedeck.MeihsuanPlugin`

## Python Environment

The plugin expects Python to be available as `python.exe` and copies Python scripts to the output directory during build. Python scripts should return JSON arrays of `PythonResponse` objects with properties: `success`, `name`, `processName`, `windowTitle`, and `error`.