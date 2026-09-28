#!/usr/bin/env python3
"""
Discord Voice Hanger / Treo Voice 24/7
Tự động đăng nhập bằng User Token, nhận ID Kênh Voice (hoặc chọn từ danh sách Server) để treo 24/7.
Hỗ trợ:
- Nhận Token trực tiếp hoặc từ file/môi trường (tokens.json, .env, token.txt).
- Nhập trực tiếp ID Kênh Voice (dán ID là vào thẳng, không cần tìm qua server).
- Duyệt danh sách Server & Kênh Voice trực quan nếu chưa có ID.
- Tự động kết nối lại 24/7 (Anti-Kick / Auto-Reconnect khi mất mạng, bị kick, hoặc bị chuyển phòng AFK).
- Tùy chọn tự tắt Mic (Self-Mute), tự tắt Tai nghe (Self-Deafen), Camera (Self-Video).
- Tùy chỉnh trạng thái hiện diện (Custom Status).
- Lưu cấu hình vào file voice_config.json để tự động chạy các lần sau.
"""

import os
import sys
import json
import time
import asyncio
import argparse
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple

# Tắt log mặc định quá chi tiết của discord
import logging
logging.getLogger("discord").setLevel(logging.WARNING)
logging.getLogger("discord.http").setLevel(logging.WARNING)
logging.getLogger("discord.client").setLevel(logging.WARNING)

# Thiết lập UTF-8 cho Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
except ImportError:
    class Fore:
        GREEN = ""
        CYAN = ""
        YELLOW = ""
        RED = ""
        MAGENTA = ""
        WHITE = ""
        BLUE = ""
        RESET = ""
    class Style:
        BRIGHT = ""
        DIM = ""
        RESET_ALL = ""

try:
    import discord
except ImportError:
    print("Vui lòng cài đặt thư viện cần thiết:")
    print("pip install discord.py-self PyNaCl colorama python-dotenv")
    sys.exit(1)

from dotenv import load_dotenv
load_dotenv()

# File cấu hình mặc định
CONFIG_FILE = "voice_config.json"


# ── Tiện ích Giao diện & Hiển thị ─────────────────────────────────────────────
def print_banner():
    banner = f"""{Fore.CYAN}{Style.BRIGHT}
======================================================================
               DISCORD VOICE HANGER - TREO VOICE 24/7                
            Tu dong duy tri trang thai ket noi Voice lien tuc        
======================================================================{Style.RESET_ALL}"""
    print(banner)
    print(f"{Fore.YELLOW}[!] LƯU Ý:{Style.RESET_ALL} Việc sử dụng User Token tự động hóa vi phạm Discord ToS.")
    print(f"    Vui lòng sử dụng cẩn trọng và tự chịu trách nhiệm đối với tài khoản.\n")


def log(msg: str, level: str = "info"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    badges = {
        "info": f"{Fore.CYAN}[INFO]{Style.RESET_ALL}",
        "ok": f"{Fore.GREEN}{Style.BRIGHT}[ OK ]{Style.RESET_ALL}",
        "warn": f"{Fore.YELLOW}[WARN]{Style.RESET_ALL}",
        "err": f"{Fore.RED}{Style.BRIGHT}[FAIL]{Style.RESET_ALL}",
        "time": f"{Fore.MAGENTA}[TIME]{Style.RESET_ALL}",
    }
    badge = badges.get(level, f"[{level.upper()}]")
    print(f"{Style.DIM}{timestamp}{Style.RESET_ALL} {badge} {msg}")


def format_duration(seconds: float) -> str:
    td = timedelta(seconds=int(seconds))
    days = td.days
    hours, remainder = divmod(td.seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    parts = []
    if days > 0:
        parts.append(f"{days} ngày")
    if hours > 0 or days > 0:
        parts.append(f"{hours:02d} giờ")
    parts.append(f"{minutes:02d} phút")
    parts.append(f"{secs:02d} giây")
    return " ".join(parts)


async def ainput(prompt: str = "") -> str:
    """Đọc input người dùng từ terminal mà không làm block asyncio loop."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, input, prompt)


# ── Quản lý Cấu hình & Nạp Token ─────────────────────────────────────────────
def load_saved_config(config_path: str = CONFIG_FILE) -> Dict[str, Any]:
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log(f"Lỗi khi đọc file cấu hình {config_path}: {e}", "warn")
    return {}


def save_config(data: Dict[str, Any], config_path: str = CONFIG_FILE):
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        log(f"Đã lưu cấu hình vào {Fore.GREEN}{config_path}{Style.RESET_ALL}", "ok")
    except Exception as e:
        log(f"Không thể lưu cấu hình: {e}", "err")


def get_tokens_from_tokens_json() -> Dict[str, str]:
    if os.path.exists("tokens.json"):
        try:
            with open("tokens.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
    return {}


def get_token_from_env_or_files() -> Optional[str]:
    # 1. Biến môi trường
    env_token = os.getenv("USER_TOKEN") or os.getenv("DISCORD_TOKEN")
    if env_token:
        return env_token.strip().strip('"').strip("'")
    
    # 2. File token.txt
    if os.path.exists("token.txt"):
        try:
            with open("token.txt", "r", encoding="utf-8") as f:
                t = f.read().strip().strip('"').strip("'")
                if t:
                    return t
        except Exception:
            pass

    return None


# ── Trình Treo Voice Chính (Voice Hanger) ─────────────────────────────────────
class VoiceHanger:
    def __init__(self, config: Dict[str, Any], config_path: str = CONFIG_FILE):
        self.config = config
        self.config_path = config_path
        self.token: str = config.get("token", "")
        self.guild_id: Optional[int] = config.get("guild_id")
        self.channel_id: Optional[int] = config.get("channel_id")
        self.self_mute: bool = config.get("self_mute", True)
        self.self_deaf: bool = config.get("self_deaf", True)
        self.self_video: bool = config.get("self_video", False)
        self.auto_reconnect: bool = config.get("auto_reconnect", True)
        self.custom_status: str = config.get("custom_status", "Treo Voice 24/7")

        self.voice_client: Optional[discord.VoiceClient] = None
        self.target_channel: Optional[discord.VoiceChannel] = None
        self.start_time: Optional[float] = None
        self.is_connected = False
        self.is_reconnecting = False
        self.is_shutting_down = False
        self.reconnect_cooldown = 5
        self.last_move_time = 0

        # Khởi tạo Discord Client
        try:
            discord.opus._load_default()
        except Exception:
            pass

        self.client = discord.Client()
        self.register_events()

    def register_events(self):
        @self.client.event
        async def on_ready():
            log(f"Đăng nhập thành công: {Fore.GREEN}{Style.BRIGHT}{self.client.user}{Style.RESET_ALL} (ID: {self.client.user.id})", "ok")
            log(f"Tổng số server tài khoản đang tham gia: {Fore.CYAN}{len(self.client.guilds)}{Style.RESET_ALL}", "info")
            
            # Cài đặt trạng thái hiện diện (Rich Presence)
            if self.custom_status:
                try:
                    activity = discord.CustomActivity(name=self.custom_status)
                    await self.client.change_presence(activity=activity, status=discord.Status.online)
                except Exception as e:
                    log(f"Không thể đặt custom status: {e}", "warn")

            # Bắt đầu thiết lập hoặc vào thẳng kênh voice
            asyncio.create_task(self.start_voice_session())

        @self.client.event
        async def on_voice_state_update(member, before, after):
            # Chỉ theo dõi sự thay đổi trạng thái của chính tài khoản này
            if member.id != self.client.user.id:
                return

            if self.is_shutting_down:
                return

            # Chỉ xử lý ngắt kết nối sau khi đã kết nối thành công trước đó
            if not self.is_connected:
                return

            # Trường hợp 1: Bị ngắt kết nối (kick ra khỏi voice hoặc mất mạng)
            if before.channel is not None and after.channel is None:
                self.is_connected = False
                log(f"Tài khoản bị ngắt kết nối khỏi kênh voice!", "warn")
                if self.auto_reconnect and not self.is_shutting_down and not self.is_reconnecting:
                    asyncio.create_task(self.delayed_reconnect())

            # Trường hợp 2: Bị chuyển sang kênh khác (ví dụ: kênh AFK hoặc phòng khác)
            elif self.target_channel and after.channel and after.channel.id != self.target_channel.id:
                now = time.time()
                log(f"Phát hiện bị di chuyển sang kênh khác: {Fore.YELLOW}{after.channel.name}{Style.RESET_ALL}", "warn")
                
                # Tránh lặp vô tận nếu bị di chuyển liên tục
                if now - self.last_move_time > 5 and self.auto_reconnect and not self.is_reconnecting:
                    self.last_move_time = now
                    asyncio.create_task(self.move_back_to_target())

    async def resolve_channel_by_id(self, channel_id: int) -> Optional[discord.VoiceChannel]:
        """Tìm kênh voice theo ID (thông qua cache hoặc gọi fetch_channel trực tiếp)."""
        ch = self.client.get_channel(channel_id)
        if not ch:
            try:
                ch = await self.client.fetch_channel(channel_id)
            except Exception as e:
                log(f"Không thể tìm kênh ID {channel_id}: {e}", "warn")
                return None

        if not isinstance(ch, (discord.VoiceChannel, discord.StageChannel)):
            log(f"Kênh ID {channel_id} ('{getattr(ch, 'name', 'N/A')}') không phải là kênh Voice/Stage!", "err")
            return None

        return ch

    async def start_voice_session(self):
        """Khởi động phiên treo voice: kiểm tra channel_id có sẵn hoặc cho chọn tương tác."""
        try:
            # Nếu người dùng đã cung cấp channel_id (từ tham số, config, hoặc nhập lúc đầu)
            if self.channel_id:
                ch = await self.resolve_channel_by_id(int(self.channel_id))
                if ch:
                    self.target_channel = ch
                    self.guild_id = ch.guild.id
                    log(f"Đã nhận diện Kênh Voice: {Fore.GREEN}{Style.BRIGHT}{ch.name}{Style.RESET_ALL} (Server: {ch.guild.name})", "ok")
                else:
                    log(f"ID Voice {self.channel_id} không tìm thấy hoặc tài khoản chưa tham gia server này!", "err")
                    self.channel_id = None
                    self.target_channel = None

            # Nếu chưa có kênh voice mục tiêu hợp lệ, chuyển sang menu chọn
            if not self.target_channel:
                await self.interactive_selection()

            if not self.target_channel:
                log("Chưa chọn được kênh voice. Dừng phiên làm việc.", "err")
                await self.client.close()
                return

            # Tiến hành kết nối vào kênh mục tiêu
            await self.connect_to_target()

            # Khởi chạy luồng giám sát thời gian treo voice
            asyncio.create_task(self.uptime_monitor_loop())

        except Exception as e:
            log(f"Lỗi trong quá trình khởi tạo phiên voice: {e}", "err")

    async def interactive_selection(self):
        """Menu chọn Kênh Voice: hỗ trợ dán ID Kênh trực tiếp hoặc duyệt danh sách Server -> Kênh."""
        print(f"\n{Fore.YELLOW}{Style.BRIGHT}================== CHON KENH VOICE DE TREO =================={Style.RESET_ALL}")
        print("Bạn có thể lựa chọn 1 trong 2 cách:")
        print(f"  [{Fore.CYAN}1{Style.RESET_ALL}] Dán trực tiếp ID Kênh Voice (nhanh nhất)")
        print(f"  [{Fore.CYAN}2{Style.RESET_ALL}] Xem danh sách Server & Kênh Voice để chọn")
        print("Mẹo: Bật Developer Mode (Cài đặt -> Nâng cao -> Chế độ nhà phát triển),")
        print("sau đó chuột phải vào kênh voice -> chọn 'Sao chép ID Kênh'.\n")

        prompt = "> Dán ID Kênh Voice (hoặc bấm Enter / gõ '2' để xem danh sách Server): "
        choice = (await ainput(prompt)).strip()

        # Nếu người dùng dán ID Kênh Voice (dạng số từ 15 chữ số trở lên)
        if choice.isdigit() and len(choice) >= 15:
            cid = int(choice)
            log(f"Đang kiểm tra Kênh Voice ID {cid}...", "info")
            ch = await self.resolve_channel_by_id(cid)
            if ch:
                self.target_channel = ch
                self.channel_id = ch.id
                self.guild_id = ch.guild.id
                log(f"Đã tìm thấy Kênh: {Fore.GREEN}{Style.BRIGHT}{ch.name}{Style.RESET_ALL} (Server: {ch.guild.name})", "ok")
                await self.prompt_voice_options(ch.guild, ch)
                return
            else:
                log(f"Không thể kết nối tới ID {cid}. Đang chuyển sang danh sách Server...", "warn")

        # Duyệt danh sách Server -> Kênh Voice
        await self.select_from_server_list()

    async def select_from_server_list(self):
        """Duyệt chọn Server sau đó chọn Kênh Voice."""
        print(f"\n{Fore.YELLOW}{Style.BRIGHT}---------- BUOC 1: CHON SERVER (MAY CHU) ----------{Style.RESET_ALL}")
        guilds = list(self.client.guilds)
        if not guilds:
            log("Tài khoản của bạn chưa tham gia bất kỳ server nào!", "err")
            return

        for idx, guild in enumerate(guilds, 1):
            member_count = guild.member_count or "N/A"
            print(f"  [{Fore.CYAN}{idx:02d}{Style.RESET_ALL}] {Fore.WHITE}{Style.BRIGHT}{guild.name}{Style.RESET_ALL} (ID: {guild.id}) - {member_count} thành viên")

        selected_guild = None
        while not selected_guild:
            prompt = f"\n> Chọn số thứ tự server (1-{len(guilds)}) hoặc dán ID Server: "
            user_choice = (await ainput(prompt)).strip()

            if user_choice.isdigit():
                val = int(user_choice)
                if 1 <= val <= len(guilds):
                    selected_guild = guilds[val - 1]
                else:
                    selected_guild = self.client.get_guild(val)
            else:
                for g in guilds:
                    if g.name.lower() == user_choice.lower():
                        selected_guild = g
                        break

            if not selected_guild:
                print(f"{Fore.RED}Lựa chọn không hợp lệ, vui lòng thử lại.{Style.RESET_ALL}")

        self.guild_id = selected_guild.id
        log(f"Đã chọn server: {Fore.GREEN}{Style.BRIGHT}{selected_guild.name}{Style.RESET_ALL}", "ok")

        # Chọn Kênh Voice trong Server đã chọn
        print(f"\n{Fore.YELLOW}{Style.BRIGHT}---------- BUOC 2: CHON KENH VOICE ----------{Style.RESET_ALL}")
        voice_channels = [
            c for c in selected_guild.channels
            if isinstance(c, (discord.VoiceChannel, discord.StageChannel))
        ]
        voice_channels.sort(key=lambda c: c.position)

        if not voice_channels:
            log(f"Server '{selected_guild.name}' không có kênh voice nào hoặc tài khoản không có quyền xem!", "err")
            return

        for idx, vc in enumerate(voice_channels, 1):
            channel_type = "[Stage]" if isinstance(vc, discord.StageChannel) else "[Voice]"
            user_count = len(vc.members)
            limit_str = f"/{vc.user_limit}" if getattr(vc, 'user_limit', 0) > 0 else ""
            category_name = f"[{vc.category.name}] " if vc.category else ""
            
            permissions = vc.permissions_for(selected_guild.me)
            lock_str = "" if permissions.connect else f" {Fore.RED}[Khoa - Thieu quyen]{Style.RESET_ALL}"

            print(f"  [{Fore.CYAN}{idx:02d}{Style.RESET_ALL}] {channel_type} {Fore.WHITE}{category_name}{vc.name}{Style.RESET_ALL} ({user_count}{limit_str} người){lock_str} (ID: {vc.id})")

        selected_channel = None
        while not selected_channel:
            prompt = f"\n> Chọn số thứ tự kênh voice (1-{len(voice_channels)}) hoặc dán ID Kênh: "
            user_choice = (await ainput(prompt)).strip()

            if user_choice.isdigit():
                val = int(user_choice)
                if 1 <= val <= len(voice_channels):
                    selected_channel = voice_channels[val - 1]
                else:
                    selected_channel = selected_guild.get_channel(val)
            else:
                for vc in voice_channels:
                    if vc.name.lower() == user_choice.lower():
                        selected_channel = vc
                        break

            if not selected_channel:
                print(f"{Fore.RED}Lựa chọn không hợp lệ, vui lòng thử lại.{Style.RESET_ALL}")

        self.channel_id = selected_channel.id
        self.target_channel = selected_channel
        log(f"Đã chọn kênh: {Fore.GREEN}{Style.BRIGHT}{selected_channel.name}{Style.RESET_ALL}", "ok")

        await self.prompt_voice_options(selected_guild, selected_channel)

    async def prompt_voice_options(self, guild: discord.Guild, channel: discord.VoiceChannel):
        """Hỏi người dùng các tùy chọn Mute, Deafen, Camera, Custom Status và lưu cấu hình."""
        print(f"\n{Fore.YELLOW}{Style.BRIGHT}---------- BUOC 3: TUY CHON CAI DAT ----------{Style.RESET_ALL}")
        mute_ans = (await ainput("Tự động tắt Micro (Self-Mute)? [Y/n]: ")).strip().lower()
        self.self_mute = mute_ans in ("", "y", "yes", "true", "1")

        deaf_ans = (await ainput("Tự động tắt Tai nghe (Self-Deafen)? [Y/n]: ")).strip().lower()
        self.self_deaf = deaf_ans in ("", "y", "yes", "true", "1")

        video_ans = (await ainput("Bật Camera (Self-Video)? [y/N]: ")).strip().lower()
        self.self_video = video_ans in ("y", "yes", "true", "1")

        status_input = (await ainput("Nhập trạng thái hiển thị (Bấm Enter để dùng 'Treo Voice 24/7'): ")).strip()
        if status_input:
            self.custom_status = status_input

        # Lưu cấu hình
        save_ans = (await ainput("\nBạn có muốn lưu cấu hình này cho các lần chạy sau? [Y/n]: ")).strip().lower()
        if save_ans in ("", "y", "yes", "true", "1"):
            config_data = {
                "token": self.token,
                "guild_id": guild.id,
                "guild_name": guild.name,
                "channel_id": channel.id,
                "channel_name": channel.name,
                "self_mute": self.self_mute,
                "self_deaf": self.self_deaf,
                "self_video": self.self_video,
                "auto_reconnect": self.auto_reconnect,
                "custom_status": self.custom_status,
            }
            save_config(config_data, self.config_path)

    async def connect_to_target(self):
        """Kết nối vào kênh voice mục tiêu."""
        if not self.target_channel:
            log("Không xác định được kênh voice mục tiêu để kết nối!", "err")
            return

        log(f"Đang kết nối vào kênh {Fore.CYAN}{Style.BRIGHT}{self.target_channel.name}{Style.RESET_ALL} (Server: {self.target_channel.guild.name})...", "info")

        # Ngắt các voice client cũ nếu có
        for vc in list(self.client.voice_clients):
            try:
                await vc.disconnect(force=True)
            except Exception:
                pass

        try:
            self.voice_client = await self.target_channel.connect(
                timeout=30.0,
                reconnect=True,
                self_deaf=self.self_deaf,
                self_mute=self.self_mute
            )
            self.is_connected = True
            if self.start_time is None:
                self.start_time = time.time()

            mute_status = f"{Fore.GREEN}BẬT{Style.RESET_ALL}" if self.self_mute else f"{Fore.RED}TẮT{Style.RESET_ALL}"
            deaf_status = f"{Fore.GREEN}BẬT{Style.RESET_ALL}" if self.self_deaf else f"{Fore.RED}TẮT{Style.RESET_ALL}"
            video_status = f"{Fore.GREEN}BẬT{Style.RESET_ALL}" if self.self_video else f"{Fore.RED}TẮT{Style.RESET_ALL}"

            print(f"\n{Fore.GREEN}{Style.BRIGHT}======================================================================")
            print(f"               KẾT NỐI VÀO PHÒNG VOICE THÀNH CÔNG!                 ")
            print(f"======================================================================{Style.RESET_ALL}")
            print(f"  * Server         : {Fore.WHITE}{Style.BRIGHT}{self.target_channel.guild.name}{Style.RESET_ALL}")
            print(f"  * Phòng Voice    : {Fore.CYAN}{Style.BRIGHT}{self.target_channel.name}{Style.RESET_ALL} (ID: {self.target_channel.id})")
            print(f"  * Tự tắt Mic     : {mute_status}")
            print(f"  * Tự tắt Tai nghe: {deaf_status}")
            print(f"  * Camera Video   : {video_status}")
            print(f"  * Tự kết nối lại : {Fore.GREEN}ĐANG BẬT (24/7 Anti-Kick){Style.RESET_ALL}")
            print(f"  * Bấm {Fore.YELLOW}Ctrl + C{Style.RESET_ALL} bất cứ lúc nào để dừng và ngắt kết nối an toàn.\n")

        except Exception as e:
            self.is_connected = False
            log(f"Lỗi khi kết nối vào kênh voice: {e}", "err")
            if self.auto_reconnect and not self.is_shutting_down and not self.is_reconnecting:
                asyncio.create_task(self.delayed_reconnect())

    async def delayed_reconnect(self):
        """Kết nối lại có độ trễ để tránh xung đột với Discord Gateway."""
        if self.is_reconnecting or self.is_shutting_down:
            return
        self.is_reconnecting = True
        try:
            log(f"Sẽ thử kết nối lại sau {self.reconnect_cooldown} giây...", "warn")
            await asyncio.sleep(self.reconnect_cooldown)
            log("Đang tiến hành kết nối lại vào kênh voice...", "info")
            await self.connect_to_target()
        finally:
            self.is_reconnecting = False

    async def move_back_to_target(self):
        """Chuyển lại về phòng mục tiêu nếu bị chuyển sang kênh khác (như kênh AFK)."""
        log(f"Đang tự động chuyển về kênh mục tiêu: {Fore.CYAN}{self.target_channel.name}{Style.RESET_ALL}...", "info")
        await asyncio.sleep(2)
        try:
            guild = self.client.get_guild(self.guild_id)
            if guild:
                await guild.change_voice_state(
                    channel=self.target_channel,
                    self_mute=self.self_mute,
                    self_deaf=self.self_deaf,
                    self_video=self.self_video
                )
        except Exception as e:
            log(f"Lỗi khi di chuyển về kênh: {e}. Đang thử kết nối lại...", "warn")
            await self.connect_to_target()

    async def uptime_monitor_loop(self):
        """Vòng lặp hiển thị thời gian đã treo và giám sát kết nối theo chu kỳ."""
        iteration = 0
        while not self.is_shutting_down:
            await asyncio.sleep(15)
            iteration += 1
            if self.is_connected and self.start_time:
                uptime_str = format_duration(time.time() - self.start_time)
                ping_ms = round(self.client.latency * 1000, 1) if self.client.latency else 0
                
                # In thông tin trạng thái mỗi 60 giây (mỗi 4 chu kỳ 15s)
                if iteration % 4 == 0:
                    channel_name = self.target_channel.name if self.target_channel else "N/A"
                    members_count = len(self.target_channel.members) if self.target_channel else 0
                    log(f"⏱️  Thời gian đã treo: {Fore.GREEN}{Style.BRIGHT}{uptime_str}{Style.RESET_ALL} | Ping: {ping_ms}ms | Phòng: {channel_name} ({members_count} người)", "time")

    async def shutdown(self):
        """Dọn dẹp và ngắt kết nối an toàn khi tắt ứng dụng."""
        if self.is_shutting_down:
            return
        self.is_shutting_down = True
        print(f"\n{Fore.YELLOW}Đang ngắt kết nối khỏi kênh voice và đóng phiên làm việc...{Style.RESET_ALL}")
        
        for vc in list(self.client.voice_clients):
            try:
                await vc.disconnect(force=True)
            except Exception:
                pass
                
        await self.client.close()
        total_time = format_duration(time.time() - self.start_time) if self.start_time else "0 giây"
        log(f"Đã ngắt kết nối an toàn. Tổng thời gian đã treo: {Fore.CYAN}{total_time}{Style.RESET_ALL}", "ok")


# ── Hàm Main & Khởi động ──────────────────────────────────────────────────────
def parse_arguments():
    parser = argparse.ArgumentParser(description="Discord Voice Hanger / Treo Voice 24/7")
    parser.add_argument("--token", help="Discord User Token")
    parser.add_argument("--guild", type=int, help="ID của Server cần treo")
    parser.add_argument("--channel", type=int, help="ID của Kênh Voice cần treo (nhập ID để vào thẳng)")
    parser.add_argument("--config", default=CONFIG_FILE, help=f"Đường dẫn file config (mặc định: {CONFIG_FILE})")
    parser.add_argument("--setup", action="store_true", help="Bắt buộc chạy giao diện cấu hình tương tác lại")
    parser.add_argument("--mute", type=str, choices=["true", "false"], help="Bật/tắt tự tắt mic (true/false)")
    parser.add_argument("--deaf", type=str, choices=["true", "false"], help="Bật/tắt tự tắt tai nghe (true/false)")
    parser.add_argument("--status", type=str, help="Trạng thái tùy chỉnh (Custom Status)")
    return parser.parse_args()


def select_or_input_token(saved_token: Optional[str]) -> str:
    """Hỗ trợ chọn token từ tokens.json, config cũ hoặc nhập mới."""
    tokens_from_file = get_tokens_from_tokens_json()

    print(f"\n{Fore.YELLOW}{Style.BRIGHT}================== DANG NHAP TOKEN DISCORD =================={Style.RESET_ALL}")
    
    # Nếu có token lưu trong tokens.json
    if tokens_from_file:
        print("Tìm thấy các tài khoản đã lưu trong tokens.json:")
        token_list = list(tokens_from_file.items())
        for idx, (uid, tok) in enumerate(token_list, 1):
            tok_preview = f"{tok[:10]}...{tok[-5:]}" if len(tok) > 15 else tok
            print(f"  [{Fore.CYAN}{idx}{Style.RESET_ALL}] User ID: {Fore.WHITE}{Style.BRIGHT}{uid}{Style.RESET_ALL} (Token: {tok_preview})")
        print(f"  [{Fore.CYAN}0{Style.RESET_ALL}] Nhập mã Token mới bằng tay")

        if saved_token:
            sav_preview = f"{saved_token[:10]}...{saved_token[-5:]}" if len(saved_token) > 15 else saved_token
            print(f"  [Enter] Dùng token đã cấu hình trước đó: ({sav_preview})")

        choice = input("\n> Lựa chọn của bạn: ").strip()
        if choice == "" and saved_token:
            return saved_token
        if choice.isdigit():
            c_val = int(choice)
            if 1 <= c_val <= len(token_list):
                return token_list[c_val - 1][1]

    # Nếu có token từ file config cũ
    elif saved_token:
        sav_preview = f"{saved_token[:10]}...{saved_token[-5:]}" if len(saved_token) > 15 else saved_token
        print(f"Token đã lưu: {Fore.GREEN}{sav_preview}{Style.RESET_ALL}")
        choice = input("> Bấm Enter để tiếp tục dùng token này, hoặc gõ 'new' để nhập token mới [Enter/new]: ").strip().lower()
        if choice not in ("new", "n", "change"):
            return saved_token

    # Nhập token mới bằng tay
    while True:
        token_input = input("> Nhập Discord User Token của bạn: ").strip().strip('"').strip("'")
        if token_input:
            return token_input
        print(f"{Fore.RED}Token không được để trống! Vui lòng nhập lại.{Style.RESET_ALL}")


def select_or_input_channel_id(saved_channel_id: Optional[int], saved_guild_name: str, saved_channel_name: str) -> Optional[int]:
    """Hỗ trợ nhập trực tiếp ID Kênh Voice hoặc chọn dùng lại ID cũ."""
    if saved_channel_id:
        print(f"\n{Fore.YELLOW}{Style.BRIGHT}================== KENH VOICE DA LUU =================={Style.RESET_ALL}")
        print(f"  * Server       : {Fore.GREEN}{saved_guild_name}{Style.RESET_ALL}")
        print(f"  * Kênh Voice   : {Fore.CYAN}{saved_channel_name}{Style.RESET_ALL} (ID: {saved_channel_id})")
        print("\nBạn có thể:")
        print(f"  - Bấm {Fore.GREEN}Enter{Style.RESET_ALL} để vào ngay kênh này.")
        print(f"  - Dán {Fore.CYAN}ID Kênh Voice mới{Style.RESET_ALL} để đổi sang kênh khác.")
        print(f"  - Gõ {Fore.YELLOW}'list'{Style.RESET_ALL} để duyệt danh sách Server & Kênh sau khi đăng nhập.")

        val = input("\n> Lựa chọn [Enter/Dán ID/list]: ").strip()
        if val == "":
            return saved_channel_id
        if val.isdigit() and len(val) >= 15:
            return int(val)
        if val.lower() in ("list", "menu", "n", "new"):
            return None

    # Chưa có ID lưu
    print(f"\n{Fore.YELLOW}{Style.BRIGHT}================== NHAP ID KENH VOICE =================={Style.RESET_ALL}")
    print("Mẹo: Chuột phải vào Kênh Voice trên Discord -> Chọn 'Sao chép ID Kênh'.")
    val = input("> Dán ID Kênh Voice (hoặc bấm Enter / gõ 'list' để xem danh sách Server & Kênh): ").strip()
    if val.isdigit() and len(val) >= 15:
        return int(val)
    return None


def main():
    args = parse_arguments()
    print_banner()

    # 1. Tải cấu hình từ file
    saved_config = load_saved_config(args.config)

    # 2. Xác định token
    token = args.token
    if not token and not args.setup:
        token = saved_config.get("token") or get_token_from_env_or_files()

    if not token or args.setup:
        token = select_or_input_token(saved_config.get("token"))

    # 3. Xác định Voice Channel ID
    channel_id = args.channel
    guild_id = args.guild

    if channel_id is None and not args.setup:
        saved_cid = saved_config.get("channel_id")
        saved_gname = saved_config.get("guild_name", "N/A")
        saved_cname = saved_config.get("channel_name", "N/A")
        channel_id = select_or_input_channel_id(saved_cid, saved_gname, saved_cname)
        if channel_id == saved_cid:
            guild_id = saved_config.get("guild_id")
    elif args.setup:
        channel_id = select_or_input_channel_id(None, "", "")

    # 4. Hợp nhất cấu hình
    config = {
        "token": token,
        "guild_id": guild_id,
        "channel_id": channel_id,
        "self_mute": (args.mute.lower() == "true") if args.mute else saved_config.get("self_mute", True),
        "self_deaf": (args.deaf.lower() == "true") if args.deaf else saved_config.get("self_deaf", True),
        "self_video": saved_config.get("self_video", False),
        "auto_reconnect": saved_config.get("auto_reconnect", True),
        "custom_status": args.status or saved_config.get("custom_status", "Treo Voice 24/7"),
    }

    hanger = VoiceHanger(config, config_path=args.config)

    # Khởi chạy Discord client
    try:
        hanger.client.run(token)
    except discord.errors.LoginFailure:
        log("Token không hợp lệ hoặc tài khoản đã đổi mật khẩu/hết hạn phiên đăng nhập!", "err")
        log("Vui lòng kiểm tra lại token và thử lại.", "err")
    except KeyboardInterrupt:
        pass
    except Exception as e:
        log(f"Lỗi không xác định: {e}", "err")
    finally:
        print(f"\n{Fore.CYAN}Cảm ơn bạn đã sử dụng Discord Voice Hanger! Tạm biệt!{Style.RESET_ALL}")


if __name__ == "__main__":
    main()
