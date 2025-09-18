namespace Loupedeck.MeihsuanPlugin
{
    using System;
    using System.Collections.Generic;
    using System.IO;
    using System.Runtime.InteropServices;
    using System.Threading;
    using System.Timers;

    // A dynamic command that starts a screen-record session (Win+Alt+R) and records timestamp marks.
    public class RecordWithMarksCommand : PluginDynamicCommand
    {
        private bool _recording = false;
        private DateTime _sessionStartUtc;
        private string _sessionId = "";
        private string _sessionLogFile = "";
        private readonly List<TimeSpan> _marks = new List<TimeSpan>();

        // UI refresh timer so the key text shows live elapsed time
        private readonly System.Timers.Timer _uiTick;

        // Hotkey: Win + Alt + R (Xbox Game Bar record toggle)
        private const ushort VK_LWIN = 0x5B;
        private const ushort VK_MENU = 0x12; // Alt
        private const ushort VK_R = 0x52;

        public RecordWithMarksCommand()
            : base(displayName: "Start Recording", description: "Start Win+Alt+R recording and drop timestamp marks on press", groupName: "Commands")
        {
            _uiTick = new System.Timers.Timer(1000);
            _uiTick.Elapsed += (_, __) => this.ActionImageChanged();
        }

        protected override void RunCommand(String actionParameter)
        {
            if (!_recording)
            {
                // Start screen recording via Win+Alt+R and init session
                try
                {
                    SendChordWinAltR();
                    _recording = true;
                    _sessionStartUtc = DateTime.UtcNow;
                    _marks.Clear();
                    _sessionId = DateTime.Now.ToString("yyyyMMdd_HHmmss");

                    var baseDir = Path.Combine(
                        Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),
                        "Loupedeck", "MeihsuanPlugin", "ScreenRecordMarks");
                    Directory.CreateDirectory(baseDir);
                    _sessionLogFile = Path.Combine(baseDir, $"{_sessionId}_session.txt");

                    WriteLineSafe(_sessionLogFile, $"# Recording session started at {DateTime.Now:yyyy-MM-dd HH:mm:ss.fff}");
                    WriteLineSafe(_sessionLogFile, $"# Each mark: [elapsed] | [local time]");
                    PluginLog.Info($"Recording started. Log file: {_sessionLogFile}");

                    _uiTick.Start();
                }
                catch (Exception ex)
                {
                    PluginLog.Error($"Failed to start recording hotkey: {ex}");
                }
            }
            else
            {
                // Add a timestamp mark
                var nowUtc = DateTime.UtcNow;
                var elapsed = nowUtc - _sessionStartUtc;
                _marks.Add(elapsed);

                var line = $"{FormatElapsed(elapsed),-12} | {DateTime.Now:HH:mm:ss.fff}";
                WriteLineSafe(_sessionLogFile, line);
                PluginLog.Info($"Mark {_marks.Count}: {line}");

                // Brief UI ping (updates label immediately)
                this.ActionImageChanged();
            }
        }

        protected override String GetCommandDisplayName(String actionParameter, PluginImageSize imageSize)
        {
            if (_recording)
            {
                var elapsed = DateTime.UtcNow - _sessionStartUtc;
                return $"REC ●  {FormatElapsed(elapsed)}{Environment.NewLine}Marks: {_marks.Count}";
            }
            else
            {
                return "Start Recording";
            }
        }

        // ---- Helpers ----

        private static string FormatElapsed(TimeSpan ts)
        {
            // HH:MM:SS (show hours only if >= 1h)
            if (ts.TotalHours >= 1.0)
                return $"{(int)ts.TotalHours:00}:{ts.Minutes:00}:{ts.Seconds:00}";
            return $"{ts.Minutes:00}:{ts.Seconds:00}";
        }

        private static void WriteLineSafe(string path, string line)
        {
            try
            {
                using (var sw = new StreamWriter(path, append: true))
                {
                    sw.WriteLine(line);
                }
            }
            catch (Exception ex)
            {
                PluginLog.Error($"Failed writing '{line}' to '{path}': {ex}");
            }
        }

        // Send Win+Alt+R using Win32 SendInput
        private static void SendChordWinAltR()
        {
            // Win down -> Alt down -> R down -> R up -> Alt up -> Win up
            KeyDown(VK_LWIN);
            SleepTiny();
            KeyDown(VK_MENU);
            SleepTiny();
            KeyPress(VK_R);
            SleepTiny();
            KeyUp(VK_MENU);
            SleepTiny();
            KeyUp(VK_LWIN);
        }

        private static void KeyPress(ushort vk)
        {
            KeyDown(vk);
            SleepTiny();
            KeyUp(vk);
        }

        private static void KeyDown(ushort vk) => SendInputWrapper(vk, keyUp: false);
        private static void KeyUp(ushort vk) => SendInputWrapper(vk, keyUp: true);

        private static void SleepTiny() => Thread.Sleep(30);

        private static void SendInputWrapper(ushort vk, bool keyUp)
        {
            INPUT[] inputs = new INPUT[1];
            inputs[0].type = 1; // INPUT_KEYBOARD
            inputs[0].U.ki = new KEYBDINPUT
            {
                wVk = vk,
                wScan = 0,
                dwFlags = keyUp ? KEYEVENTF.KEYUP : 0,
                time = 0,
                dwExtraInfo = IntPtr.Zero
            };
            var sent = SendInput((uint)inputs.Length, inputs, Marshal.SizeOf(typeof(INPUT)));
            if (sent == 0)
            {
                var err = Marshal.GetLastWin32Error();
                PluginLog.Warning($"SendInput failed for vk=0x{vk:X} (keyUp={keyUp}) lastError={err}");
            }
        }

        // ---- Win32 interop ----
        [StructLayout(LayoutKind.Sequential)]
        private struct INPUT
        {
            public int type; // 1 = Keyboard
            public INPUTUNION U;
        }

        [StructLayout(LayoutKind.Explicit)]
        private struct INPUTUNION
        {
            [FieldOffset(0)] public KEYBDINPUT ki;
        }

        [StructLayout(LayoutKind.Sequential)]
        private struct KEYBDINPUT
        {
            public ushort wVk;
            public ushort wScan;
            public uint dwFlags;
            public uint time;
            public IntPtr dwExtraInfo;
        }

        private static class KEYEVENTF
        {
            public const uint EXTENDEDKEY = 0x0001;
            public const uint KEYUP = 0x0002;
            public const uint SCANCODE = 0x0008;
            public const uint UNICODE = 0x0004;
        }

        [DllImport("user32.dll", SetLastError = true)]
        private static extern uint SendInput(uint nInputs, INPUT[] pInputs, int cbSize);
    }
}
