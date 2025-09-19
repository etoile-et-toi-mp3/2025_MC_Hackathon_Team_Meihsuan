namespace Loupedeck.MeiPlugin 
{     
    using System;     
    using System.Diagnostics;
    using System.IO;
   
    public class MeetingLauncherCommand : PluginDynamicCommand     
    {            
        public MeetingLauncherCommand()             
            : base(displayName: "Meeting Control", description: "Launch meeting auto control", groupName: "Meeting")         
        {         
        }          
  
        protected override void RunCommand(String actionParameter)         
        {             
            try 
            {
                // 修改這些路徑為你的實際路徑
                string pythonPath = @"C:/Users/miche/AppData/Local/Microsoft/WindowsApps/python3.12.exe";  // 你的虛擬環境 Python 路徑
                string scriptPath = @"D:\MeiPlugin\src\Actions\python_scripts\fixed_meeting.py";  // 你的 Python 腳本路徑
                
                // Python 程式參數
                string arguments = $"\"{scriptPath}\" --mode meet --obs-password 20050616 --camera-source-name \"Video Capture Device\" --show --log-level INFO";

                // 檢查文件是否存在
                if (!File.Exists(pythonPath))
                {
                    PluginLog.Error($"Python executable not found: {pythonPath}");
                    PluginLog.Error("請確認 Python 虛擬環境路徑正確");
                    return;
                }

                if (!File.Exists(scriptPath))
                {
                    PluginLog.Error($"Python script not found: {scriptPath}");
                    PluginLog.Error("請確認 Python 腳本路徑正確");
                    return;
                }

                // 啟動 Python 程式
                ProcessStartInfo startInfo = new ProcessStartInfo
                {
                    FileName = pythonPath,
                    Arguments = arguments,
                    UseShellExecute = false,
                    CreateNoWindow = false,  // 顯示控制台視窗以便監控
                    WorkingDirectory = Path.GetDirectoryName(scriptPath)
                };

                Process.Start(startInfo);
                PluginLog.Info("Meeting control launched successfully");
            }
            catch (Exception ex) 
            {
                PluginLog.Error($"Error launching meeting control: {ex.Message}");
                PluginLog.Error($"Exception details: {ex}");
            }
        }          
        
        protected override String GetCommandDisplayName(String actionParameter, PluginImageSize imageSize) =>             
            "Launch Meeting\nControl";     
    } 
}
