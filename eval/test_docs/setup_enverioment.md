## git全局配置

这个配置及其重要，能解决git clone和brew install经常断链的问题
git config --global http.postBuffer 524288000
## 安装brew
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

## oh my zsh插件
```bash
sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
brew install zsh-autosuggestions zsh-syntax-highlighting
brew install --cask font-meslo-lg-nerd-font

# add to zshrc
source $(brew --prefix)/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh
source $(brew --prefix)/share/zsh-autosuggestions/zsh-autosuggestions.zsh
```

## 安装lua5.1，为neovim作准备
```bash
wget https://www.lua.org/ftp/lua-5.1.5.tar.gz
tar xzf lua-5.1.5.tar.gz
cd lua-5.1.5
make macosx
make INSTALL_TOP=/usr/local/lua@5.1 install
ln -s /usr/local/lua@5.1/bin/lua /usr/local/bin/lua5.1
```

## 设置主题

omz theme set agnoster

安装一些终端工具

```bash
brew install -v zellij
brew install -v yazi
brew install ripgrep 
brew install ast-grep fzf 
brew install -v neovim
brew install lazygit
brew install lazydocker
brew install zoxide
brew install eza
brew install ical-buddy
brew install keith/formulae/reminders-cli
brew install lua
brew install luarocks
brew install tree wget ncftp bat
brew install btop

# add to zshrc
eval "$(zoxide init zsh)"
alias cd=z
alias ls="eza --icons=always"

# 安装历史增强插件
brew install atuin
echo 'eval "$(atuin init zsh)"' >> ~/.zshrc
atuin import zsh # 导入历史

# mermaid 安装neovim可视化、图形化，安装后就能在neovim中看到图片
# 也可以解决 command not found: mmdc
npm install -g @mermaid-js/mermaid-cli
brew install imagemagick
```

## nvim设置

安装后执行:LazyHealth查看安装的错误

## [[安装配置p10k]]

## [[安装配置openvpn]]

## 设置SketchyBar

```bash
brew tap FelixKratz/formulae
brew install sketchybar
brew install --cask font-jetbrains-mono-nerd-font
mkdir -p ~/.config/sketchybar/plugins
cp $(brew --prefix)/share/sketchybar/examples/sketchybarrc ~/.config/sketchybar/sketchybarrc
cp -r $(brew --prefix)/share/sketchybar/examples/plugins/ ~/.config/sketchybar/plugins/
brew services start sketchybar
```

访问calendar的插件

```bash
brew install ical-buddy
brew install switchaudio-osx
```

### 安装配置yabai

关闭sip

[https://github.com/koekeishiya/yabai/wiki/Disabling-System-Integrity-Protection](https://github.com/koekeishiya/yabai/wiki/Disabling-System-Integrity-Protection)

1 进入recover模式
关机，然后开机按住电源键，直到进入安全模式

2 部分禁用sip
csrutil enable --without fs --without debug --without nvram

3 重启增加nvram参数
sudo nvram boot-args=-arm64e_preview_abi

4 再重启一次就可以load as了
```bash

brew install koekeishiya/formulae/yabai 
brew tap FelixKratz/formulae
brew install borders
brew install koekeishiya/formulae/skhd
skhd --start-service
# start yabai 
yabai --start-service 
# 写入sudo权限 
echo "$(whoami) ALL=(root) NOPASSWD: sha256:$(shasum -a 256 $(which yabai) | cut -d " " -f 1) $(which yabai) --load-sa" | sudo tee /private/etc/sudoers.d/yabai 
# 创建配置文件 
mkdir -p $HOME/.config/yabai 
cd $HOME/.config/yabai touch yabairc && chmod +x yabairc 
yabai -m signal --add event=dock_did_restart action="sudo yabai --load-sa" 
sudo yabai --load-sa
```

## docker配置

config file
```json
{
  "builder": {
    "gc": {
      "defaultKeepStorage": "20GB",
      "enabled": true
    }
  },
  "experimental": false,
  "registry-mirrors": [
    "https://docker.registry.cyou",
    "https://docker-cf.registry.cyou",
    "https://dockercf.jsdelivr.fyi",
    "https://docker.jsdelivr.fyi",
    "https://dockertest.jsdelivr.fyi",
    "https://mirror.aliyuncs.com",
    "https://dockerproxy.com",
    "https://mirror.baidubce.com",
    "https://docker.m.daocloud.io",
    "https://docker.nju.edu.cn",
    "https://docker.mirrors.sjtug.sjtu.edu.cn",
    "https://docker.mirrors.ustc.edu.cn",
    "https://mirror.iscas.ac.cn",
    "https://docker.rainbond.cc"
  ]
}
```

打开到 docker.destop > setup > resource
配置cpu、内存
Disk Image Location
/Volumes/data/working/docker/data/DockerDesktop

## [[python 环境初始化]]

## 配置输入法 [[rime安装和配置]]

## gemini cli 安装 https://geminicli.com
创建 api key https://aistudio.google.com/api-keys

在~/.zshrc文件中增加apikey配置

export GEMINI_API_KEY="xxxxx"

安装gemini cli的稳定版

```bash
npm install -g @google/gemini-cli@latest
```

## 命令行打印横幅

将下面的指令粘贴到zshrc里

```bash
function p10k-on-pre-prompt() {
  figlet "MacMini M4"
  p10k-on-pre-prompt() {}
}
```

## [[Claude Code安装和配置]]

## [[安装配置Karabiner]]

## [[安装Jenv管理jdk环境]]

## mysql命令行客户端安装

```bash
brew install mysql-client

# 把下面的命令放到.zshrc中
export PATH="/opt/homebrew/opt/mysql-client/bin:$PATH"
```


## 安装 google等宽字体

```bash
brew install --cask font-noto-sans-mono-cjk-sc
```

[[安装llmfit]]

## 另外一个看models和提供商的

```
brew install arimxyer/tap/models
```
