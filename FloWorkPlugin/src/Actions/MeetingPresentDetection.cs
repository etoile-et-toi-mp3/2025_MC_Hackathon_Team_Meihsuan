namespace Loupedeck.FloWorkPlugin
{
    using System;
    using System.Diagnostics;
    using System.IO;

    public class MeetingLauncherCommand : PluginDynamicCommand
    {
        private Process _meetingProcess; // 記住正在執行的 Python 程式

        public MeetingLauncherCommand()
            : base(displayName: "Auto Meeting Guard", description: "Launch meeting auto control", groupName: "Meeting")
        {
        }

        protected override void RunCommand(String actionParameter)
        {
            try
            {
                if (_meetingProcess != null && !_meetingProcess.HasExited)
                {
                    // 已經在執行 → 停止
                    PluginLog.Info("Stopping meeting control...");
                    try
                    {
                        _meetingProcess.Kill();
                        _meetingProcess.Dispose();
                        _meetingProcess = null;
                        PluginLog.Info("Meeting control stopped.");
                    }
                    catch (Exception killEx)
                    {
                        PluginLog.Error($"Error stopping meeting control: {killEx.Message}");
                    }

                    // 通知 Loupedeck 更新按鈕文字
                    this.ActionImageChanged();
                    return;
                }

                // 啟動新程式
                string pythonPath = @"C:/Users/miche/AppData/Local/Microsoft/WindowsApps/python3.12.exe";
                string scriptPath = @"D:\FloWorkPlugin\src\Actions\python_scripts\meeting.py";

                string arguments = $"\"{scriptPath}\" --mode meet --obs-password 20050616 --camera-source-name \"Video Capture Device\" --log-level INFO";

                if (!File.Exists(pythonPath))
                {
                    PluginLog.Error($"Python executable not found: {pythonPath}");
                    return;
                }

                if (!File.Exists(scriptPath))
                {
                    PluginLog.Error($"Python script not found: {scriptPath}");
                    return;
                }

                ProcessStartInfo startInfo = new ProcessStartInfo
                {
                    FileName = pythonPath,
                    Arguments = arguments,
                    UseShellExecute = false,
                    CreateNoWindow = true,
                    WorkingDirectory = Path.GetDirectoryName(scriptPath)
                };

                _meetingProcess = Process.Start(startInfo);
                PluginLog.Info("Meeting control launched successfully");

                // 通知 Loupedeck 更新按鈕文字
                this.ActionImageChanged();
            }
            catch (Exception ex)
            {
                PluginLog.Error($"Error launching/stopping meeting control: {ex.Message}");
                PluginLog.Error($"Exception details: {ex}");
            }
        }

        protected override String GetCommandDisplayName(String actionParameter, PluginImageSize imageSize) =>
            (_meetingProcess != null && !_meetingProcess.HasExited)
                ? "Stop Meeting\nGuard"
                : "Launch Meeting\nGuard";
    }
}
