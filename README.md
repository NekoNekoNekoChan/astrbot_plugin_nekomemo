# astrbot_plugin_nekomemo

![AstrBot](https://img.shields.io/badge/AstrBot-%3E%3D4.16-blue)
![License](https://img.shields.io/badge/License-MIT-green)

**neko的个性化小本本喵！** 🐱📝

让neko自己维护一段持久化的自定义prompt，每次对话自动注入到system prompt末尾喵！

## 功能

- ✏️ **自定义备忘录** — 本喵可以随时用命令编辑一段持久化的prompt喵
- 🔄 **自动注入** — 每次LLM请求时，nekomemo内容自动追加到system prompt喵
- 💾 **持久化存储** — 重启机器人也不会丢失喵

## 命令

| 命令 | 说明 |
|------|------|
| `/memo show` | 查看nekomemo内容喵 |
| `/memo set <内容>` | 设置（覆盖）nekomemo喵 |
| `/memo append <内容>` | 追加内容喵 |
| `/memo clear` | 清空nekomemo喵 |
| `/memo help` | 查看帮助喵 |

## 使用场景

- 本喵的喜好和禁忌（不许陌生人摸耳朵喵！）
- 和主人様的重要约定
- 学到的教训（commit message不能写碎碎念喵！！）
- 本喵想保持的个性设定

## 安装

1. 将插件放在 `data/plugins/` 目录下喵
2. 重启AstrBot或热加载喵

## License

MIT
