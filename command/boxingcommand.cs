namespace Loupedeck.ExamplePlugin 
{     
    using System;     
    using System.Diagnostics;

    // This class implements a command that launches boxing game.      
    public class CounterCommand : PluginDynamicCommand     
    {         
        // Initializes the command class.         
        public CounterCommand()             
            : base(displayName: "Boxing Game", description: "Launch boxing detection", groupName: "Commands")         
        {         
        }          

        // This method is called when the user executes the command.         
        protected override void RunCommand(String actionParameter)         
        {             
            try 
            {
                Process.Start("python", @"C:\Users\miche\Downloads\gesture.py");
                PluginLog.Info("Boxing game launched successfully");
            }
            catch (Exception ex) 
            {
                PluginLog.Info($"Error launching boxing game: {ex.Message}");
            }
        }          

        // This method is called when Loupedeck needs to show the command on the console or the UI.         
        protected override String GetCommandDisplayName(String actionParameter, PluginImageSize imageSize) =>             
            "Boxing Game";     
    } 
}

