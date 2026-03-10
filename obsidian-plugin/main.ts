import { Plugin, TFile, debounce, Setting, TAbstractFile, PluginSettingTab, App, Notice } from "obsidian";
import { exec } from "child_process";

interface PluginSettings {
  repository: string;
  debounceMs: number;
}

const DEFAULT_SETTINGS: PluginSettings = {
  repository: "my-obsidian",
  debounceMs: 1000,
};

export default class FileHookPlugin extends Plugin {

  settings: PluginSettings = DEFAULT_SETTINGS;

  async onload() {

    await this.loadSettings();

    this.addSettingTab(new SettingTab(this.app, this));

    const debouncedModify = debounce((file: TFile, action: string) => {
      this.runSync(file.path, 'debouncedModify');
    }, this.settings.debounceMs, true);

    // modify
    this.registerEvent(
      this.app.vault.on("modify", (file: TAbstractFile) => {
        if (this.shouldHandle(file)) {
          debouncedModify(file as TFile, 'modify');
        }
      })
    );

    // 不必监听create事件，因为create还没有真正创建有用的内容
    // this.registerEvent(
    //   this.app.vault.on("create", (file: TAbstractFile) => {
    //     if (this.shouldHandle(file)) {
    //       this.runSync((file as TFile).path, 'create');
    //     }
    //   })
    // );

    // delete
    this.registerEvent(
      this.app.vault.on("delete", (file: TAbstractFile) => {
        if (this.shouldHandle(file)) {
          debouncedModify((file as TFile), 'delete');
        }
      })
    );

    // rename
    this.registerEvent(
      this.app.vault.on("rename", (file: TAbstractFile, oldPath: string) => {
        if (this.shouldHandle(file)) {
          debouncedModify((file as TFile), 'rename');
        }
      })
    );
  }

  shouldHandle(file: TAbstractFile): boolean {

    if (!(file instanceof TFile)) return false;

    if (!file.path.endsWith(".md")) return false;

    if (file.path.startsWith(".obsidian")) return false;

    return true;
  }

  runSync(filePath: string, action: string) {
    const cmd = `~/.local/bin/memory sync -r ${this.settings.repository}`;

    console.log(`[My Memory Hook] Syncing repository: ${this.settings.repository}`);
    new Notice(`[My Memory Hook] Syncing...`, 2000);

    exec(cmd, (err: Error | null, stdout: string, stderr: string) => {

      if (err) {
        console.error("[My Memory Hook] Sync failed:", err);
        new Notice(`[My Memory Hook] Sync failed: ${err.message}`, 5000);
        return;
      }

      if (stdout) {
        console.log("[My Memory Hook]", stdout);
        // 提取关键信息显示
        const lines = stdout.trim().split("\n");
        const lastLine = lines[lines.length - 1];
        new Notice(`[My Memory Hook] ${lastLine}`, 3000);
      }
      if (stderr) console.error("[My Memory Hook]", stderr);
    });
  }

  async loadSettings() {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
  }

  async saveSettings() {
    await this.saveData(this.settings);
  }
}

class SettingTab extends PluginSettingTab {
  plugin: FileHookPlugin;

  constructor(app: App, plugin: FileHookPlugin) {
    super(app, plugin);
    this.plugin = plugin;
  }

  display() {
    this.containerEl.empty();

    new Setting(this.containerEl)
      .setName("Repository name")
      .setDesc("The repository to sync with (e.g., my-obsidian)")
      .addText((text) =>
        text
          .setPlaceholder("my-obsidian")
          .setValue(this.plugin.settings.repository)
          .onChange(async (value) => {
            this.plugin.settings.repository = value;
            await this.plugin.saveSettings();
          })
      );

    new Setting(this.containerEl)
      .setName("Debounce (ms)")
      .setDesc("Delay before triggering sync after file changes")
      .addText((text) =>
        text
          .setPlaceholder("1000")
          .setValue(String(this.plugin.settings.debounceMs))
          .onChange(async (value) => {
            const ms = parseInt(value, 10);
            if (!isNaN(ms) && ms > 0) {
              this.plugin.settings.debounceMs = ms;
              await this.plugin.saveSettings();
            }
          })
      );
  }
}
