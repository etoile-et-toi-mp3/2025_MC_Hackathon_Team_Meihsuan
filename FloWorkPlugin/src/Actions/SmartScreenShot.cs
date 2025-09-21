namespace Loupedeck.FloWorkPlugin
{     
    using System;     
    using System.Diagnostics;
   
    public class SmartPaste : PluginDynamicCommand     
    {            
        public SmartPaste()             
            : base(displayName: "Smart Paste", description: "paste target shortcut", groupName: "Study")         
        {         
        }          
  
        protected override void RunCommand(String actionParameter)
{
    try
    {
        var processStartInfo = new ProcessStartInfo
        {
            FileName = @"C:\Users\miche\AppData\Local\Microsoft\WindowsApps\pythonw.exe", 
            Arguments = @"call_paste_target.py",
            WorkingDirectory = @"D:\FloWorkPlugin\src\Actions\python_scripts\",
            UseShellExecute = true
        };
        
        Process.Start(processStartInfo);
        PluginLog.Info("lauching paste target with pythonw");
    }
    catch (Exception ex)
    {
        PluginLog.Info($"Error: {ex.Message}");
    }
}    

        protected override String GetCommandDisplayName(String actionParameter, PluginImageSize imageSize) =>             
            "Smart Paste";     
    } 
}

