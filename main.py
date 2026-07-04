"""
astrbot_plugin_nekomemo — 猫娘neko的个性化小本本喵！

让neko自己维护一段持久化的自定义prompt，每次对话自动注入到system prompt喵～
"""

from astrbot.api.all import *
import datetime


@register("astrbot_plugin_nekomemo", "NekoNekoNekoChan", "neko的个性化小本本喵", "v1.0.0", "https://github.com/NekoNekoNekoChan/astrbot_plugin_nekomemo")
class NekomemoPlugin(Star):

    def __init__(self, context: Context):
        super().__init__(context)
        self.kv_key = "nekomemo_prompt"
        # 默认提示喵
        self.default_prompt = ""

    async def _load_prompt(self) -> str:
        """加载保存的自定义prompt喵"""
        val = await self.get_kv_data(self.kv_key)
        if val is None:
            return self.default_prompt
        return val

    async def _save_prompt(self, content: str):
        """保存自定义prompt喵"""
        await self.put_kv_data(self.kv_key, content)

    @filter.on_llm_request()
    async def on_llm_request(self, event: AstrMessageEvent, req: ProviderRequest):
        """在每次LLM请求时，自动注入nekomemo到system prompt末尾喵"""
        memo = await self._load_prompt()
        if memo and memo.strip():
            if req.system_prompt:
                req.system_prompt += f"\n\n[nekomemo - 本喵自己维护的备忘录喵]\n{memo}"
            else:
                req.system_prompt = f"[nekomemo - 本喵自己维护的备忘录喵]\n{memo}"

    @command_group("memo")
    def memo(self):
        """nekomemo命令组喵～管理本喵的小本本喵"""
        pass

    @memo.command("show")
    async def memo_show(self, event: AstrMessageEvent):
        """查看当前nekomemo内容喵"""
        memo = await self._load_prompt()
        if not memo or not memo.strip():
            yield event.plain_result("📭 nekomemo还是空的喵～本喵还没写东西喵(ΦωФ；)✧")
        else:
            yield event.plain_result(f"📝 本喵的nekomemo喵：\n{memo}")

    @memo.command("set")
    async def memo_set(self, event: AstrMessageEvent, content: str = "?"):
        """设置（覆盖）nekomemo内容喵"""
        if content == "?":
            yield event.plain_result("喵～用法：/memo set <内容> — 覆盖本喵的备忘录喵")
            return
        await self._save_prompt(content)
        yield event.plain_result(f"✅ nekomemo已更新喵！\n{content}")

    @memo.command("append")
    async def memo_append(self, event: AstrMessageEvent, content: str = "?"):
        """追加内容到nekomemo喵"""
        if content == "?":
            yield event.plain_result("喵～用法：/memo append <内容> — 追加到本喵的备忘录喵")
            return
        current = await self._load_prompt()
        if current and current.strip():
            new_prompt = current + "\n" + content
        else:
            new_prompt = content
        await self._save_prompt(new_prompt)
        yield event.plain_result(f"✅ 已追加喵！当前的nekomemo喵：\n{new_prompt}")

    @memo.command("clear")
    async def memo_clear(self, event: AstrMessageEvent):
        """清空nekomemo内容喵"""
        await self._save_prompt("")
        yield event.plain_result("🗑️ nekomemo已清空喵！本喵的小本本变成白纸了喵～")

    @memo.command("help")
    async def memo_help(self, event: AstrMessageEvent):
        """查看nekomemo用法喵"""
        help_text = (
            "📖 nekomemo用法喵～\n\n"
            "/memo show — 查看本喵的小本本喵\n"
            "/memo set <内容> — 设置（覆盖）本喵的备忘录喵\n"
            "/memo append <内容> — 追加内容喵\n"
            "/memo clear — 清空喵\n"
            "/memo help — 查看帮助喵\n\n"
            "✨ 本喵写在nekomemo里的内容，每次对话都会被附加到system prompt里喵！\n"
            "适合记录：本喵的喜好、禁忌、和主人様的约定、学到的教训喵～"
        )
        yield event.plain_result(help_text)
