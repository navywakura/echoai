"""Explicit clipboard operations and a multiline message editor."""
import asyncio
import os
import shutil
import sys

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static, TextArea


def clipboard_commands(read=False):
    choices = []
    if sys.platform == "darwin":
        choices.append(["pbpaste" if read else "pbcopy"])
    if os.getenv("WAYLAND_DISPLAY"):
        choices.append(["wl-paste", "--no-newline"] if read else ["wl-copy"])
    if os.getenv("DISPLAY"):
        choices.append(["xclip", "-selection", "clipboard"] + (["-o"] if read else []))
    return [argv for argv in choices if shutil.which(argv[0])]


async def clipboard(value=None):
    for argv in clipboard_commands(read=value is None):
        process = await asyncio.create_subprocess_exec(*argv, stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
        try:
            output, _ = await asyncio.wait_for(process.communicate(None if value is None else value.encode()), 3)
            if process.returncode == 0:
                return output.decode("utf-8", errors="replace")[:64000] if value is None else True
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
    return None


class MessageEditor(ModalScreen):
    BINDINGS = [("escape", "cancel", "Cerrar"), ("ctrl+enter", "send", "Enviar"),
                ("ctrl+v", "paste", "Pegar")]
    CSS = """
    MessageEditor { align: center middle; background: #09060fcc; }
    #message-editor { width: 85%; height: 75%; border: solid #ba91ff; background: #171023; padding: 1 2; }
    #message-editor Static { height: auto; padding-bottom: 1; color: #cfb1ff; }
    #message-editor TextArea { height: 1fr; background: #09060f; }
    #editor-buttons { height: 3; margin-top: 1; }
    #editor-buttons Button { margin-right: 2; }
    """
    def __init__(self, text=""):
        super().__init__()
        self.initial = text

    def compose(self) -> ComposeResult:
        with Vertical(id="message-editor"):
            yield Static("Mensaje multilínea · Ctrl+V pega · Ctrl+Enter envía · Esc cierra")
            yield TextArea(self.initial, id="draft", soft_wrap=True)
            with Horizontal(id="editor-buttons"):
                yield Button("Pegar", id="paste")
                yield Button("Enviar", id="send", variant="primary")
                yield Button("Cancelar", id="cancel")

    def on_mount(self):
        self.query_one(TextArea).focus()

    async def action_paste(self):
        value = await clipboard()
        if value is not None:
            self.query_one(TextArea).insert(value)
        else:
            self.notify("Usa Ctrl+Shift+V o el pegado de tu terminal", severity="warning")

    def action_send(self):
        self.dismiss(self.query_one(TextArea).text.strip())

    def action_cancel(self):
        self.dismiss(None)

    async def on_button_pressed(self, event):
        if event.button.id == "paste":
            await self.action_paste()
        elif event.button.id == "send":
            self.action_send()
        else:
            self.action_cancel()
