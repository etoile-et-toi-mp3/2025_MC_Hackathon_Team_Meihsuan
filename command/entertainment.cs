namespace Loupedeck.ExamplePlugin 
{     
    using System;     
    using System.Diagnostics;

    // This class implements a command that launches entertainment apps.      
    public class EntertainmentCommand : PluginDynamicCommand     
    {         
        // Initializes the command class.         
        public EntertainmentCommand()             
            : base(displayName: "Entertainment", description: "Launch YouTube, Spotify & Netflix", groupName: "Commands")         
        {         
        }          

        // This method is called when the user executes the command.         
        protected override void RunCommand(String actionParameter)         
        {             
            try 
            {
                // 開啟 YouTube
                Process.Start(new ProcessStartInfo
                {
                    FileName = "https://www.youtube.com",
                    UseShellExecute = true
                });

                // 開啟 Spotify (桌面版或網頁版)
                try
                {
                    Process.Start("spotify"); // 嘗試開啟桌面版
                }
                catch
                {
                    Process.Start(new ProcessStartInfo
                    {
                        FileName = "https://open.spotify.com",
                        UseShellExecute = true
                    });
                }

                // 開啟 Netflix
                Process.Start(new ProcessStartInfo
                {
                    FileName = "https://www.netflix.com",
                    UseShellExecute = true
                });

                PluginLog.Info("Entertainment apps launched successfully");
            }
            catch (Exception ex) 
            {
                PluginLog.Info($"Error launching entertainment apps: {ex.Message}");
            }
        }          

        // This method is called when Loupedeck needs to show the command on the console or the UI.         
        protected override String GetCommandDisplayName(String actionParameter, PluginImageSize imageSize) =>             
            "Entertainment";

    } 
}