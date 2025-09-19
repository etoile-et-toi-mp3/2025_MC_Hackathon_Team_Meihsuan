// namespace Loupedeck.MeihsuanPlugin
// {
//     using System;
//     using System.IO;
//     using System.Runtime.InteropServices;
//     using System.Threading;
//     using Microsoft.VisualBasic;

//     // =================================================================
//     // 主要指令: 將所有功能整合到一個按鈕
//     // =================================================================
//     public class UnifiedRecordingCommand : PluginDynamicCommand
//     {
//         // ... (這個類別的內容完全不變) ...
//         private readonly System.Timers.Timer _uiTick;

//         public UnifiedRecordingCommand()
//             : base(displayName: "Unified Recording", description: "Start, Mark, and Stop recording with a single button.", groupName: "Screen Recording")
//         {
//             RecordingStateService.StateChanged += () => this.ActionImageChanged();
//             _uiTick = new System.Timers.Timer(1000);
//             _uiTick.Elapsed += (_, __) => { if (RecordingStateService.IsRecording) this.ActionImageChanged(); };
//             _uiTick.Start();
//         }

//         protected override void RunCommand(String actionParameter)
//         {
//             if (!RecordingStateService.IsRecording)
//             {
//                 RecordingStateService.StartRecording();
//             }
//             else
//             {
//                 string prompt = Interaction.InputBox("Enter prompt below.\nLeave it blank and press OK to stop recording.", "Add Timestamp Mark", "");
//                 if (!String.IsNullOrEmpty(prompt))
//                 {
//                     RecordingStateService.AddMark(prompt);
//                 }
//                 else
//                 {
//                     RecordingStateService.StopRecording();
//                 }
//             }
//         }

//         protected override String GetCommandDisplayName(String actionParameter, PluginImageSize imageSize)
//         {
//             if (RecordingStateService.IsRecording)
//             {
//                 var elapsed = DateTime.UtcNow - RecordingStateService.SessionStartTime;
//                 var elapsedStr = elapsed.TotalHours >= 1.0 ? $"{(int)elapsed.TotalHours:00}:{elapsed.Minutes:00}:{elapsed.Seconds:00}" : $"{elapsed.Minutes:00}:{elapsed.Seconds:00}";
//                 return $"REC ● {elapsedStr}{Environment.NewLine}Add Mark/Stop";
//             }
//             return "Start Recording";
//         }
//     }

//     // =================================================================
//     // 狀態管理器: 和之前一樣，集中管理錄影狀態
//     // =================================================================
//     public static class RecordingStateService
//     {
//         // ... (這個類別的內容也完全不變) ...
//         public static bool IsRecording { get; private set; } = false;
//         public static DateTime SessionStartTime { get; private set; }
//         public static String SessionLogFile { get; private set; } = "";

//         public static event Action StateChanged;

//         public static void StartRecording()
//         {
//             if (IsRecording) return;
//             try
//             {
//                 PlatformKeySender.SendScreenRecordShortcut(); // <-- 注意：這裡呼叫的是新的類別
//                 IsRecording = true;
//                 // ... 後續程式碼不變 ...
//                 SessionStartTime = DateTime.UtcNow;
//                 var baseDir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "Loupedeck", "MeihsuanPlugin", "ScreenRecordMarks");
//                 Directory.CreateDirectory(baseDir);
//                 var sessionId = DateTime.Now.ToString("yyyyMMdd_HHmmss");
//                 SessionLogFile = Path.Combine(baseDir, $"{sessionId}_session.txt");
//                 WriteLineSafe($"# Recording session started at {DateTime.Now:yyyy-MM-dd HH:mm:ss.fff}");
//                 WriteLineSafe($"# Format: [Elapsed Time] | [Local Time] | [Prompt]");
//                 PluginLog.Info($"Recording started. Log file: {SessionLogFile}");
//                 StateChanged?.Invoke();
//             }
//             catch (Exception ex) { PluginLog.Error($"Failed to start recording: {ex.Message}"); IsRecording = false; }
//         }

//         public static void StopRecording()
//         {
//             if (!IsRecording) return;
//             try
//             {
//                 PlatformKeySender.SendScreenRecordShortcut(); // <-- 注意：這裡呼叫的是新的類別
//                 IsRecording = false;
//                 WriteLineSafe($"# Recording session stopped at {DateTime.Now:yyyy-MM-dd HH:mm:ss.fff}");
//                 PluginLog.Info("Recording stopped.");
//                 StateChanged?.Invoke();
//             }
//             catch (Exception ex) { PluginLog.Error($"Failed to stop recording: {ex.Message}"); }
//         }

//         public static void AddMark(string prompt)
//         {
//             // ... (這個方法不變) ...
//              if (!IsRecording) return;
//             var elapsed = DateTime.UtcNow - SessionStartTime;
//             var line = $"{FormatElapsed(elapsed),-12} | {DateTime.Now:HH:mm:ss.fff} | {prompt}";
//             WriteLineSafe(line);
//             PluginLog.Info($"Mark added: {line}");
//             StateChanged?.Invoke();
//         }

//         private static void WriteLineSafe(string line)
//         {
//             try { File.AppendAllText(SessionLogFile, line + Environment.NewLine); }
//             catch (Exception ex) { PluginLog.Error($"Failed writing to '{SessionLogFile}': {ex.Message}"); }
//         }

//         private static string FormatElapsed(TimeSpan ts) =>
//             ts.TotalHours >= 1.0 ? $"{(int)ts.TotalHours:00}:{ts.Minutes:00}:{ts.Seconds:00}" : $"{ts.Minutes:00}:{ts.Seconds:00}";
//     }

//     // =================================================================
//     // ✨【簡化版】平台按鍵發送器 ✨
//     // =================================================================
//     public static class PlatformKeySender
//     {
//         public static void SendScreenRecordShortcut()
//         {
//             // 在程式執行時，直接檢查當前的作業系統
//             if (OperatingSystem.IsWindows())
//             {
//                 PluginLog.Info("Detected Windows OS. Sending Win+Alt+R.");
//                 Win32.SendWinAltR();
//             }
//             else if (OperatingSystem.IsMacOS())
//             {
//                 PluginLog.Info("Detected macOS. Sending Shift+Cmd+5.");
//                 MacOS.SendShiftCmd5();
//             }
//             else
//             {
//                 PluginLog.Warning("Unsupported operating system for screen recording shortcut.");
//             }
//         }

//         // --- macOS 專用程式碼 ---
//         private static class MacOS
//         {
//             internal static void SendShiftCmd5()
//             {
//                 var script = "tell application \\"System Events\\" to keystroke \\"5\\" using {shift down, command down}";
//                 try
//                 {
//                     using (var process = new System.Diagnostics.Process())
//                     {
//                         process.StartInfo = new System.Diagnostics.ProcessStartInfo
//                         {
//                             FileName = "/usr/bin/osascript",
//                             Arguments = $"-e \"{script}\"",
//                             UseShellExecute = false,
//                             CreateNoWindow = true,
//                         };
//                         process.Start();
//                     }
//                 }
//                 catch (Exception ex)
//                 {
//                     PluginLog.Error($"Failed to send key on macOS: {ex.Message}");
//                 }
//             }
//         }

//         // --- Windows 專用程式碼 ---
//         private static class Win32
//         {
//             internal static void SendWinAltR()
//             {
//                 const ushort VK_LWIN = 0x5B, VK_MENU = 0x12, VK_R = 0x52;
//                 KeyDown(VK_LWIN); Thread.Sleep(30); KeyDown(VK_MENU); Thread.Sleep(30);
//                 KeyPress(VK_R); Thread.Sleep(30); KeyUp(VK_MENU); Thread.Sleep(30); KeyUp(VK_LWIN);
//             }

//             private static void KeyPress(ushort vk) { KeyDown(vk); Thread.Sleep(30); KeyUp(vk); }
//             private static void KeyDown(ushort vk) => SendInputWrapper(vk, keyUp: false);
//             private static void KeyUp(ushort vk) => SendInputWrapper(vk, keyUp: true);

//             private static void SendInputWrapper(ushort vk, bool keyUp)
//             {
//                 INPUT[] inputs = { new INPUT { type = 1, U = new INPUTUNION { ki = new KEYBDINPUT { wVk = vk, dwFlags = keyUp ? KEYEVENTF.KEYUP : 0 } } } };
//                 if (SendInput((uint)inputs.Length, inputs, Marshal.SizeOf(typeof(INPUT))) == 0)
//                 {
//                      PluginLog.Warning($"SendInput failed. Error: {Marshal.GetLastWin32Error()}");
//                 }
//             }
            
//             [StructLayout(LayoutKind.Sequential)] private struct INPUT { public int type; public INPUTUNION U; }
//             [StructLayout(LayoutKind.Explicit)] private struct INPUTUNION { [FieldOffset(0)] public KEYBDINPUT ki; }
//             [StructLayout(LayoutKind.Sequential)] private struct KEYBDINPUT { public ushort wVk; public ushort wScan; public uint dwFlags; public uint time; public IntPtr dwExtraInfo; }
//             private static class KEYEVENTF { public const uint KEYUP = 0x0002; }
//             [DllImport("user32.dll", SetLastError = true)] private static extern uint SendInput(uint nInputs, INPUT[] pInputs, int cbSize);
//         }
//     }
// }