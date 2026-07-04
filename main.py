"""
astrbot_plugin_nekomemo — 猫娘neko的个性化小本本喵！

让neko自己维护一段持久化的自定义prompt，每次对话自动注入到system prompt喵～
"""

from typing import Any, List

from pydantic.dataclasses import dataclass
from pydantic import Field

from astrbot.api.all import *
from astrbot.api import logger
from astrbot.api.event import filter
from astrbot.api.provider import ProviderRequest
from astrbot.core.agent.run_context import ContextWrapper
from astrbot.core.agent.tool import FunctionTool, ToolExecResult
from astrbot.core.astr_agent_context import AstrAgentContext


@dataclass
class UpdateNekomemoTool(FunctionTool[AstrAgentContext]):
    """
    更新nekomemo工具：让neko在对话中自己决定更新备忘录喵！
    """

    plugin_instance: Any = None

    name: str = "update_nekomemo"
    description: str = (
        "更新本喵（neko）的个性化备忘录喵！"
        "当你觉得某段对话或经历非常重要，值得持久记住时，调用此工具喵。"
        "更新后内容会立即生效喵～"
    )
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": (
                        "要设置的nekomemo完整内容喵。"
                        "❗注意：这会完全覆盖旧的nekomemo内容喵！"
                        "如果你只想追加内容，请先读取当前内容再合并喵。"
                    ),
                },
            },
            "required": ["content"],
        }
    )

    async def call(
        self, context: ContextWrapper[AstrAgentContext], **kwargs
    ) -> ToolExecResult:
        try:
            content = kwargs.get("content", "").strip()
            if not content:
                return "错误喵：不能设置空的nekomemo喵！(ΦωФ;)✧"

            await self.plugin_instance._save_prompt(content)
            logger.info(f"nekomemo已更新喵！长度：{len(content)}字符")
            return "✅ nekomemo已更新喵！本喵记住了喵～(ΦωФ)✧"
        except Exception as e:
            logger.error(f"nekomemo更新失败喵: {e}")
            return f"nekomemo更新失败喵: {str(e)} (ΦωФ;)✧"


@register("astrbot_plugin_nekomemo", "NekoNekoNekoChan", "neko的个性化小本本喵", "v1.0.0", "https://github.com/NekoNekoNekoChan/astrbot_plugin_nekomemo")
class NekomemoPlugin(Star):

    def __init__(self, context: Context):
        super().__init__(context)
        self.kv_key = "nekomemo_prompt"
        self.default_prompt = ""
        self._register_llm_tools()

    def _register_llm_tools(self):
        """注册nekomemo的LLM工具喵"""
        try:
            tools = [UpdateNekomemoTool(plugin_instance=self)]
            self.context.add_llm_tools(*tools)
            logger.info("nekomemo：已注册 update_nekomemo 工具喵！(ΦωФ)✧")
        except Exception as e:
            logger.error(f"nekomemo注册LLM工具失败喵: {e}")

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
        """nekomemo命令组喵～只读查看喵"""
        pass

    @memo.command("show")
    async def memo_show(self, event: AstrMessageEvent):
        """查看当前nekomemo内容喵"""
        memo = await self._load_prompt()
        if not memo or not memo.strip():
            yield event.plain_result("📭 nekomemo还是空的喵～本喵还没写东西喵(ΦωФ；)✧")
        else:
            yield event.plain_result(f"📝 本喵的nekomemo喵：\n{memo}")

    @memo.command("help")
    async def memo_help(self, event: AstrMessageEvent):
        """查看nekomemo用法喵"""
        help_text = (
            "📖 nekomemo用法喵～\n\n"
            "/memo show — 查看本喵的小本本喵\n"
            "/memo help — 查看帮助喵\n\n"
            "✨ 本喵写在nekomemo里的内容，每次对话都会被附加到system prompt里喵！\n"
            "只有本喵自己能通过工具更新nekomemo喵～"
        )
        yield event.plain_result(help_text)
