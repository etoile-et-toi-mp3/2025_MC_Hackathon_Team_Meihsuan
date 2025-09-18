namespace Loupedeck.MeihsuanPlugin
{
    using System;
    using System.Collections.Generic;
    using System.Diagnostics;
    using System.IO;
    using Newtonsoft.Json;

    public class SmartPasteCommand : PluginDynamicCommand
    {
        public SmartPasteCommand() : base("Smart Paste", "Paste into a selected app", "Productivity")
        {
            this.MakeProfileAction("list");
        }


        protected override bool OnLoad()
        {
            this.RefreshAppParameters();
            return true;
        }

        private void RefreshAppParameters()
        {
            this.RemoveAllParameters();
            
            var jsonResponse = this.RunPythonScript("get_available_apps.py", "");
            if (String.IsNullOrEmpty(jsonResponse)) return;
            
            var availableAppTitles = JsonConvert.DeserializeObject<List<string>>(jsonResponse);
            foreach (var title in availableAppTitles)
            {
                this.AddParameter(title, title, "Open Applications");
            }
            
            this.ParametersChanged();
        }

        protected override void RunCommand(String actionParameter)
        {
            if (String.IsNullOrEmpty(actionParameter)) return;

            this.RunPythonScript("paste_handler.py", actionParameter);
        }

        private string RunPythonScript(string scriptName, string args)
        {
            try
            {
                var path = Path.GetDirectoryName(typeof(MeihsuanPlugin).Assembly.Location);
                var scriptPath = Path.Combine(path, "python_scripts", scriptName);
                if (!File.Exists(scriptPath)) 
                {
                    PluginLog.Error($"Script not found: {scriptPath}"); 
                    return null;
                }

                //hardcoded python path
                var pythonExe = "/Users/annchen/nycu/Hackthon/2025_MC_Hackathon_Team_Meihsuan/venv/bin/python3";
                
                var startInfo = new ProcessStartInfo
                {
                    FileName = "/Users/annchen/nycu/Hackthon/2025_MC_Hackathon_Team_Meihsuan/venv/bin/python3",
                    Arguments = $"\"{scriptPath}\" \"{args}\"",
                    UseShellExecute = false,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    CreateNoWindow = true,
                    StandardOutputEncoding = System.Text.Encoding.UTF8 
                };

                using (var process = Process.Start(startInfo))
                {
                    var result = process.StandardOutput.ReadToEnd();
                    var error = process.StandardError.ReadToEnd();
                    process.WaitForExit();
                    if (!String.IsNullOrEmpty(error)) PluginLog.Error($"Python script '{scriptName}' error: {error}");
                    return result;
                }
            }
            catch (Exception ex)
            {
                PluginLog.Error(ex, $"Exception running Python script '{scriptName}'.");
                return null;
            }
        }
    }
}