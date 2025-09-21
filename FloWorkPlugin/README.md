# FloWork Plugin

A comprehensive Loupedeck plugin that enhances productivity through innovative computer vision and automation features. This plugin provides multiple tools for meeting management, screen recording, adaptive controls, and interactive features.

## Core Features

### Meeting Auto Guard

Automatic face detection that manages meeting camera visibility based on user presence. When you leave your seat, the system automatically switches to a "Be Right Back" screen and mutes your microphone; when you return, it automatically restores normal operation.

#### How It Works

The key innovation is using OBS Virtual Camera, allowing the system to continue face detection even when the camera appears "off" to meeting participants, enabling true automatic recovery functionality.

#### Setup Requirements

**OBS Studio Configuration:**
1. Create a scene named `Live`
2. Add a camera source to the Live scene, name it `Video Capture Device`
3. Go to Tools → WebSocket Server Settings, enable and set a password
4. Start Virtual Camera

**Meeting Software Configuration:**
Set your camera to `OBS Virtual Camera` in your meeting application:
- **Google Meet**: Settings → Camera → OBS Virtual Camera
- **Zoom**: Camera options → Choose Camera → OBS Virtual Camera

#### Implementation Files
- `src/Actions/MeetingPresentDetection.cs` - C# command interface for Loupedeck
- `src/Actions/python_scripts/meeting.py` - Core face detection and OBS control logic

## Action Components

### Recording and Documentation

#### Sync-note Recorder
**Files:** `RecordWithMarksCommand.cs`, `rec.py`

Advanced screen recording system with smart marking functionality:
- **Single tap during recording**: Add timestamped mark
- **Double tap during recording**: Stop recording
- **Tap when not recording**: Start new recording session
- Automatic session state management
- Supports Win+Alt+R global hotkey integration

#### Smart Screenshot Tools
**Files:** `SmartScreenShot.cs`, `ScreenShotToLatex.cs`

Intelligent screenshot capture with:
- Smart crop detection
- LaTeX formula recognition and conversion
- Automatic clipboard integration

### Gesture Control and Interaction

#### Virtual Touchpad
**Files:** `VirtualTouchpadCommand.cs`, `virtual_touchpad.py`

Computer vision-based hand gesture control system:
- **Two fingers**: Page navigation (Alt+Left/Right)
- **Four fingers**: Virtual desktop switching (Ctrl+Win+Left/Right)
- **OK gesture**: Alt-Tab application switching with visual feedback
- **Seven gesture**: Zoom control (Ctrl+Plus/Minus)
- Full-screen transparent overlay with visual cursor tracking
- Real-time hand detection and gesture recognition

#### Stress-Relief Boxing Game
**Files:** `BoxingCommand.cs`, `boxing.py`

Interactive stress-relief mini-game:
- Real-time fist detection using MediaPipe
- Punch type recognition (straight, left hook, right hook)
- Dynamic screen crack effects
- Score tracking system
- Sound feedback with customizable audio

### System Optimization

#### Adaptive Brightness Control
**Files:** `BrightnessCommand.cs`, `brightness.py`

Automatic screen brightness adjustment:
- Camera-based environment light detection
- Dynamic brightness mapping (30-150 lux → 10-100% brightness)
- Real-time adjustment with 1-second intervals
- Smart interpolation for smooth transitions

#### Pulse Light Control
**Files:** `PulseLight.cs`

Advanced lighting control integration for workspace ambiance management.

## Technical Architecture

### C# Components (`src/Actions/*.cs`)
- **Loupedeck Integration**: All C# files inherit from `PluginDynamicCommand`
- **Process Management**: Robust Python subprocess handling with proper lifecycle management
- **State Synchronization**: Real-time state watching and UI updates
- **Error Handling**: Comprehensive logging and exception management

### Python Scripts (`src/Actions/python_scripts/`)
- **Computer Vision**: MediaPipe integration for hand and face detection
- **OBS Integration**: WebSocket API v5 for scene and source control
- **System Integration**: Windows API calls for keyboard/mouse simulation
- **Audio Processing**: Pygame for sound effects and feedback

### Key Dependencies
- **MediaPipe**: Hand and face landmark detection
- **OpenCV**: Computer vision and image processing
- **OBS WebSocket**: Remote OBS Studio control
- **PyAutoGUI**: System automation and hotkey simulation
- **Screen Brightness Control**: Display brightness management

## Installation and Setup

1. **Install Python Dependencies:**
   ```bash
   pip install opencv-python mediapipe pyautogui screen-brightness-control obsws-python pygame pygetwindow keyboard
   ```

2. **Configure OBS Studio:**
   - Install OBS Studio
   - Enable WebSocket server with password
   - Create required scenes (Live, BRB)
   - Start Virtual Camera

3. **Plugin Installation:**
   - Copy plugin files to Loupedeck plugin directory
   - Update Python executable paths in C# files to match your system
   - Configure script paths to match your installation directory

## Usage

### Meeting Auto Guard
1. Launch from Loupedeck: "Auto Meeting Guard" button
2. System automatically detects presence and manages camera/microphone
3. Press button again to stop monitoring

### Virtual Touchpad
1. Activate "Virtual TouchPad" from Loupedeck
2. Use hand gestures in front of camera for system control
3. Visual overlay shows cursor position and gesture recognition

### Recording with Marks
1. Start recording with "Sync-note Recorder"
2. Single tap to add timestamps during recording
3. Double tap to stop and save recording

### Boxing Game
1. Launch "Stress-Relief Mini Game"
2. Make fists and punch toward camera
3. Score points with different punch types

### Adaptive Brightness
1. Enable "Adaptive Brightness"
2. System automatically adjusts screen brightness based on ambient light
3. Manual override available through system settings

## Configuration

All components support customizable parameters:
- **Camera indices**: Adjust for different camera setups
- **Detection thresholds**: Fine-tune sensitivity for gestures and face detection
- **File paths**: Configure storage locations for recordings and logs
- **Timing parameters**: Adjust debounce and cooldown periods

## Troubleshooting

### Common Issues
- **Camera not detected**: Check camera index in Python scripts
- **OBS connection failed**: Verify WebSocket settings and password
- **Gesture recognition poor**: Ensure good lighting and camera positioning
- **Python path errors**: Update executable paths in C# command files

### Logs and Debugging
- Check Loupedeck plugin logs for C# component issues
- Python scripts output to console for debugging
- OBS WebSocket connection status in meeting.py logs

## Development Notes

This plugin demonstrates advanced integration between:
- Loupedeck hardware controls
- Computer vision processing
- System automation
- External application control (OBS Studio)
- Real-time user interface feedback

The architecture supports easy extension for additional gesture types, meeting platforms, and automation scenarios.