namespace Loupedeck.FloWorkPlugin
{
    using System;
    using System.Diagnostics;
    using System.Text;

    public class VirtualTouchPadCommand : PluginDynamicCommand
    {
        private static Process _process;
        private static DateTime _startTime;

        public VirtualTouchPadCommand()
            : base("Virtual TouchPad", "Start/Stop The Virtual TouchPad", "Daily Use")
        {
        }

        private bool IsRunning => _process != null && !_process.HasExited;

        protected override void RunCommand(String actionParameter)
        {
            if (IsRunning)
            {
                StopVirtualTouchPad();
            }
            else
            {
                StartVirtualTouchPad();
            }

            this.ActionImageChanged(); // 刷新按鈕文字
        }

        private void StartVirtualTouchPad()
        {
            try
            {
                var psi = new ProcessStartInfo
                {
                    FileName = @"C:\Users\miche\AppData\Local\Microsoft\WindowsApps\pythonw.exe",
                    Arguments = "virtual_touchpad.py",
                    WorkingDirectory = @"D:/FloWorkPlugin/src/Actions/python_scripts/",
                    UseShellExecute = false,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    CreateNoWindow = true,
                    StandardOutputEncoding = Encoding.UTF8,
                    StandardErrorEncoding = Encoding.UTF8
                };

                _process = new Process { StartInfo = psi, EnableRaisingEvents = true };
                _process.Exited += (s, e) =>
                {
                    PluginLog.Info($"VirtualTouchPad process exited with code {_process?.ExitCode}");
                    _process = null;
                    this.ActionImageChanged();
                };

                _process.OutputDataReceived += (s, e) =>
                {
                    if (!string.IsNullOrEmpty(e.Data))
                        PluginLog.Info($"[VTP stdout] {e.Data}");
                };

                _process.ErrorDataReceived += (s, e) =>
                {
                    if (!string.IsNullOrEmpty(e.Data))
                        PluginLog.Warning($"[VTP stderr] {e.Data}");
                };

                if (_process.Start())
                {
                    _process.BeginOutputReadLine();
                    _process.BeginErrorReadLine();
                    _startTime = DateTime.Now;
                    PluginLog.Info("VirtualTouchPad started.");
                }
            }
            catch (Exception ex)
            {
                PluginLog.Error($"Failed to start VirtualTouchPad: {ex.Message}");
            }
        }

        private void StopVirtualTouchPad()
        {
            try
            {
                if (IsRunning)
                {
                    _process.Kill(true);
                    PluginLog.Info("VirtualTouchPad stopped.");
                }
            }
            catch (Exception ex)
            {
                PluginLog.Error($"Failed to stop VirtualTouchPad: {ex.Message}");
            }
            finally
            {
                try { _process?.Dispose(); } catch { }
                _process = null;
            }
        }

        protected override String GetCommandDisplayName(String actionParameter, PluginImageSize imageSize)
        {
            if (IsRunning)
            {
                var elapsed = DateTime.Now - _startTime;
                return $"Stop VirtualTouchPad";
            }
            else
            {
                return "Start VirtualTouchPad";
            }
        }

        protected override bool OnUnload()
        {
            try
            {
                StopVirtualTouchPad();
                return true;
            }
            catch
            {
                return false;
            }
        }
    }
}
