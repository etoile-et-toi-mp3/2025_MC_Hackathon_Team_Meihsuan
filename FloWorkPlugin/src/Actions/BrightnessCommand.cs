namespace Loupedeck.FloWorkPlugin
{
    using System;
    using System.Diagnostics;
    using System.Text;

    public class BrightnessToggleCommand : PluginDynamicCommand // 差異：類名改為 BrightnessToggleCommand
    {
        private static Process _process;            // 與前例相同
        private static DateTime _startTime;         // 與前例相同

        public BrightnessToggleCommand()
            : base("Adaptive Brightness", "啟動或停止螢幕亮度調整腳本", "Daily Use") // 差異：顯示名稱/描述
        {
        }

        private bool IsRunning => _process != null && !_process.HasExited; // 與前例相同

        protected override void RunCommand(String actionParameter)
        {
            if (IsRunning)
            {
                StopBrightness(); // 差異：呼叫停止 brightness
            }
            else
            {
                StartBrightness(); // 差異：呼叫啟動 brightness
            }

            this.ActionImageChanged(); // 與前例相同：刷新按鈕文字（Start/Stop）
        }

        private void StartBrightness() // 差異：方法名稱
        {
            try
            {
                var psi = new ProcessStartInfo
                {
                    FileName = @"C:\Users\miche\AppData\Local\Microsoft\WindowsApps\pythonw.exe", // 與前例相同：使用 pythonw
                    // 建議使用完整路徑並加引號，避免 WorkingDirectory 改變或路徑含空白的問題
                    Arguments = @"""D:\FloWorkPlugin\src\Actions\python_scripts\brightness.py""", // 差異：改為 brightness.py 的完整路徑
                    WorkingDirectory = @"D:/FloWorkPlugin/src/Actions/python_scripts/",           // 與前例相同（可留作相對參考）
                    UseShellExecute = false,               // 與前例相同：需要重導輸出
                    RedirectStandardOutput = true,         // 與前例相同
                    RedirectStandardError = true,          // 與前例相同
                    CreateNoWindow = true,                 // 與前例相同
                    StandardOutputEncoding = Encoding.UTF8,// 與前例相同
                    StandardErrorEncoding = Encoding.UTF8  // 與前例相同
                };

                _process = new Process { StartInfo = psi, EnableRaisingEvents = true }; // 與前例相同
                _process.Exited += (s, e) =>
                {
                    PluginLog.Info($"[Brightness] process exited with code {_process?.ExitCode}"); // 差異：前綴 Brightness
                    _process = null;
                    this.ActionImageChanged(); // 與前例相同
                };

                _process.OutputDataReceived += (s, e) =>
                {
                    if (!string.IsNullOrEmpty(e.Data))
                        PluginLog.Info($"[Brightness stdout] {e.Data}"); // 差異：前綴 Brightness
                };

                _process.ErrorDataReceived += (s, e) =>
                {
                    if (!string.IsNullOrEmpty(e.Data))
                        PluginLog.Warning($"[Brightness stderr] {e.Data}"); // 差異：前綴 Brightness
                };

                if (_process.Start())
                {
                    _process.BeginOutputReadLine();
                    _process.BeginErrorReadLine();
                    _startTime = DateTime.Now;
                    PluginLog.Info("Brightness script started."); // 差異：訊息
                }
            }
            catch (Exception ex)
            {
                PluginLog.Error($"Failed to start Brightness script: {ex.Message}"); // 差異：訊息
            }
        }

        private void StopBrightness() // 差異：方法名稱
        {
            try
            {
                if (IsRunning)
                {
                    _process.Kill(true); // 與前例相同：強制結束（含子行程）
                    PluginLog.Info("Brightness script stopped."); // 差異：訊息
                }
            }
            catch (Exception ex)
            {
                PluginLog.Error($"Failed to stop Brightness script: {ex.Message}"); // 差異：訊息
            }
            finally
            {
                try { _process?.Dispose(); } catch { } // 與前例相同
                _process = null; // 與前例相同
            }
        }

        protected override String GetCommandDisplayName(String actionParameter, PluginImageSize imageSize)
        {
            if (IsRunning)
            {
                var elapsed = DateTime.Now - _startTime; // 如需顯示經過時間可用
                return "Stop Brightness"; // 差異：顯示 Stop Brightness
            }
            else
            {
                return "Adaptive Brightness"; // 差異：顯示 Start Brightness
            }
        }

        protected override bool OnUnload()
        {
            try
            {
                StopBrightness(); // 差異：卸載時停止 Brightness
                return true;
            }
            catch
            {
                return false;
            }
        }
    }
}
