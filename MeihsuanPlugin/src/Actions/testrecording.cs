namespace Loupedeck.MeihsuanPlugin
{
    using System;
    using System.IO;
    using System.Runtime.InteropServices;
    using System.Threading;
    using Microsoft.VisualBasic; // <--- 確保你已經加入了專案參考！

    // =================================================================
    // 主要指令: 將所有功能整合到一個按鈕
    // =================================================================
    public class UnifiedRecordingCommand : PluginDynamicCommand
    {
        private readonly System.Timers.Timer _uiTick;

        public UnifiedRecordingCommand()
            : base(displayName: "Unified Recording", description: "Start, Mark, and Stop recording with a single button.", groupName: "Screen Recording")
        {
            // 當錄影狀態改變時，通知UI更新
            RecordingStateService.StateChanged += () => this.ActionImageChanged();

            // 計時器，每一秒更新按鈕上顯示的時間
            _uiTick = new System.Timers.Timer(1000);
            _uiTick.Elapsed += (_, __) => { if (RecordingStateService.IsRecording) this.ActionImageChanged(); };
            _uiTick.Start();
        }



        protected override void RunCommand(String actionParameter)
        {
            // 情況一：如果不在錄影中，就開始錄影
            if (!RecordingStateService.IsRecording)
            {
                RecordingStateService.StartRecording();
            }
            // 情況二：如果在錄影中，就彈出輸入框
            else
            {
                // 彈出一個輸入框，讓使用者輸入提示詞
                // "Prompt:" 是視窗標題, "Enter your prompt..." 是提示文字
                string prompt = Interaction.InputBox("Enter prompt below.\nLeave it blank and press OK to stop recording.", "Add Timestamp Mark", "");

                // 如果使用者輸入了文字 (不是空的也不是null)
                if (!String.IsNullOrEmpty(prompt))
                {
                    RecordingStateService.AddMark(prompt);
                }
                // 如果使用者沒輸入任何東西就按了確定，或是直接按取消
                else
                {
                    RecordingStateService.StopRecording();
                }
            }
        }

        // 動態更新按鈕上的文字
        protected override String GetCommandDisplayName(String actionParameter, PluginImageSize imageSize)
        {
            if (RecordingStateService.IsRecording)
            {
                var elapsed = DateTime.UtcNow - RecordingStateService.SessionStartTime;
                var elapsedStr = elapsed.TotalHours >= 1.0 ? $"{(int)elapsed.TotalHours:00}:{elapsed.Minutes:00}:{elapsed.Seconds:00}" : $"{elapsed.Minutes:00}:{elapsed.Seconds:00}";
                return $"REC ● {elapsedStr}{Environment.NewLine}Add Mark/Stop";
            }
            else
            {
                return "Start Recording";
            }
        }
    }


    // =================================================================
    // 狀態管理器: 和之前一樣，集中管理錄影狀態
    // =================================================================
    public static class RecordingStateService
    {
        public static bool IsRecording { get; private set; } = false;
        public static DateTime SessionStartTime { get; private set; }
        public static String SessionLogFile { get; private set; } = "";

        public static event Action StateChanged;

        public static void StartRecording()
        {
            if (IsRecording) return;
            try
            {
                SendWin32.SendChordWinAltR();
                IsRecording = true;
                SessionStartTime = DateTime.UtcNow;

                var baseDir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "Loupedeck", "MeihsuanPlugin", "ScreenRecordMarks");
                Directory.CreateDirectory(baseDir);
                var sessionId = DateTime.Now.ToString("yyyyMMdd_HHmmss");
                SessionLogFile = Path.Combine(baseDir, $"{sessionId}_session.txt");

                WriteLineSafe($"# Recording session started at {DateTime.Now:yyyy-MM-dd HH:mm:ss.fff}");
                WriteLineSafe($"# Format: [Elapsed Time] | [Local Time] | [Prompt]");
                PluginLog.Info($"Recording started. Log file: {SessionLogFile}");
                StateChanged?.Invoke();
            }
            catch (Exception ex) { PluginLog.Error($"Failed to start recording: {ex}"); IsRecording = false; }
        }

        public static void StopRecording()
        {
            if (!IsRecording) return;
            try
            {
                SendWin32.SendChordWinAltR();
                IsRecording = false;
                WriteLineSafe($"# Recording session stopped at {DateTime.Now:yyyy-MM-dd HH:mm:ss.fff}");
                PluginLog.Info("Recording stopped.");
                StateChanged?.Invoke();
            }
            catch (Exception ex) { PluginLog.Error($"Failed to stop recording: {ex}"); }
        }

        public static void AddMark(string prompt)
        {
            if (!IsRecording) return;
            var elapsed = DateTime.UtcNow - SessionStartTime;
            var line = $"{FormatElapsed(elapsed),-12} | {DateTime.Now:HH:mm:ss.fff} | {prompt}";
            WriteLineSafe(line);
            PluginLog.Info($"Mark added: {line}");
            StateChanged?.Invoke();
        }

        private static void WriteLineSafe(string line)
        {
            try { File.AppendAllText(SessionLogFile, line + Environment.NewLine); }
            catch (Exception ex) { PluginLog.Error($"Failed writing to '{SessionLogFile}': {ex}"); }
        }

        private static string FormatElapsed(TimeSpan ts) =>
            ts.TotalHours >= 1.0 ? $"{(int)ts.TotalHours:00}:{ts.Minutes:00}:{ts.Seconds:00}" : $"{ts.Minutes:00}:{ts.Seconds:00}";
    }

    // =================================================================
    // Win32 API 輔助工具: 和之前一樣，用來模擬鍵盤輸入
    // =================================================================
    public static class SendWin32
    {
        private const ushort VK_LWIN = 0x5B, VK_MENU = 0x12, VK_R = 0x52;

        public static void SendChordWinAltR()
        {
            KeyDown(VK_LWIN); SleepTiny(); KeyDown(VK_MENU); SleepTiny();
            KeyPress(VK_R); SleepTiny(); KeyUp(VK_MENU); SleepTiny(); KeyUp(VK_LWIN);
        }

        private static void KeyPress(ushort vk) { KeyDown(vk); SleepTiny(); KeyUp(vk); }
        private static void KeyDown(ushort vk) => SendInputWrapper(vk, keyUp: false);
        private static void KeyUp(ushort vk) => SendInputWrapper(vk, keyUp: true);
        private static void SleepTiny() => Thread.Sleep(30);

        private static void SendInputWrapper(ushort vk, bool keyUp)
        {
            INPUT[] inputs = { new INPUT { type = 1, U = new INPUTUNION { ki = new KEYBDINPUT { wVk = vk, dwFlags = keyUp ? KEYEVENTF.KEYUP : 0 } } } };
            if (SendInput((uint)inputs.Length, inputs, Marshal.SizeOf(typeof(INPUT))) == 0)
            {
                PluginLog.Warning($"SendInput failed. Error: {Marshal.GetLastWin32Error()}");
            }
        }

        [StructLayout(LayoutKind.Sequential)] private struct INPUT { public int type; public INPUTUNION U; }
        [StructLayout(LayoutKind.Explicit)] private struct INPUTUNION { [FieldOffset(0)] public KEYBDINPUT ki; }
        [StructLayout(LayoutKind.Sequential)] private struct KEYBDINPUT { public ushort wVk; public ushort wScan; public uint dwFlags; public uint time; public IntPtr dwExtraInfo; }
        private static class KEYEVENTF { public const uint KEYUP = 0x0002; }
        [DllImport("user32.dll", SetLastError = true)] private static extern uint SendInput(uint nInputs, INPUT[] pInputs, int cbSize);
    }
}