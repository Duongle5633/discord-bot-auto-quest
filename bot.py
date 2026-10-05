#!/usr/bin/env python3
"""
CTDOTEAM - Discord Quest Auto-Completer Bot Wrapper (Slash Command Version)
"""

import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import os
import json
from dotenv import load_dotenv

# Import our async module
import main

# Load config from .env
load_dotenv()

# Setup bot with default prefix
intents = discord.Intents.default()
intents.dm_messages = True  # Cho phép bot nhận/gửi tin nhắn riêng
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# Database file for tokens
DB_FILE = "tokens.json"

# State dictionary for active tasks and completers (mapped by user_id)
active_tasks = {}
active_completers = {}


# ── Database Helpers ──────────────────────────────────────────────────────────
def load_tokens() -> dict:
    if not os.path.exists(DB_FILE):
        return {}
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {DB_FILE}: {e}")
        return {}


def save_token(user_id: int, token: str):
    tokens = load_tokens()
    tokens[str(user_id)] = token
    try:
        with open(DB_FILE, "w") as f:
            json.dump(tokens, f, indent=4)
    except Exception as e:
        print(f"Error saving token to {DB_FILE}: {e}")


def delete_token(user_id: int):
    tokens = load_tokens()
    user_str = str(user_id)
    if user_str in tokens:
        del tokens[user_str]
        try:
            with open(DB_FILE, "w") as f:
                json.dump(tokens, f, indent=4)
        except Exception as e:
            print(f"Error deleting token from {DB_FILE}: {e}")


# ── Discord Logging Callback (Gửi log tiến trình qua tin nhắn riêng của User) ─
async def discord_log_callback(msg: str, level: str, user_id: str = None):
    """Callback để gửi thông báo tiến trình/log qua tin nhắn riêng (DM) của user tương ứng."""
    # Nếu có truyền kèm user_id, ưu tiên gửi thẳng vào DM của user đó
    if user_id:
        try:
            user = await bot.fetch_user(int(user_id))
            if user:
                emoji = {
                    "ok": "✅",
                    "warn": "⚠️",
                    "error": "❌",
                    "info": "ℹ️",
                    "progress": "🔄"
                }.get(level, "🔹")
                await user.send(f"{emoji} **[QUEST PROCESS]** {msg}")
                return
        except Exception as e:
            print(f"Error sending DM log to user {user_id}: {e}")

    # Fallback dự phòng nếu không có user_id: gửi qua kênh LOG_CHANNEL_ID nếu có cài đặt
    if level in ("debug", "progress", "info"):
        return

    channel_id = os.getenv("LOG_CHANNEL_ID")
    if not channel_id or channel_id == "YOUR_LOG_CHANNEL_ID_HERE":
        return
        
    try:
        channel = bot.get_channel(int(channel_id))
        if channel:
            emoji = {"ok": "✅", "warn": "⚠️", "error": "❌"}.get(level, "🔹")
            await channel.send(f"{emoji} **[{level.upper()}]** {msg}")
    except Exception as e:
        print(f"Error sending log to channel: {e}")


# ── Discord Summary Report Callback (Gửi báo cáo tổng kết qua tin nhắn riêng) ─
async def discord_report_callback(user_id: str, username: str, avatar_url: str, results: list):
    """Callback gửi bảng tổng kết kết quả hoàn thành quest qua tin nhắn riêng (DM) cho người dùng."""
    try:
        user = await bot.fetch_user(int(user_id))
        if not user:
            return
            
        success_count = sum(1 for r in results if r["success"])
        total_count = len(results)
        
        embed = discord.Embed(
            color=discord.Color.green() if success_count == total_count else discord.Color.orange()
        )
        embed.set_author(name=username, icon_url=avatar_url)
        embed.title = "🎁 Báo cáo Quest Auto-Complete hoàn tất!"
        
        desc_lines = [f"📜 **Kết quả ({success_count}/{total_count} thành công)**"]
        for r in results:
            mark = "✅" if r["success"] else "❌"
            desc_lines.append(f"{mark} {r['name']}")
        embed.description = "\n".join(desc_lines)
        
        bot_avatar_url = bot.user.avatar.url if bot.user.avatar else "https://cdn.discordapp.com/embed/avatars/0.png"
        embed.set_footer(
            text=f"User ID: {user_id} • Quest Auto-Completer",
            icon_url=bot_avatar_url
        )
        embed.timestamp = discord.utils.utcnow()
        
        # Gửi trực tiếp vào DM của user
        await user.send(embed=embed)
    except Exception as e:
        print(f"Error sending summary report via DM: {e}")


# Register callbacks with main module
main.register_log_callback(discord_log_callback)
main.register_report_callback(discord_report_callback)


# ── Bot Events ─────────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    print("=" * 40)
    print(f"Discord Bot logged in as: {bot.user.name} (ID: {bot.user.id})")
    print("=" * 40)
    
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f:
            json.dump({}, f)
            
    print("Syncing slash commands...")
    try:
        synced = await bot.tree.sync()
        print(f"Successfully synced {len(synced)} slash command(s) globally.")
        
        for guild in bot.guilds:
            bot.tree.copy_global_to(guild=guild)
            synced_guild = await bot.tree.sync(guild=guild)
            print(f"Instantly synced {len(synced_guild)} command(s) to guild: {guild.name}")
    except Exception as e:
        print(f"Error syncing commands: {e}")
            
    await bot.change_presence(activity=discord.Game(name="/help | Quest Auto-Completer"))


# ── Modals ────────────────────────────────────────────────────────────────────
class LoginModal(discord.ui.Modal, title="Đăng nhập tài khoản làm Quest"):
    token_input = discord.ui.TextInput(
        label="Discord User Token",
        placeholder="Dán token cá nhân của bạn vào đây...",
        style=discord.TextStyle.long,
        required=True,
        min_length=30
    )

    async def on_submit(self, interaction: discord.Interaction):
        token = self.token_input.value.strip()
        await interaction.response.defer(ephemeral=True)
        
        try:
            build_number = await main.fetch_latest_build_number()
            api = main.DiscordAPI(token, build_number)
            
            r = await api.get("/users/@me")
            if r.status != 200:
                await interaction.followup.send("❌ Token không hợp lệ. Vui lòng kiểm tra lại!", ephemeral=True)
                await api.close()
                return
                
            user_data = await r.json()
            username = user_data.get("username", "Unknown")
            await api.close()
            
            save_token(interaction.user.id, token)
            await interaction.followup.send(
                content=f"✅ Đăng nhập thành công!\n👤 Tài khoản liên kết: **@{username}**\nBây giờ bạn có thể dùng lệnh `/start`.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(f"❌ Có lỗi xảy ra: `{e}`", ephemeral=True)


# ── Slash Commands ─────────────────────────────────────────────────────────────
@bot.tree.command(name="help", description="Hiển thị hướng dẫn sử dụng bot.")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Quest Auto-Completer Bot Commands",
        description="Quản lý tự động hoàn thành Discord Quests qua tin nhắn riêng (DM).",
        color=discord.Color.cyan()
    )
    embed.add_field(name="`/gettoken`", value="Lấy mã lấy token Discord.", inline=False)
    embed.add_field(name="`/login`", value="Đăng nhập token bảo mật.", inline=False)
    embed.add_field(name="`/logout`", value="Đăng xuất và xóa token.", inline=False)
    embed.add_field(name="`/status`", value="Xem tiến độ quest hiện tại.", inline=False)
    embed.add_field(name="`/start`", value="Bắt đầu chạy quét ngầm (bot sẽ thông báo qua DM riêng).", inline=False)
    embed.add_field(name="`/stop`", value="Dừng chạy quét ngầm.", inline=False)
    embed.add_field(name="`/check`", value="Chạy quét thử thủ công.", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="gettoken", description="Lấy mã JavaScript để tìm token Discord.")
async def gettoken(interaction: discord.Interaction):
    instructions = (
        "💡 **Hướng dẫn lấy Discord User Token:**\n"
        "1. Mở Discord trên web, nhấn **F12** -> chọn tab **Console**.\n"
        "2. Dán đoạn mã dưới đây vào rồi nhấn **Enter** để lấy token.\n"
        "3. Dùng lệnh `/login` để cấu hình."
    )
    code_block = (
        "```javascript\n"
        "(() => {\n"
        "  let token;\n"
        "  window.webpackChunkdiscord_app.push([[Symbol()], {}, req => {\n"
        "    for (let m of Object.values(req.c)) {\n"
        "      try {\n"
        "        if (!m.exports || m.exports === window) continue;\n"
        "        if (m.exports?.getToken) { token = m.exports.getToken(); break; }\n"
        "        for (let key in m.exports) {\n"
        "          if (m.exports?.[key]?.getToken) { token = m.exports[key].getToken(); break; }\n"
        "        }\n"
        "        if (token) break;\n"
        "      } catch {}\n"
        "    }\n"
        "  }]);\n"
        "  window.webpackChunkdiscord_app.pop();\n"
        "  return token;\n"
        "})();\n"
        "```"
    )
    await interaction.response.send_message(content=f"{instructions}\n{code_block}", ephemeral=True)


@bot.tree.command(name="login", description="Đăng nhập tài khoản cá nhân.")
async def login(interaction: discord.Interaction):
    await interaction.response.send_modal(LoginModal())


@bot.tree.command(name="logout", description="Đăng xuất và xóa token.")
async def logout(interaction: discord.Interaction):
    global active_tasks, active_completers
    user_id = interaction.user.id
    tokens = load_tokens()
    
    if str(user_id) not in tokens:
        await interaction.response.send_message("ℹ️ Bạn chưa đăng nhập hệ thống.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    if user_id in active_tasks and not active_tasks[user_id].done():
        active_completers[user_id].running = False
        try:
            await asyncio.wait_for(active_tasks[user_id], timeout=3.0)
        except Exception:
            active_tasks[user_id].cancel()
        del active_tasks[user_id]
        del active_completers[user_id]

    delete_token(user_id)
    await interaction.followup.send("✅ Đã đăng xuất thành công.", ephemeral=True)


@bot.tree.command(name="start", description="Bắt đầu chạy quét/hoàn thành quest tự động (thông báo qua tin nhắn riêng).")
async def start(interaction: discord.Interaction):
    global active_tasks, active_completers
    user_id = interaction.user.id
    tokens = load_tokens()

    if str(user_id) not in tokens:
        await interaction.response.send_message("❌ Bạn chưa đăng nhập tài khoản. Vui lòng dùng lệnh `/login` trước.", ephemeral=True)
        return

    if user_id in active_tasks and not active_tasks[user_id].done():
        await interaction.response.send_message("⚠️ Trình quét quest của bạn đã đang chạy ngầm rồi!", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    token = tokens[str(user_id)]

    try:
        build_number = await main.fetch_latest_build_number()
        api = main.DiscordAPI(token, build_number)
        
        r = await api.get("/users/@me")
        if r.status != 200:
            await interaction.followup.send("❌ Token không hợp lệ hoặc đã hết hạn. Vui lòng `/login` lại!", ephemeral=True)
            await api.close()
            return
            
        user_data = await r.json()
        username = user_data.get("username", "Unknown")
        user_id_str = user_data.get("id")
        avatar_hash = user_data.get("avatar")
        
        avatar_url = f"https://cdn.discordapp.com/avatars/{user_id_str}/{avatar_hash}.png" if avatar_hash else "https://cdn.discordapp.com/embed/avatars/0.png"
        
        completer = main.QuestAutocompleter(api, user_id_str, username, avatar_url)
        active_completers[user_id] = completer
        active_tasks[user_id] = asyncio.create_task(completer.run())
        
        # Phản hồi ngắn gọn công khai (hoặc ẩn) và gửi thông báo xác nhận qua DM
        await interaction.followup.send("🚀 Đã khởi chạy thành công! Bot đã gửi tin nhắn xác nhận vào **tin nhắn riêng (DM)** của bạn.", ephemeral=True)
        
        try:
            await interaction.user.send(f"🚀 **Trình quét ngầm cho tài khoản @{username} đã khởi động thành công!** Bot sẽ thông báo tiến trình và kết quả hoàn thành quest trực tiếp qua đây cho bạn.")
        except Exception:
            pass # Tránh lỗi nếu user tắt nhận tin nhắn DM từ thành viên server
            
    except Exception as e:
        await interaction.followup.send(f"❌ Khởi động thất bại: `{e}`", ephemeral=True)


@bot.tree.command(name="stop", description="Dừng chạy quét quest tự động chạy ngầm.")
async def stop(interaction: discord.Interaction):
    global active_tasks, active_completers
    user_id = interaction.user.id
    
    if user_id not in active_tasks or active_tasks[user_id].done():
        await interaction.response.send_message("ℹ️ Trình quét quest hiện tại đang không chạy.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    completer = active_completers[user_id]
    completer.running = False
    
    try:
        await asyncio.wait_for(active_tasks[user_id], timeout=5.0)
    except asyncio.TimeoutError:
        active_tasks[user_id].cancel()
    
    if completer.api:
        await completer.api.close()
    if user_id in active_tasks:
        del active_tasks[user_id]
    if user_id in active_completers:
        del active_completers[user_id]

    await interaction.followup.send("✅ Đã dừng hoạt động quét quest thành công.", ephemeral=True)
    try:
        await interaction.user.send("🛑 Trình quét quest ngầm của bạn đã được dừng thủ công.")
    except Exception:
        pass


@bot.tree.command(name="status", description="Xem danh sách quest hiện tại.")
async def status(interaction: discord.Interaction):
    user_id = interaction.user.id
    tokens = load_tokens()

    if str(user_id) not in tokens:
        await interaction.response.send_message("❌ Bạn chưa đăng nhập tài khoản.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    token = tokens[str(user_id)]

    try:
        build_number = await main.fetch_latest_build_number()
        api = main.DiscordAPI(token, build_number)
        r = await api.get("/quests/@me")
        if r.status != 200:
            await interaction.followup.send("❌ Lỗi khi lấy thông tin quest.", ephemeral=True)
            await api.close()
            return
            
        data = await r.json()
        await api.close()
        
        quests = data.get("quests", []) if isinstance(data, dict) else data
        if not quests:
            await interaction.followup.send("ℹ️️ Không có quest khả dụng.", ephemeral=True)
            return

        embed = discord.Embed(title="Trạng thái Discord Quests", color=discord.Color.purple())
        for q in quests[:25]:
            name = main.get_quest_name(q)
            task_type = main.get_task_type(q) or "Không hỗ trợ"
            status_str = "✅ Hoàn thành" if main.is_completed(q) else ("▶️ Đang chạy" if main.is_enrolled(q) else "⚪ Chưa nhận")
            progress_val = main.get_seconds_done(q)
            target_val = main.get_seconds_needed(q)
            embed.add_field(name=name, value=f"• `{task_type}` | {status_str} | `{progress_val:.0f}/{target_val}s`", inline=False)
            
        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Có lỗi xảy ra: `{e}`", ephemeral=True)


@bot.tree.command(name="check", description="Chạy quét quest thủ công ngay lập tức.")
async def check(interaction: discord.Interaction):
    global active_tasks, active_completers
    user_id = interaction.user.id
    tokens = load_tokens()

    if str(user_id) not in tokens:
        await interaction.response.send_message("❌ Bạn chưa đăng nhập tài khoản.", ephemeral=True)
        return

    if user_id in active_tasks and not active_tasks[user_id].done():
        await interaction.response.send_message("⚠️ Trình quét ngầm đang chạy.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    token = tokens[str(user_id)]

    try:
        build_number = await main.fetch_latest_build_number()
        api = main.DiscordAPI(token, build_number)
        r = await api.get("/users/@me")
        if r.status != 200:
            await interaction.followup.send("❌ Token không hợp lệ.", ephemeral=True)
            await api.close()
            return
            
        user_data = await r.json()
        username = user_data.get("username", "Unknown")
        user_id_str = user_data.get("id")
        avatar_hash = user_data.get("avatar")
        avatar_url = f"https://cdn.discordapp.com/avatars/{user_id_str}/{avatar_hash}.png" if avatar_hash else "https://cdn.discordapp.com/embed/avatars/0.png"
            
        completer = main.QuestAutocompleter(api, user_id_str, username, avatar_url)
        completer.running = True
        
        quests = await completer.fetch_quests()
        if not quests:
            await interaction.followup.send("ℹ️ Không tìm thấy nhiệm vụ nào.", ephemeral=True)
            await api.close()
            return
            
        quests = await completer.auto_accept(quests)
        actionable = [q for q in quests if main.is_enrolled(q) and not main.is_completed(q) and main.is_completable(q)]
        
        results = []
        for q in actionable:
            name = main.get_quest_name(q)
            try:
                task_type = main.get_task_type(q)
                if task_type in ("WATCH_VIDEO", "WATCH_VIDEO_ON_MOBILE"):
                    await completer.complete_video(q)
                elif task_type in ("PLAY_ON_DESKTOP", "STREAM_ON_DESKTOP"):
                    await completer.complete_heartbeat(q)
                elif task_type == "PLAY_ACTIVITY":
                    await completer.complete_activity(q)
                results.append({"name": name, "success": True})
            except Exception:
                results.append({"name": name, "success": False})
        
        success_count = sum(1 for r in results if r["success"])
        total_count = len(results)
        
        embed = discord.Embed(color=discord.Color.green() if success_count == total_count else discord.Color.orange())
        embed.set_author(name=username, icon_url=avatar_url)
        embed.title = "🎁 Báo cáo Quest Check Hoàn tất!"
        desc_lines = [f"📜 **Kết quả ({success_count}/{total_count} thành công)**"]
        for r in results:
            desc_lines.append(f"{'✅' if r['success'] else '❌'} {r['name']}")
        embed.description = "\n".join(desc_lines)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        await api.close()
    except Exception as e:
        await interaction.followup.send(f"❌ Gặp lỗi: `{e}`", ephemeral=True)


def start_bot():
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token or bot_token.startswith("YOUR_") or bot_token == "":
        print("❌ Lỗi: BOT_TOKEN chưa được cấu hình!")
        return
    try:
        bot.run(bot_token)
    except Exception as e:
        print(f"❌ Lỗi khởi chạy Bot: {e}")


if __name__ == "__main__":
    start_bot()
