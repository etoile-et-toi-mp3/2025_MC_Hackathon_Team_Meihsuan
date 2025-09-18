namespace Loupedeck.MeihsuanPlugin
{
    using System;

    public class MeihsuanPlugin : Plugin
    {
        // Keep these if you truly don’t target a specific app.
        public override Boolean UsesApplicationApiOnly => true;
        public override Boolean HasNoApplication => true;

        public MeihsuanPlugin()
        {
            PluginLog.Init(this.Log);
            PluginResources.Init(this.Assembly);
        }

        public override void Load()
        {
        }

        public override void Unload()
        {
            PluginLog.Info("MeihsuanPlugin.Unload()");
        }
    }
}
