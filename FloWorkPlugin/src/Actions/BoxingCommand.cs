namespace Loupedeck.FloWorkPlugin
{
    using System;
    using System.Diagnostics;
    using System.Text;

    public class BoxingToggleCommand : PluginDynamicCommand // 差異：類名改為 BoxingToggleCommand，避免撞名
    {
        private static Process _process; // 與 VTP 相同
        private static DateTime _startTime; // 與 VTP 相同

        public BoxingToggleCommand()
            : base("Stress-Relief Mini Game", "啟動或停止拳擊偵測小遊戲", "Daily Use") // 差異：顯示名稱與描述對應 boxing
        {
        }

        private bool IsRunning => _process != null && !_process.HasExited; // 與 VTP 相同

        protected override void RunCommand(String actionParameter)
        {
            if (IsRunning)
            {
                StopBoxing(); // 差異：呼叫停止 boxing
            }
            else
            {
                StartBoxing(); // 差異：呼叫啟動 boxing
            }

            this.ActionImageChanged(); // 與 VTP 相同：刷新按鈕文字（Start/Stop）
        }

        private void StartBoxing() // 差異：方法名稱改為 StartBoxing
        {
            try
            {
                var psi = new ProcessStartInfo
                {
                    FileName = @"C:\Users\miche\AppData\Local\Microsoft\WindowsApps\pythonw.exe", // 與 VTP 相同：使用 pythonw
                    Arguments = @"""boxing.py""", // 差異：腳本換成 boxing.py；若路徑含空白建議改成完整路徑
                    WorkingDirectory = @"D:/FloWorkPlugin/src/Actions/python_scripts/", // 與 VTP 類似：改為你 boxing.py 所在資料夾
                    UseShellExecute = false, // 與 VTP 相同：要重導輸出因此關閉 shell
                    RedirectStandardOutput = true, // 與 VTP 相同
                    RedirectStandardError = true, // 與 VTP 相同
                    CreateNoWindow = true, // 與 VTP 相同
                    StandardOutputEncoding = Encoding.UTF8, // 與 VTP 相同
                    StandardErrorEncoding = Encoding.UTF8 // 與 VTP 相同
                };

                _process = new Process { StartInfo = psi, EnableRaisingEvents = true }; // 與 VTP 相同
                _process.Exited += (s, e) =>
                {
                    PluginLog.Info($"[Boxing] process exited with code {_process?.ExitCode}"); // 差異：前綴改成 Boxing
                    _process = null; // 與 VTP 相同
                    this.ActionImageChanged(); // 與 VTP 相同
                };

                _process.OutputDataReceived += (s, e) =>
                {
                    if (!string.IsNullOrEmpty(e.Data))
                        PluginLog.Info($"[Boxing stdout] {e.Data}"); // 差異：前綴改成 Boxing
                };

                _process.ErrorDataReceived += (s, e) =>
                {
                    if (!string.IsNullOrEmpty(e.Data))
                        PluginLog.Warning($"[Boxing stderr] {e.Data}"); // 差異：前綴改成 Boxing
                };

                if (_process.Start())
                {
                    _process.BeginOutputReadLine(); // 與 VTP 相同
                    _process.BeginErrorReadLine(); // 與 VTP 相同
                    _startTime = DateTime.Now; // 與 VTP 相同
                    PluginLog.Info("Boxing started."); // 差異：訊息改 Boxing
                }
            }
            catch (Exception ex)
            {
                PluginLog.Error($"Failed to start Boxing: {ex.Message}"); // 差異：訊息改 Boxing
            }
        }

        private void StopBoxing() // 差異：方法名稱改為 StopBoxing
        {
            try
            {
                if (IsRunning)
                {
                    _process.Kill(true); // 與 VTP 相同：強制結束（含子行程）
                    PluginLog.Info("Boxing stopped."); // 差異：訊息改 Boxing
                }
            }
            catch (Exception ex)
            {
                PluginLog.Error($"Failed to stop Boxing: {ex.Message}"); // 差異：訊息改 Boxing
            }
            finally
            {
                try { _process?.Dispose(); } catch { } // 與 VTP 相同
                _process = null; // 與 VTP 相同
            }
        }

        protected override String GetCommandDisplayName(String actionParameter, PluginImageSize imageSize)
        {
            if (IsRunning)
            {
                var elapsed = DateTime.Now - _startTime; // 與 VTP 相同（如需顯示經過時間可用）
                return "Stop Boxing"; // 差異：顯示 Stop Boxing
            }
            else
            {
                return "Start Boxing"; // 差異：顯示 Start Boxing
            }
        }

        protected override bool OnUnload()
        {
            try
            {
                StopBoxing(); // 差異：卸載時停止 Boxing
                return true; // 與 VTP 相同
            }
            catch
            {
                return false; // 與 VTP 相同
            }
        }
    }
}
