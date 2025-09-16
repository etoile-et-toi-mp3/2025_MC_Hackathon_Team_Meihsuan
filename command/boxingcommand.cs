namespace Loupedeck.ExamplePlugin 
{     
    using System;     
    using System.Diagnostics;
   
    public class CounterCommand : PluginDynamicCommand     
    {            
        public CounterCommand()             
            : base(displayName: "Boxing Game", description: "Launch boxing detection", groupName: "Commands")         
        {         
        }          
  
        protected override void RunCommand(String actionParameter)         
        {             
            try 
            {
                Process.Start(@"C:\Path\To\Python\pythonw.exe", @"C:\Users\miche\Downloads\gesture.py");
                PluginLog.Info("Boxing game launched successfully");
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

