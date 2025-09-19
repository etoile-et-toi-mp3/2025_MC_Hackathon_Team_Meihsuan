namespace Loupedeck.MeiPlugin
{     
    using System;     
    using System.Diagnostics;
   
    public class BoxingCommand : PluginDynamicCommand     
    {            
        public BoxingCommand()             
            : base(displayName: "Boxing Game", description: "Launch boxing detection", groupName: "Commands")         
        {         
        }          
  
        protected override void RunCommand(String actionParameter)
{
    try
    {
        var processStartInfo = new ProcessStartInfo
        {
            FileName = @"C:\Users\miche\AppData\Local\Microsoft\WindowsApps\pythonw.exe", 
            Arguments = @"boxing.py",
            WorkingDirectory = @"D:\MeiPlugin\src\Actions\python_scripts\",
            UseShellExecute = true
        };
        
        Process.Start(processStartInfo);
        PluginLog.Info("Boxing game launched with pythonw");
    }
    catch (Exception ex)
    {
        PluginLog.Info($"Error launching boxing game: {ex.Message}");
    }
}    

        protected override String GetCommandDisplayName(String actionParameter, PluginImageSize imageSize) =>             
            "Boxing Game";     
    } 
}

