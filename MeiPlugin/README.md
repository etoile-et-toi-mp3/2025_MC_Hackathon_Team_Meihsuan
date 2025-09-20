# MeiPlugin - Command Documentation

This directory contains a collection of commands that integrate C# Loupedeck plugin actions with Python implementations for various interactive utilities.

## Project Structure

```
MeiPlugin/
├── src/
│   └── Actions/
│       ├── *.cs                # C# Loupedeck plugin commands
│       │   ├── BoxingCommand.cs
│       │   ├── BrightnessCommand.cs
│       │   ├── MeetingPresentDetection.cs
│       │   ├── RecordWithMarksCommand.cs
│       │   ├── ScrrenShotToLatex.cs
│       │   ├── SmartScreenShot.cs
│       └── python_scripts/     # Python command implementations
│       │   ├── boxing.py
│       │   ├── brightness.py
│       │   ├── call_paste_target.py
│       │   ├── fixed_meeting.py
│       │   ├── rec.py
│       │   └── virtual_touchpad.py
├── .vscode/                    # VS Code configuration
└── MeiPlugin.sln              # Solution file
```

## Available Commands

### 1. Boxing Game
**C# Command**: `BoxingCommand.cs` | **Python Implementation**: `boxing.py`

**Purpose**: Interactive hand gesture-controlled boxing game using computer vision
- **C# Function**: Launches Python boxing game via process execution
- **Python Function**: Real-time hand tracking with MediaPipe, gesture-based boxing mechanics, sound effects
- **Dependencies**: `opencv-python`, `mediapipe`, `numpy`, `pygame`

### 2. Auto Brightness Control
**C# Command**: `BrightnessCommand.cs` | **Python Implementation**: `brightness.py`

**Purpose**: Automatically adjusts screen brightness based on environment lighting
- **C# Function**: Toggle start/stop brightness monitoring process with state management
- **Python Function**: Webcam-based ambient light detection, dynamic brightness adjustment (10-100%)
- **Dependencies**: `opencv-python`, `numpy`, `screen-brightness-control`

### 3. Smart Paste System
**C# Command**: `SmartScreenShot.cs` | **Python Implementation**: `call_paste_target.py`

**Purpose**: Intelligent window switching and paste utility
- **C# Function**: Launches smart paste tool via Python process
- **Python Function**: Window detection, automatic switching, smart click positioning, modern dark-themed GUI
- **Dependencies**: `pyautogui`, `pywinctl`, `customtkinter`, `pygetwindow`

### 4. Meeting Control System
**C# Command**: `MeetingPresentDetection.cs` | **Python Implementation**: `fixed_meeting.py`

**Purpose**: Automated meeting controls with face detection for video conferencing
- **C# Function**: Launches meeting control with OBS integration and configurable parameters
- **Python Function**:
  - Platform support (Google Meet, Zoom) with keyboard shortcuts
  - MediaPipe face detection with confidence scoring
  - OBS Studio WebSocket integration for streaming
  - Intelligent window detection and activation
- **Dependencies**: `opencv-python`, `mediapipe`, `obsws-python`, `pygetwindow`, `keyboard`

### 5. Screen Recording with Marks
**C# Command**: `RecordWithMarksCommand.cs` | **Python Implementation**: `rec.py`

**Purpose**: Enhanced screen recording management with automatic file handling
- **C# Function**: Double-tap detection, session state management, UI updates with timers
- **Python Function**:
  - Windows Game Bar integration (Win+Alt+R)
  - Auto MP4 file detection in standard capture directories
  - JSON-based session state tracking
  - Background processing with stop flags
- **Dependencies**: Built-in Windows libraries, `pathlib`, `json`

### 6. Screenshot to LaTeX
**C# Command**: `ScrrenShotToLatex.cs`

**Purpose**: Convert screenshot to LaTeX code using OCR
- **Function**: Executes `latexocr` command to convert screenshots to LaTeX markup
- **Dependencies**: LaTeX OCR tool installation required

## Installation & Setup

1. **Install Python Dependencies**:
   ```bash
   pip install opencv-python mediapipe numpy pygame screen-brightness-control
   pip install pyautogui pywinctl customtkinter pygetwindow obsws-python keyboard
   ```

2. **Audio Files**:
   - For `boxing.py`: Place `punch.wav` sound file in the script directory

3. **OBS Setup** (for `fixed_meeting.py`):
   - Enable WebSocket plugin in OBS Studio
   - Configure connection settings if needed

## Usage Examples

**Via Loupedeck Plugin** (Recommended):
- Use the Loupedeck interface to trigger the C# commands directly
- Commands are available in the "Commands" and "Meeting" groups

**Direct Python Execution**:
- **Boxing game**: `python boxing.py`
- **Auto brightness**: `python brightness.py`
- **Smart paste tool**: `python call_paste_target.py`
- **Meeting controls**: `python fixed_meeting.py --mode meet --obs-password [password]`
- **Recording manager**: `python rec.py`

## Platform Compatibility

- **Primary**: Windows (full feature support)
- **Secondary**: macOS (limited compatibility for some features)
- **Requirements**: Webcam access for computer vision features

## Development Notes

**Architecture**:
- **C# Layer**: Loupedeck plugin commands that handle UI integration and process management
- **Python Layer**: Core functionality implementation using computer vision and automation libraries
- **Integration**: C# commands launch Python scripts via `ProcessStartInfo` with configurable paths

**Features**:
- Cross-platform compatibility where possible (primarily Windows-focused)
- Modern UI frameworks (CustomTkinter) for better user experience
- Integration with popular meeting platforms and streaming software
- State management for toggle-able commands (brightness, recording)
- Process lifecycle management with proper cleanup and error handling